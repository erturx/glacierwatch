"""Assemble the web inventory from reviewed and exported observations."""
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
        lakes.append(data)
    save_json(OUT / "inventory.json", {"lakes": lakes})


if __name__ == "__main__":
    main()
