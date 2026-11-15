# GlacierWatch

**Challenge.** NASA Space Apps Challenge 2026, Dancing with the SARs.

**Live demonstration.** [GlacierWatch](https://glacierwatch.tastyring263.chatgpt.site/)

**Public source.** [erturx/glacierwatch](https://github.com/erturx/glacierwatch)

**Pitch slides.** [GlacierWatch PowerPoint](../pitch/GlacierWatch.pptx)

## Short description

GlacierWatch lets researchers compare glacial lake shorelines in Kyrgyzstan using NASA–ISRO NISAR and Copernicus Sentinel-2. The explorer shows two acquisitions, their mapped open-water areas and the source and quality of each estimate. It covers Petrov Lake, Lake Ala-Kol and two distinct basins in the Adygine cascade.

## What we did and what we found

We used NASA Harmony to extract the L-band HH backscatter, subswath mask and number of looks from two NISAR Level-2 GCOV granules over Petrov Lake. The acquisitions use the same track and processing release. We measured 4.53 km² on 17 August 2026 and 4.47 km² on 10 September 2026. The estimated difference of −0.06 km² is within the sensitivity of the method. Nearby Sentinel-2 dates corroborate the radar outlines on the shared clear pixels, with 81% and 89% intersection over union. The optical series adds historical context, with the earliest reviewed observation in July 2017 at Ala-Kol.

The app runs from published, precomputed imagery, masks and metadata. Visitors can trace every observation to its granule without an Earthdata account. The offline pipeline and the small NISAR cutouts are published for reproduction. Clouds, ice, shadow and shoreline mixtures limit what each observation can resolve. The project supports research review of observable surface area and is unsuitable for operational flood warnings.

## NASA and other data

- [NASA–ISRO NISAR Level-2 GCOV PROVISIONAL v1](https://doi.org/10.5067/NIL2GCOV-P1) supplied the radar image and the two direct Petrov area estimates.
- [NASA Harmony](https://nisar-docs.asf.alaska.edu/harmony/) extracted the three science and quality layers to GeoTIFF.
- [Copernicus Sentinel-2 Level-2A](https://sentiwiki.copernicus.eu/web/s2-products) supplied optical lake estimates and corroborating imagery.
- [Complete data ledger and lake research](https://github.com/erturx/glacierwatch/blob/main/docs/data-sources.md)

## AI-use disclosure

OpenAI Codex assisted with research, implementation, testing and drafting. Satellite interpretation in the app comes from deterministic offline image processing and documented quality checks.

## Spoken pitch

How much of a glacial lake’s apparent change survives a quality check? We built GlacierWatch so researchers in Kyrgyzstan can examine that question directly. Choose a lake and two acquisitions. The app shows real satellite pixels, the mapped shorelines and the estimated change, with the source and exclusions one click away.

At Petrov Lake we used two NASA–ISRO NISAR radar passes from the same track. We measured 4.53 and 4.47 square kilometres of open water. The sensitivity ranges overlap, so the two scenes do not establish a resolved loss of water. Near-date Sentinel-2 observations give us an independent check on the shape of each radar outline.

The public demo covers four lakes and the optical archive begins in 2017. Every estimate can be traced to its granule and reproduced with the published workflow. That gives mountain-lake researchers a quicker way to decide where a closer look is warranted.
