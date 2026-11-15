"""Screen ASF GCOV footprints and public Sentinel-2 L2A STAC records."""
import argparse
import concurrent.futures
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "catalog"
CANDIDATES = ROOT / "pipeline" / "candidates.json"
STAC = "https://earth-search.aws.element84.com/v1"
ASF = "https://api.daac.asf.alaska.edu/services/search/param"


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def search(lake, mission, date_range):
    point = [lake["lon"], lake["lat"]]
    if mission == "optical":
        payload = {
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": point},
            "datetime": date_range.replace("/", "T00:00:00Z/") + "T23:59:59Z",
            "limit": 100,
        }
        response = requests.post(STAC + "/search", json=payload, timeout=45)
        features = []
        followed = set()
        while True:
            response.raise_for_status()
            page = response.json()
            features.extend(page["features"])
            link = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
            if not link:
                return features
            signature = json.dumps(link, sort_keys=True)
            if signature in followed:
                raise RuntimeError("Earth Search repeated a pagination link")
            followed.add(signature)
            args = {"json": (payload | link.get("body", {})) if link.get("merge") else link.get("body", {})}
            response = requests.request(link.get("method", "GET"), link["href"], timeout=45, **args)
    response = requests.get(ASF, params={
        "platform": "NISAR", "processingLevel": "GCOV",
        "intersectsWith": f"POINT({point[0]} {point[1]})",
        "start": date_range.split("/")[0],
        "end": date_range.split("/")[1],
        "maxResults": 100, "output": "geojson",
    }, timeout=45)
    response.raise_for_status()
    return response.json()["features"]


def query(task, refresh):
    lake, mission, date_range = task
    start, end = date_range.split("/")
    path = CACHE / lake["id"] / f"{mission}_{start}_{end}.json"
    if path.exists() and not refresh:
        return
    results = search(lake, mission, date_range)
    save_json(path, results)
    print(lake["id"], mission, start, end, len(results), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", action="append")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    tasks = []
    for lake in load_json(CANDIDATES):
        if args.lake and lake["id"] not in args.lake:
            continue
        if "lon" not in lake:
            print(lake["id"], "pending verified study coordinates", flush=True)
            continue
        tasks.append((lake, "nisar", "2026-06-17/2026-11-15"))
        for year in (2017, 2020, 2024, 2025, 2026):
            tasks.append((lake, "optical", f"{year}-07-10/{year}-09-20"))
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(query, task, args.refresh): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except requests.RequestException as error:
                lake, mission, period = futures[future]
                failures.append((lake["id"], mission, period, str(error)))
                print("Catalog error:", failures[-1], flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
