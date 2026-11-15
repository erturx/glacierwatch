"""Extract and measure reviewed Sentinel-2 water outlines on a common UTM grid."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import math
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.transform import from_origin, rowcol
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from scipy import ndimage as ndi
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform as transform_geometry, unary_union

from catalog import CACHE, CANDIDATES, ROOT, STAC, load_json, save_json

WORK = ROOT / ".cache" / "optical"
OUT = ROOT / "dist" / "data"
ACCEPTED = ROOT / "pipeline" / "review.json"
REFERENCES = ROOT / "pipeline" / "reference-geometries.json"
PIXEL = 10
BANDS = ("scl", "green", "nir", "swir16", "red", "blue")
TARGET_MONTH_DAY = {
    "zyndan": ["2024-08-09", "2024-08-28"],
    "merzbacher": ["2026-08-20", "2026-09-06", "2025-08-15", "2025-09-10", "2024-08-15"],
    "uchitel": ["2024-08-15", "2025-08-15", "2026-08-15"],
}


class Grid:
    def __init__(self, lake):
        self.epsg = 32601 + int((lake["lon"] + 180) // 6)
        self.project = Transformer.from_crs(4326, self.epsg, always_xy=True).transform
        self.unproject = Transformer.from_crs(self.epsg, 4326, always_xy=True).transform
        x, y = self.project(lake["lon"], lake["lat"])
        r = lake["radius"]
        west = math.floor((x - r) / PIXEL) * PIXEL
        north = math.ceil((y + r) / PIXEL) * PIXEL
        self.size = math.ceil(r * 2 / PIXEL) + 1
        self.bounds = (west, north - self.size * PIXEL, west + self.size * PIXEL, north)
        self.transform = from_origin(west, north, PIXEL, PIXEL)
        self.dim = (self.size, self.size)
        self.anchor = rowcol(self.transform, x, y)
        refs = load_json(REFERENCES) if REFERENCES.exists() else {}
        ref = refs.get(lake["id"])
        self.reference = transform_geometry(self.project, shape(ref["geometry"])) if ref else None
        locator = shape(lake["locator"]) if "locator" in lake else None
        if locator is not None:
            self.seed = transform_geometry(self.project, locator)
        else:
            self.seed = self.reference if self.reference is not None else Point(x, y).buffer(max(65, r / 5))
        self.basin = self.seed.buffer(lake.get("buffer", min(650, r * .42)))
        self.seed_pixels = self.rasterize(self.seed)
        self.basin_pixels = self.rasterize(self.basin)
        self.extent = transform_geometry(self.unproject, box(*self.bounds))

    def rasterize(self, geom):
        return geometry_mask([mapping(geom)], out_shape=self.dim, transform=self.transform, invert=True)

    def polygons(self, mask):
        polygons = [
            shape(geom) for geom, value in shapes(mask.astype("uint8"), mask, transform=self.transform)
            if value == 1
        ]
        return unary_union(polygons)


def read_band(item, key, grid):
    asset = item["assets"][key]
    numeric = key != "scl"
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_USE_HEAD="NO",
        GDAL_HTTP_MAX_RETRY="2", GDAL_HTTP_TIMEOUT="25",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    ), rasterio.open(asset["href"]) as src:
        with WarpedVRT(src, crs=f"EPSG:{grid.epsg}", transform=grid.transform,
                       width=grid.size, height=grid.size, src_nodata=0, nodata=0,
                       resampling=Resampling.bilinear if numeric else Resampling.nearest) as aligned:
            raw = aligned.read(1)
    if not numeric:
        return raw
    metadata = asset.get("raster:bands", [{}])[0]
    flag = item["properties"].get("earthsearch:boa_offset_applied")
    baseline = float(item["properties"]["s2:processing_baseline"])
    if flag is None and baseline >= 4:
        raise ValueError("BOA offset status absent for post-04.00 COG")
    offset = metadata.get("offset", -0.1) if flag is False and baseline >= 4 else 0
    return np.where(raw > 0, np.maximum(0, raw * metadata.get("scale", 0.0001) + offset), np.nan).astype("float32")


def read_cache(item, lake, grid, minimum_clear=.85):
    path = WORK / lake["id"] / f'{item["id"]}.npz'
    if path.exists():
        with np.load(path) as files:
            if tuple(files["frame"]) == (*grid.bounds, grid.epsg):
                return {key: files[key] for key in BANDS}
    scl = read_band(item, "scl", grid)
    valid = np.isin(scl, [4, 5, 6])
    if np.mean(valid[grid.seed_pixels]) < minimum_clear:
        raise ValueError(f"clear SCL class over only {np.mean(valid[grid.seed_pixels]):.0%} of locator")
    with ThreadPoolExecutor(max_workers=5) as pool:
        stack = dict(zip(BANDS[1:], pool.map(lambda k: read_band(item, k, grid), BANDS[1:])))
    stack["scl"] = scl
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, frame=[*grid.bounds, grid.epsg], **stack)
    save_json(path.with_suffix(".json"), item)
    return stack


def index(a, b):
    return (a - b) / np.maximum(a + b, 1e-5)


def measure(stack, grid, lake):
    scl = stack["scl"]
    green, nir, swir = (stack[key] for key in ("green", "nir", "swir16"))
    valid = np.isin(scl, [4, 5, 6]) & np.all(np.isfinite([stack[key] for key in BANDS[1:]]), axis=0)
    label_water = (scl == 6) & grid.seed_pixels & valid
    if np.sum(label_water) >= 36 and not .001 <= np.median(nir[label_water]) <= .14:
        raise ValueError("median SCL-water NIR outside reflectance sanity check")
    ndwi, mndwi = index(green, nir), index(green, swir)

    def classify(shift):
        detected = valid & grid.basin_pixels & (ndwi > .06 + shift) & (mndwi > .18 + shift) & (nir < .16)
        components, count = ndi.label(detected, structure=np.ones((3, 3)))
        if not count:
            return np.zeros_like(valid)
        overlap = np.bincount(components[grid.seed_pixels], minlength=count + 1)
        size = np.bincount(components.ravel(), minlength=count + 1)
        eligible = np.flatnonzero((overlap >= 3) & (size >= 6))
        eligible = eligible[eligible != 0]
        if eligible.size and not lake.get("segments", False):
            eligible = [eligible[np.argmax(overlap[eligible])]]
        return np.isin(components, eligible)

    water = classify(0)
    strong, loose = classify(.05), classify(-.05)
    ring = ndi.binary_dilation(water, iterations=3) | grid.seed_pixels
    unknown = ring & ~valid
    outside = ndi.binary_dilation(water, iterations=1) & ~grid.basin_pixels
    unknown_count = int(np.sum(unknown))
    count = int(np.sum(water))
    scl_count = int(np.sum((scl == 6) & grid.basin_pixels))
    matched = int(np.sum(water & (scl == 6)))
    error = {
        "waterPixels": count,
        "validFraction": round(float(np.mean(valid[ring])), 5),
        "unknownKm2": round(unknown_count * .0001, 5),
        "lowKm2": round(min(count, int(np.sum(strong))) * .0001, 5),
        "highKm2": round((max(count, int(np.sum(loose))) + unknown_count) * .0001, 5),
        "sclWaterPixels": scl_count,
        "sclOverlap": round(matched / max(1, count), 4),
        "touchesBasinEdge": bool(np.any(outside)),
    }
    return water, valid, error


def write_assets(stack, water, valid, grid, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.dstack([stack[key] for key in ("red", "green", "blue")])
    rgb = (np.nan_to_num(np.clip(rgb / .33, 0, 1)) ** .71 * 255).astype("uint8")
    Image.fromarray(rgb).save(path.with_suffix(".webp"), quality=90, method=5)
    outline = water & ~ndi.binary_erosion(water)
    tint = np.zeros((*grid.dim, 4), dtype="uint8")
    tint[~valid] = [206, 143, 76, 35]
    yy, xx = np.indices(grid.dim)
    tint[(~valid) & (((xx + yy) % 6) == 0)] = [236, 176, 110, 125]
    tint[water] = [75, 226, 233, 37]
    tint[outline] = [111, 245, 245, 255]
    Image.fromarray(tint).save(path.with_suffix(".png"))
    poly = grid.polygons(water)
    area = float(poly.area)
    assert math.isclose(area, int(np.sum(water)) * PIXEL ** 2, abs_tol=.001)
    save_json(path.with_suffix(".geojson"), {
        "type": "FeatureCollection", "features": [{
            "type": "Feature", "geometry": mapping(transform_geometry(grid.unproject, poly)),
            "properties": {"areaKm2": round(area / 1_000_000, 5), "source": path.name},
        }],
    })
    with rasterio.open(path.with_suffix(".tif"), "w", driver="GTiff", width=grid.size, height=grid.size,
                       count=1, dtype="uint8", nodata=255, crs=f"EPSG:{grid.epsg}",
                       transform=grid.transform, compress="deflate") as dst:
        dst.write(np.where(valid, water, 255).astype("uint8"), 1)


def scout_selection(items, lake):
    targets = TARGET_MONTH_DAY.get(lake["id"], [
        f"{year}-08-20" for year in (2017, 2020, 2024, 2025, 2026)
    ])
    ranked = {}
    for target in map(date.fromisoformat, targets):
        year = [item for item in items if item["properties"]["datetime"].startswith(str(target.year))]
        def rank(item):
            props = item["properties"]
            day = date.fromisoformat(props["datetime"][:10])
            return abs((day - target).days) * .35 + props["eo:cloud_cover"] + (2 if props.get("proj:epsg") != 32601 + int((lake["lon"] + 180) // 6) else 0)

        ranked_days = {}
        for item in sorted(year, key=rank):
            day = item["properties"]["datetime"][:10]
            ranked_days.setdefault(day, item)
        selected = list(ranked_days.values())[:10]
        if target.isoformat() in ranked_days:
            selected.append(ranked_days[target.isoformat()])
        for item in selected:
            ranked[item["id"]] = item
    return list(ranked.values())


def process(item, lake, grid, destination):
    stack = read_cache(item, lake, grid)
    water, valid, quality = measure(stack, grid, lake)
    platform = item["properties"]
    path = destination / lake["id"] / item["id"]
    write_assets(stack, water, valid, grid, path)
    prefix = f'data/{lake["id"]}/{item["id"]}'
    return {
        "id": item["id"], "lake": lake["id"], "datetime": platform["datetime"],
        "provider": "ESA / Copernicus via Element 84 Earth Search",
        "satellite": platform["platform"].upper().replace("SENTINEL", "Sentinel"),
        "instrument": "MSI", "product": "Sentinel-2 L2A surface reflectance",
        "collection": item["collection"], "granule": platform.get("s2:granule_id") or platform.get("s2:product_uri") or item["id"],
        "safeProduct": platform.get("s2:product_uri"), "baseline": platform["s2:processing_baseline"],
        "boaOffsetApplied": platform.get("earthsearch:boa_offset_applied"),
        "source": f'{STAC}/collections/{item["collection"]}/items/{item["id"]}',
        "inputs": {key: item["assets"][key]["href"] for key in BANDS},
        "areaKm2": round(quality["waterPixels"] * .0001, 5), "quality": quality,
        "method": "NDWI > 0.06, MNDWI > 0.18, NIR < 0.16, clear SCL classes and basin connectivity",
        "grid": {"crs": f"EPSG:{grid.epsg}", "bounds": grid.bounds, "size": grid.size, "pixelMetres": PIXEL},
        "files": {k: prefix + "." + v for k, v in
                  {"image": "webp", "overlay": "png", "boundary": "geojson", "mask": "tif"}.items()},
    }


def scene_worker(item, lake, grid, destination):
    try:
        obs = process(item, lake, grid, destination)
        print(lake["id"], obs["datetime"][:10], obs["id"], obs["areaKm2"], obs["quality"], flush=True)
        return obs
    except (ValueError, rasterio.errors.RasterioError) as error:
        print(lake["id"], item["id"], "skip:", error, flush=True)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", action="append")
    parser.add_argument("--scene", action="append", help="limit scouting to specified STAC item IDs")
    parser.add_argument("--scout", action="store_true", help="screen scenes into the ignored working directory")
    args = parser.parse_args()
    reviews = {} if args.scout else load_json(ACCEPTED)
    for lake in load_json(CANDIDATES):
        key = lake["id"]
        if "lon" not in lake or (args.lake and key not in args.lake) or (not args.scout and key not in reviews):
            continue
        grid = Grid(lake)
        catalog = {item["id"]: item for path in (CACHE / key).glob("optical_*") for item in load_json(path)}
        if args.scout:
            items = [catalog[ident] for ident in args.scene] if args.scene else scout_selection(list(catalog.values()), lake)
            with ThreadPoolExecutor(max_workers=5) as pool:
                observations = list(pool.map(lambda item: scene_worker(item, lake, grid, WORK / "scout"), items))
            save_json(WORK / "scout" / key / "scout.json", [obs for obs in observations if obs])
            continue
        observations = []
        for ident, note in reviews[key]["scenes"].items():
            obs = process(catalog[ident], lake, grid, OUT)
            minimum = reviews[key].get("minValid", .95)
            if obs["quality"]["validFraction"] < minimum or obs["quality"]["touchesBasinEdge"] or obs["areaKm2"] <= 0:
                raise ValueError(f'Observation {ident} failed final quality gates')
            obs["quality"]["review"] = note
            obs["quality"]["status"] = "Coverage-limited" if obs["quality"]["validFraction"] < .95 else "Reviewed"
            observations.append(obs)
        lake["extent"] = mapping(grid.extent)
        lake["defaultDates"] = reviews[key]["defaultDates"]
        lake["observations"] = sorted(observations, key=lambda obs: obs["datetime"])
        save_json(OUT / key / "observations.json", lake)


if __name__ == "__main__":
    main()
