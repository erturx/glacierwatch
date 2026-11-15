"""Validate observation identity, grid alignment, water areas and exported assets."""
from datetime import datetime
import hashlib
import math

import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.features import rasterize
from shapely.geometry import Point, shape
from shapely.ops import transform

from catalog import ROOT, load_json
from inventory import reviewed_reductions, verify_pair
from optical import ACCEPTED, OUT


def verify_observation(obs):
    assert obs["granule"] and obs["source"].startswith("https://")
    assert datetime.fromisoformat(obs["datetime"]).utcoffset().total_seconds() == 0
    q = obs["quality"]
    assert q["status"] in {"Reviewed", "Coverage-limited"}
    assert .90 <= q["validFraction"] <= 1
    assert not q["touchesBasinEdge"]
    assert q["lowKm2"] <= obs["areaKm2"] <= q["highKm2"]
    assert q["unknownKm2"] >= 0
    paths = {k: OUT.parent / p for k, p in obs["files"].items()}
    with rasterio.open(paths["mask"]) as ds:
        data = ds.read(1)
        assert ds.nodata == 255
        assert set(np.unique(data)).issubset({0, 1, 255})
        assert ds.crs.is_projected
        assert ds.res == (obs["grid"]["pixelMetres"],) * 2
        assert data.shape == (obs["grid"]["size"],) * 2
        assert int(np.sum(data == 1)) == q["waterPixels"]
        assert math.isclose(np.sum(data == 1) * ds.res[0] * ds.res[1] / 1e6, obs["areaKm2"], abs_tol=1e-10)
        boundary = shape(load_json(paths["boundary"])["features"][0]["geometry"])
        projected = transform(Transformer.from_crs(4326, ds.crs, always_xy=True).transform, boundary)
        rebuilt = rasterize([(projected, 1)], out_shape=ds.shape, transform=ds.transform)
        assert np.array_equal(rebuilt == 1, data == 1)
        with Image.open(paths["image"]) as image, Image.open(paths["overlay"]) as overlay:
            assert image.size == overlay.size == (ds.width, ds.height)
            layers = np.asarray(overlay)
            assert np.any(layers[data == 255, 3] > 0) if np.any(data == 255) else True
            assert not np.any((layers[:, :, 2] == 245) & (data != 1))
        frame = (ds.crs, ds.transform, ds.shape)
    if obs["collection"].startswith("NISAR_"):
        assert q["opticalComparison"]["iou"] >= .70
        for src in obs["inputs"].values():
            file = ROOT / "pipeline" / "source" / "nisar" / src["file"]
            assert hashlib.sha256(file.read_bytes()).hexdigest() == src["sha256"]
    return frame


def main():
    inventory = load_json(OUT / "inventory.json")
    region = load_json(OUT / "region.geojson")
    kyrgyzstan = shape(next(f["geometry"] for f in region["features"] if f["properties"]["code"] == "KGZ"))
    lake_ids = set()
    count = 0
    for lake in inventory["lakes"]:
        assert lake["id"] not in lake_ids
        lake_ids.add(lake["id"])
        marker = Point(lake["lon"], lake["lat"])
        assert kyrgyzstan.covers(marker) and shape(lake["extent"]).covers(marker)
        for series in lake["series"]:
            verify_pair(series)
            observations = series["observations"]
            assert len(set(o["datetime"][:10] for o in observations)) == len(observations)
            assert all(o["lake"] == lake["id"] for o in observations)
            grids = {verify_observation(obs) for obs in observations}
            assert len(grids) == 1, f'Images in {lake["id"]}/{series["key"]} are misaligned'
            assert series["comparisons"] == reviewed_reductions(observations)
            count += len(observations)
    assert lake_ids and lake_ids == set(load_json(ACCEPTED))
    print(f"PASS: {len(lake_ids)} Kyrgyz lake locations, {count} observation masks, boundaries, image pairs and provenance records")


if __name__ == "__main__":
    main()
