"""Assemble the web inventory from reviewed and exported observations."""
from itertools import combinations

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

from catalog import load_json, save_json
from optical import OUT, ACCEPTED


def verify_pair(series):
    dates = series["defaultDates"]
    items = {item["id"]: item for item in series["observations"]}
    if dates[0] not in items or dates[1] not in items or items[dates[0]]["datetime"] >= items[dates[1]]["datetime"]:
        raise ValueError(f"Invalid default comparison {dates}")
    for obs in items.values():
        for file in obs["files"].values():
            if not (OUT.parent / file).is_file():
                raise FileNotFoundError(file)


def reviewed_reductions(observations):
    pairs = []
    for before, after in combinations(observations, 2):
        a, b = before["quality"], after["quality"]
        if any(q["validFraction"] != 1 or q["unknownKm2"] != 0 for q in (a, b)):
            continue
        minimum_loss = a["lowKm2"] - b["highKm2"]
        if before["areaKm2"] - after["areaKm2"] < .005 or minimum_loss < .20 * a["highKm2"]:
            continue
        with rasterio.open(OUT.parent / before["files"]["mask"]) as src_a, \
             rasterio.open(OUT.parent / after["files"]["mask"]) as src_b:
            if (src_a.crs, src_a.transform, src_a.shape) != (src_b.crs, src_b.transform, src_b.shape):
                continue
            mask_a, mask_b = src_a.read(1, masked=True), src_b.read(1, masked=True)
        shoreline = binary_dilation((mask_a.filled(0) == 1) | (mask_b.filled(0) == 1), iterations=3)
        if not (np.ma.getmaskarray(mask_a) | np.ma.getmaskarray(mask_b))[shoreline].any():
            pairs.append([before["id"], after["id"]])
    return pairs


def main():
    lakes = []
    for key in load_json(ACCEPTED):
        data = load_json(OUT / key / "observations.json")
        optical = {
            "key": "optical", "defaultDates": data.pop("defaultDates"),
            "observations": data.pop("observations"),
        }
        data["series"] = [optical]
        radar_path = OUT / key / "radar.json"
        if radar_path.exists():
            obs = load_json(radar_path)
            if len(obs) >= 2:
                same_group = {(o["track"], o["direction"], o["maturity"], o["release"]) for o in obs}
                if len(same_group) != 1:
                    raise ValueError(f"Incompatible radar observations for {key}")
                data["series"].insert(0, {
                    "key": "radar", "defaultDates": [obs[0]["id"], obs[-1]["id"]], "observations": obs,
                })
        for entry in data["series"]:
            verify_pair(entry)
            entry["comparisons"] = reviewed_reductions(entry["observations"])
        lakes.append(data)
    lakes.sort(key=lambda lake: not any(series["comparisons"] for series in lake["series"]))
    save_json(OUT / "inventory.json", {"lakes": lakes})


if __name__ == "__main__":
    main()
