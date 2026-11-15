"""Process Frequency A NISAR GCOV cutouts and validate them against clear optical pixels."""
import argparse
from datetime import datetime
import hashlib
import math
import os
import time

import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import reproject
import requests
from scipy import ndimage as ndi
from shapely.geometry import mapping, shape
from shapely.ops import transform as project_geometry, unary_union

from catalog import CACHE, CANDIDATES, ROOT, STAC, load_json, save_json
from optical import BANDS, Grid, OUT, measure, read_cache

HARMONY = "https://harmony.earthdata.nasa.gov"
LAYERS = ("HHHH", "mask", "numberOfLooks")
VARIABLE = "/science/LSAR/GCOV/grids/frequencyA/"
LOCAL = ROOT / ".cache" / "nisar" / "science"
RETAINED = ROOT / "pipeline" / "source" / "nisar"


def asset_name(scene, layer):
    return scene["granule"] + "_science_LSAR_GCOV_grids_frequencyA_" + layer + "_subsetted.tif"


def request_parameters(scene):
    west, south, east, north = scene["bbox"]
    return [
        ("granuleId", scene["concept"]), ("forceAsync", "true"), ("format", "image/tiff"),
        ("subset", f"lat({south}:{north})"), ("subset", f"lon({west}:{east})"),
        *[("variable", VARIABLE + layer) for layer in LAYERS],
    ]


def paths_for(scene):
    files = [asset_name(scene, layer) for layer in LAYERS]
    paths = [RETAINED / file if (RETAINED / file).exists() else LOCAL / file for file in files]
    if all(path.exists() for path in paths):
        return paths
    token = os.environ.get("EARTHDATA_TOKEN")
    if not token:
        raise FileNotFoundError("Harmony inputs missing; set EARTHDATA_TOKEN in the environment or provide the documented GeoTIFF cutouts")
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    endpoint = f'{HARMONY}/{scene["collectionConcept"]}/ogc-api-coverages/1.0.0/collections/parameter_vars/coverage/rangeset'
    response = session.get(endpoint, params=request_parameters(scene), timeout=50)
    response.raise_for_status()
    status = response.json()
    job = f'{HARMONY}/jobs/{status["jobID"]}'
    for _ in range(100):
        if status["status"] == "successful":
            break
        if status["status"] in {"failed", "canceled"}:
            raise RuntimeError(f'Harmony job {status["jobID"]}: {status["status"]}')
        time.sleep(6)
        response = session.get(job, timeout=30)
        response.raise_for_status()
        status = response.json()
    else:
        raise TimeoutError(f'Harmony job {status["jobID"]} exceeded 10 minutes')
    by_file = {link["title"]: link["href"] for link in status["links"] if link["rel"] == "data"}
    LOCAL.mkdir(parents=True, exist_ok=True)
    for file in files:
        link = by_file[file]
        response = session.get(link, timeout=90)
        response.raise_for_status()
        if not response.content.startswith((b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")):
            raise ValueError(f"Harmony returned a response other than TIFF for {file}")
        pending = LOCAL / (file + ".part")
        pending.write_bytes(response.content)
        pending.replace(LOCAL / file)
    return [LOCAL / file for file in files]


def read_scene(lake, scene):
    paths = paths_for(scene)
    optical_grid = Grid(lake)
    with rasterio.open(paths[0]) as src:
        crs = src.crs
        cell_x, cell_y = src.res
    if not crs.is_projected or not math.isclose(cell_x, cell_y) or cell_x != 20:
        raise ValueError("This GCOV workflow expects native 20 m square UTM cells")
    project = Transformer.from_crs(4326, crs, always_xy=True).transform
    unproject = Transformer.from_crs(crs, 4326, always_xy=True).transform
    x, y = project(lake["lon"], lake["lat"])
    radius = lake["radius"]
    west = math.floor((x - radius) / cell_x) * cell_x
    north = math.ceil((y + radius) / cell_y) * cell_y
    transform = from_origin(west, north, cell_x, cell_y)
    size = math.ceil(2 * radius / cell_x) + 1
    warp = {"crs": crs, "transform": transform, "width": size, "height": size}
    arrays = []
    for layer, path in zip(LAYERS, paths):
        with rasterio.open(path) as src:
            if src.crs != crs or src.res != (cell_x, cell_y):
                raise ValueError(f"Grid does not match HHHH: {layer}")
            if layer == "mask" and "subswath" not in src.tags(1).get("long_name", "").lower():
                raise ValueError("GCOV mask does not identify the expected subswath semantics")
            with WarpedVRT(src, **warp) as aligned:
                arrays.append(aligned.read(1, masked=True).astype("float32").filled(np.nan))
    hh, mask, looks = arrays
    valid = np.isfinite(hh) & (hh > 0) & (mask >= 1) & (mask < 255) & (looks >= 3)
    db = np.full(hh.shape, np.nan, dtype="float32")
    db[valid] = 10 * np.log10(hh[valid])
    rasterize = lambda g: geometry_mask([mapping(project_geometry(project, project_geometry(optical_grid.unproject, g)))],
                                         out_shape=hh.shape, transform=transform, invert=True)
    seed, basin = rasterize(optical_grid.seed), rasterize(optical_grid.basin)
    return {"db": db, "looks": looks, "valid": valid, "seed": seed, "basin": basin,
            "unproject": unproject, "warp": warp, "paths": paths, "cell": cell_x}


def classify(frame, threshold):
    valid, seed, basin = (frame[name] for name in ("valid", "seed", "basin"))
    values = np.where(valid, frame["db"], 0)
    local_weight = ndi.uniform_filter(valid.astype("float32"), size=3)
    mean = ndi.uniform_filter(values, size=3) / np.maximum(local_weight, 1e-6)
    candidates = valid & basin & (mean < threshold) & (local_weight >= 5/9)
    regions, count = ndi.label(candidates, structure=np.ones((3, 3)))
    score = np.bincount(regions[seed], minlength=count + 1)
    score[0] = 0
    return (regions == np.argmax(score)) if np.any(score) else np.zeros_like(valid)


def optical_support(lake, ident, frame, water):
    items = (item for path in (CACHE / lake["id"]).glob("optical_*") for item in load_json(path))
    item = next(item for item in items if item["id"] == ident)
    props = item["properties"]
    grid = Grid(lake)
    stack = read_cache(item, lake, grid, minimum_clear=.70)
    optical_water, optical_valid, optical_quality = measure(stack, grid, lake)
    truth = np.full(water.shape, 255, dtype="uint8")
    reproject(np.where(optical_valid, optical_water, 255).astype("uint8"), truth,
              src_transform=grid.transform, src_crs=f"EPSG:{grid.epsg}", src_nodata=255,
              dst_transform=frame["warp"]["transform"], dst_crs=frame["warp"]["crs"], dst_nodata=255)
    shared = frame["valid"] & (truth != 255)
    observed = shared & (truth == 1)
    predicted = shared & water
    scale = frame["cell"] ** 2 / 1e6
    return {
        "scene": ident, "datetime": props["datetime"],
        "provider": "ESA / Copernicus via Element 84 Earth Search",
        "product": "Sentinel-2 L2A surface reflectance", "collection": item["collection"],
        "satellite": props["platform"], "instrument": "MSI",
        "granule": props.get("s2:granule_id") or props["s2:product_uri"],
        "source": f'{STAC}/collections/{item["collection"]}/items/{ident}',
        "inputs": {key: item["assets"][key]["href"] for key in BANDS},
        "baseline": props["s2:processing_baseline"], "validFraction": optical_quality["validFraction"],
        "iou": round(float(np.sum(observed & predicted) / max(1, np.sum(observed | predicted))), 4),
        "opticalKm2OnSharedPixels": round(float(np.sum(observed)) * scale, 5),
        "radarKm2OnSharedPixels": round(float(np.sum(predicted)) * scale, 5),
    }


def export(lake, scene, frame, threshold, destination, optical=None):
    db, valid, seed = (frame[name] for name in ("db", "valid", "seed"))
    water = classify(frame, threshold)
    low, high = classify(frame, threshold - 1.5), classify(frame, threshold + 1.5)
    region = seed | ndi.binary_dilation(water, iterations=2)
    unknown = region & ~valid
    pixels = int(np.sum(water))
    scale = frame["cell"] ** 2 / 1e6
    name = scene["granule"].split("_")[11]
    acquired = datetime.strptime(name, "%Y%m%dT%H%M%S").isoformat() + "Z"
    parts = scene["granule"].split("_")
    notes = {
        "waterPixels": pixels, "validFraction": float(np.mean(valid[region])),
        "unknownKm2": round(float(unknown.sum()) * scale, 5),
        "lowKm2": round(min(pixels, int(np.sum(low))) * scale, 5),
        "highKm2": round((max(pixels, int(np.sum(high))) + int(unknown.sum())) * scale, 5),
        "medianLooks": round(float(np.median(frame["looks"][region & valid])), 2),
        "thresholdDb": threshold, "touchesBasinEdge": bool(np.any(ndi.binary_dilation(water) & ~frame["basin"])),
        "medianWaterDb": round(float(np.median(db[water])), 2) if pixels else None,
        "medianSurroundingsDb": round(float(np.median(db[frame["basin"] & ~ndi.binary_dilation(water, iterations=3) & valid])), 2),
    }
    if optical:
        notes["opticalComparison"] = optical_support(lake, optical, frame, water)
    path = destination / lake["id"] / ("nisar-" + name)
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels_db = np.nan_to_num(db, nan=-32)
    ramp = np.clip((pixels_db + 28) / 27, 0, 1)
    rgb = np.stack((23 + ramp * 215, 30 + ramp * 212, 38 + ramp * 210), axis=2).astype("uint8")
    Image.fromarray(rgb).save(path.with_suffix(".webp"), quality=91)
    overlay = np.zeros((*db.shape, 4), dtype="uint8")
    rows, cols = np.indices(db.shape)
    overlay[~valid] = [220, 153, 79, 26]
    overlay[~valid & ((rows + cols) % 6 == 0)] = [224, 159, 88, 155]
    overlay[water] = [69, 234, 249, 44]
    overlay[water & ~ndi.binary_erosion(water)] = [111, 245, 245, 255]
    Image.fromarray(overlay).save(path.with_suffix(".png"))
    geometry = unary_union([shape(g) for g, value in shapes(water.astype("uint8"), mask=water,
                                                           transform=frame["warp"]["transform"]) if value == 1])
    assert math.isclose(geometry.area, pixels * frame["cell"] ** 2, abs_tol=.001)
    save_json(path.with_suffix(".geojson"), {
        "type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {"areaKm2": round(pixels * scale, 5)},
            "geometry": mapping(project_geometry(frame["unproject"], geometry)),
        }],
    })
    with rasterio.open(path.with_suffix(".tif"), "w", driver="GTiff", count=1, dtype="uint8",
                       nodata=255, compress="deflate", **frame["warp"]) as dst:
        dst.write(np.where(valid, water, 255).astype("uint8"), 1)
    relative = f'data/{lake["id"]}/{path.name}'
    return {
        "id": path.name, "lake": lake["id"], "datetime": acquired, "provider": "NASA / ASF DAAC",
        "satellite": "NASA–ISRO NISAR", "instrument": "L-band SAR", "product": "NISAR Level 2 GCOV",
        "collection": scene["collection"], "granule": scene["granule"], "concept": scene["concept"],
        "track": int(parts[5]), "direction": "Descending" if parts[6] == "D" else "Ascending",
        "maturity": "PROVISIONAL" if "PROVISIONAL" in scene["collection"] else "VALIDATED",
        "release": parts[13], "polarization": "HH × HH, Frequency A", "source": f'https://search.earthdata.nasa.gov/search/granules?p={scene["collectionConcept"]}&pg[0][id]={scene["concept"]}',
        "harmonyJob": f'{HARMONY}/jobs/{scene["job"]}', "harmonyBbox": scene["bbox"],
        "inputs": {layer: {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                   for layer, p in zip(LAYERS, frame["paths"])},
        "areaKm2": round(pixels * scale, 5), "quality": notes,
        "method": "HH gamma-zero in dB, 3×3 local mean, fixed threshold, connected basin component",
        "grid": {"crs": frame["warp"]["crs"].to_string(), "size": int(db.shape[0]), "pixelMetres": frame["cell"]},
        "files": {k: relative + "." + v for k, v in
                  {"image": "webp", "overlay": "png", "boundary": "geojson", "mask": "tif"}.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", default="petrov")
    parser.add_argument("--threshold", type=float, default=-16)
    parser.add_argument("--scout", action="store_true")
    args = parser.parse_args()
    lake = next(candidate for candidate in load_json(CANDIDATES) if candidate["id"] == args.lake)
    scenes = load_json(ROOT / "pipeline" / "radar-inputs.json")[args.lake]
    destination = LOCAL.parent / "scout" if args.scout else OUT
    review_path = ROOT / "pipeline" / "radar-review.json"
    review = {} if args.scout else load_json(review_path)[args.lake]
    observations = []
    for scene in scenes:
        reviewed = review.get(scene["concept"])
        if not args.scout and reviewed is None:
            continue
        frame = read_scene(lake, scene)
        opts = reviewed or {}
        obs = export(lake, scene, frame, opts.get("thresholdDb", args.threshold), destination, opts.get("opticalScene"))
        if reviewed:
            obs["quality"]["review"] = reviewed["review"]
            obs["quality"]["status"] = "Reviewed"
            if (obs["quality"]["validFraction"] < .95 or obs["quality"]["touchesBasinEdge"]
                    or obs["quality"]["opticalComparison"]["iou"] < .70 or obs["areaKm2"] <= 0):
                raise ValueError(f'Observation {obs["id"]} failed final radar quality gates')
        print(obs["id"], obs["areaKm2"], obs["quality"], flush=True)
        observations.append(obs)
    save_json(destination / args.lake / "radar.json", observations)


if __name__ == "__main__":
    main()
