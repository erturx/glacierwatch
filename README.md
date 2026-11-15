# GlacierWatch

**[Open the live GlacierWatch explorer](https://glacierwatch.tastyring263.chatgpt.site/)**

Satellite observations of glacial lake surface extent in Kyrgyzstan. Built for **NASA Space Apps Challenge 2026 — Dancing with the SARs**.

GlacierWatch lets researchers and judges inspect the same lake on two dates, see the pixels behind each measured shoreline and trace each value to the originating product. The app is a research demonstration. It shows observable open-water extent and is unsuitable for emergency decisions or forecasts.

## Explore

- **Petrov Lake**, a moraine-dammed lake in Ak-Shyirak. Compare both same-track NASA–ISRO NISAR radar acquisitions and a separate Sentinel-2 optical series.
- **Lake Ala-Kol**, a glacier-fed lake in the Teskey Range. A historical optical view is available from 2017. Some shore pixels are excluded and the coverage limitation is shown with each estimate.
- **Adygine Lake 2**, the middle basin of the Ala-Archa glacier lake cascade. Field monitoring documents its surface outlet.
- **Adygine Lake 3**, the separate upper glacier-contact basin. Its small size makes shore pixels sensitive to sensor resolution and classifier thresholds.

Select two reviewed acquisition dates, drag the split view, toggle the water outlines and open the source records. The lake map shows georeferenced water boundaries. The public viewer uses precomputed assets and requires no NASA account.

## NISAR result

On Petrov Lake, two 20 m, track 63 descending, Frequency A HH observations from 17 August and 10 September 2026 produced mapped extents of **4.53 km² and 4.47 km²**. The indicative difference is **−0.06 km²**, or **−1.4%**. The sensitivity ranges overlap, so the difference is unresolved. Near-date Sentinel-2 imagery corroborates the shoreline shape on shared clear pixels, with 81% and 89% intersection over union. The references are three and eight days away from the corresponding radar observation.

## Data sources

- NASA / Alaska Satellite Facility DAAC provides **NASA–ISRO NISAR L2 GCOV**. The website comparison uses two `NISAR_L2_GCOV_PROVISIONAL_V1` granules, both CRID P05023. NASA Harmony generated the cutouts from Frequency A HH × HH, its subswath mask, and its number-of-looks layer. [ASF GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/) · [NASA Harmony documentation](https://harmony.earthdata.nasa.gov/docs)
- **Copernicus Sentinel-2 MSI Level-2A** surface reflectance, available through Element 84's public Earth Search COG archive. It supplies optical comparisons and independent checks for NISAR. Contains modified Copernicus Sentinel data 2017, 2020, 2024–2026. [Sentinel-2 documentation](https://sentiwiki.copernicus.eu/web/s2-products) · [Earth Search collection](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a)
- The [Kyrgyz glacial-lake inventory](https://doi.org/10.5281/zenodo.17869915) identifies basin locations and independent reference footprints. [Natural Earth](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/) provides regional map boundaries. Lake-specific field and historical research is listed in [lake selection](docs/lake-selection.md).

[Full source and granule ledger](docs/data-sources.md) · [Machine-readable observation inventory](dist/data/inventory.json)

[Submission copy and spoken pitch](docs/submission.md)

## Run locally

With Python installed, start the static site and visit [localhost:8765](http://localhost:8765).

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

The site runs directly from the checked-in `dist/` directory. The offline pipeline needs Python 3.14 and the packages below. Public STAC access and windowed HTTPS reads are required to rebuild the Sentinel-2 assets. The two small, checksummed sets of original Harmony cutouts are included for radar reproducibility. To retrieve them again, the radar pipeline supports a NASA Earthdata user token through the environment variable `EARTHDATA_TOKEN`. Browser-authenticated Harmony requests are documented in the source ledger.

```sh
python -m pip install -r requirements.txt
python pipeline/geography.py
python pipeline/catalog.py --lake petrov --lake alakol --lake adygine2 --lake adygine3
python pipeline/optical.py
python pipeline/radar.py
python pipeline/inventory.py
python pipeline/verify.py
python pipeline/report.py
```

The catalog and cutout caches are ignored by Git. The reviews in `pipeline/review.json` and `pipeline/radar-review.json` enumerate the accepted observations. Screening more scenes uses `pipeline/optical.py --scout --lake <id>`. See [scientific method](docs/scientific-method.md), [quality checks](docs/quality-report.md) and [limitations](docs/limitations.md).

## AI-use disclosure

OpenAI Codex assisted with research, implementation, test execution and drafting. The site uses deterministic offline image processing. Its satellite pixels and area values come from the cited source products, and the imagery and outlines can be audited independently.

Thank you to NASA, ISRO, ASF DAAC, Copernicus, Element 84, Natural Earth and the authors of the cited Kyrgyz lake studies. GlacierWatch is a participant project and does not represent NASA.
