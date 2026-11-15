"""Generate the source ledger and numerical quality report from the published inventory."""
from catalog import ROOT, load_json
from optical import OUT

LEDGER_INTRO = """# Data sources and granules

Every row below contributes to the public measurements or their checks. Timestamps are UTC.

- **NASA–ISRO NISAR L-band SAR**, NASA / ASF DAAC, Geocoded Polarimetric Covariance L2. The two public observations use version 1 PROVISIONAL, CRID P05023, Frequency A HH × HH, and nominal 20 m posting. Their views and numerical areas come from those rasters. The native subsetting boxes, job IDs, filenames and SHA-256 hashes are in [the inventory](../dist/data/inventory.json). The included cutouts preserve the source GeoTIFFs and metadata. [ASF GCOV documentation](https://nisar-docs.asf.alaska.edu/gcov/) · [NASA collection DOI](https://doi.org/10.5067/NIL2GCOV-P1)
- **ESA / Copernicus Sentinel-2 A/B/C MSI**, Level-2A bottom-of-atmosphere surface reflectance from Element 84 Earth Search `sentinel-2-l2a`. B02, B03, B04, B08 and B11 and the SCL quality layer provide backgrounds, numerical optical extent and cross-sensor checks. Raster URLs and BOA metadata are recorded in the inventory. Some Earth Search items expose a full SAFE product identifier in place of a tile-granule identifier. [Sentinel-2 Level-2A](https://sentiwiki.copernicus.eu/web/s2-products) · [Earth Search](https://github.com/Element84/earth-search)
- **Glacial lakes of Kyrgyzstan (2016 & 2024)**, Piroton, Emmer and Havenith. Published 2024 geometries locate basin seeds and support identity checks. See the attributed source and row identifiers in [reference geometries](../pipeline/reference-geometries.json). [Zenodo](https://doi.org/10.5281/zenodo.17869915)
- **Natural Earth**, 1:50m admin-0 country boundaries, for geographic context. Public-domain data. [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/)
- For independently published lake history, see [lake selection](lake-selection.md).

## Measurements displayed

| Lake | Mission and baseline/CRID | Acquired UTC | Full provider granule or SAFE product | Role |
| --- | --- | --- | --- | --- |
"""


def fmt(obs):
    return f'`{obs["granule"]}` ([source]({obs["source"]}))'


def write(name, lines):
    path = ROOT / "docs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main():
    lakes = load_json(OUT / "inventory.json")["lakes"]
    ledger = [LEDGER_INTRO.rstrip()]
    validations = []
    flags = [
        "# Observation quality",
        "",
        "The exported GeoTIFF cells, WGS84 boundary and display pixels were reconciled using `pipeline/verify.py`. "
        "The analysis confirms the reported areas and their provenance. Independent field measurements for the displayed dates remain unavailable.",
        "",
        "| Lake and series | UTC date | Mapped water (km²) | Sensitivity low–high (km²) | Eligible lake/shore support | Relative quality |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for lake in lakes:
        for series in lake["series"]:
            radar = series["key"] == "radar"
            for obs in series["observations"]:
                q = obs["quality"]
                version = obs.get("release", obs.get("baseline"))
                role = "HH backscatter, water detection and area" if radar else "RGB imagery, water detection and area"
                ledger.append(f'| {lake["name"]} | {obs["satellite"]} {version} | {obs["datetime"]} | {fmt(obs)} | {role} |')
                flags.append(
                    f'| {lake["name"]} · {series["key"]} | {obs["datetime"][:10]} | {obs["areaKm2"]:.4f} | '
                    f'{q["lowKm2"]:.4f}–{q["highKm2"]:.4f} | {q["validFraction"]:.1%} | {q["status"]} |'
                )
                if radar:
                    c = q["opticalComparison"]
                    validations.append((lake["name"], obs, c))
    ledger.extend([
        "", "## Independent optical agreement checks", "",
        "| Lake | Radar date | Sentinel-2 reference UTC and baseline | Reference product | Shared-pixel IoU |",
        "| --- | --- | --- | --- | ---: |",
    ])
    for lake, radar, optical in validations:
        ledger.append(
            f'| {lake} | {radar["datetime"][:10]} | {optical["datetime"]}, {optical["baseline"]} | '
            f'{fmt(optical)} | {optical["iou"]:.1%} |'
        )
    ledger.extend([
        "", "## Harmony retrieval and investigated datasets", "",
        "The authenticated browser session submitted explicit CMR granule IDs and a lake bounding box to Harmony. The request is reproducible with the CMR collection, granule IDs, box and layer fields in [radar inputs](../pipeline/radar-inputs.json). Harmony result URLs are temporary. For regeneration, use the archived small cutouts or submit the same request under Earthdata Login.",
        "",
        "The workflow also inspected a VALIDATED P05036 scene over Petrov and two PROVISIONAL scenes over Lower Merzbacher. Those exploratory detections do not enter the comparison or observation inventory. [Candidate screening](lake-selection.md) · [Known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)",
    ])
    flags.extend([
        "", "## Interpretation", "",
        "- NISAR's 17 August and 10 September Petrov extents differ by approximately −0.06 km². Both are compatible within the tested sensitivity ranges. Approximate shared-pixel optical agreement is 81% and 89%. Independent reference dates differ by three and eight days.",
        "- Full-quality comparison requires at least 95% eligible support in the lake/shore check and a water component that stays inside the study basin. For Ala-Kol, the reviewed coverage-limited tier allows at least 90% eligible support. Its contiguous outline is visible on RGB and unknown pixels contribute to the upper sensitivity bound. The result remains informative as observable area, with all default changes unresolved.",
        "- The 10 m optical mask inherits 20 m SWIR and SCL limitations. Refer to the individual scene records for sensor availability and edge notes.",
    ])
    write("data-sources.md", ledger)
    write("quality-report.md", flags)


if __name__ == "__main__":
    main()
