"""Recreate the published lake locator geometries and regional boundary layer."""
from pyproj import CRS, Transformer
import requests
import shapefile
from shapely.geometry import box, mapping, shape
from shapely.ops import transform

from catalog import ROOT, load_json, save_json

SOURCE = ROOT / ".cache" / "inventory"
ZENODO = "https://zenodo.org/api/records/17869915/files"
NATURAL_EARTH = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
RECORDS = {"petrov": 2216, "uchitel": 487, "alakol": 702, "adygine2": 2, "adygine3": 2093, "inventory-1115": 1115}


def download(url, path):
    if not path.exists():
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        pending = path.with_suffix(path.suffix + ".part")
        pending.write_bytes(response.content)
        pending.replace(path)
    return path


def lake_inventory(year):
    stem = f"Glacial_lakes_KYRG_{year}"
    for suffix in ("shp", "shx", "dbf", "prj", "cpg"):
        name = f"{stem}.{suffix}"
        download(f"{ZENODO}/{name}/content", SOURCE / name)
    return SOURCE / f"{stem}.shp"


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    latest = lake_inventory(2024)
    previous = lake_inventory(2016)
    crs = CRS.from_wkt(latest.with_suffix(".prj").read_text())
    wgs = Transformer.from_crs(crs, 4326, always_xy=True).transform
    refs = {}
    with shapefile.Reader(str(latest)) as records:
        for lake, index in RECORDS.items():
            geometry = shape(records.shapeRecord(index).shape.__geo_interface__)
            refs[lake] = {
                "inventory": "https://doi.org/10.5281/zenodo.17869915", "record": index,
                "areaKm2": round(geometry.area / 1e6, 5),
                "geometry": mapping(transform(wgs, geometry.simplify(4, preserve_topology=True))),
            }
        prior_index = 1629
        with shapefile.Reader(str(previous)) as old_records:
            prior = shape(old_records.shape(prior_index).__geo_interface__).buffer(0)
        recent = shape(records.shape(RECORDS["inventory-1115"]).__geo_interface__).buffer(0)
        locator = prior.union(recent).buffer(20).simplify(4, preserve_topology=True)
        refs["inventory-1115"]["previousRecord"] = prior_index
        refs["inventory-1115"]["locator"] = mapping(transform(wgs, locator))
    save_json(ROOT / "pipeline" / "reference-geometries.json", refs)
    region = box(67.2, 38.1, 82.1, 45.3)
    features = []
    for item in load_json(download(NATURAL_EARTH, SOURCE / "countries.geojson"))["features"]:
        geometry = shape(item["geometry"]).intersection(region)
        if geometry.area <= 0:
            continue
        properties = item["properties"]
        features.append({
            "type": "Feature", "geometry": mapping(geometry.simplify(.012, preserve_topology=True)),
            "properties": {"name": properties["ADMIN"], "code": properties["ADM0_A3"]},
        })
    save_json(ROOT / "dist" / "data" / "region.geojson", {"type": "FeatureCollection", "features": features})


if __name__ == "__main__":
    main()
