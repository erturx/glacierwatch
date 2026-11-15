# Observation quality

The exported GeoTIFF cells, WGS84 boundary and display pixels were reconciled using `pipeline/verify.py`. The analysis confirms the reported areas and their provenance. Independent field measurements for the displayed dates remain unavailable.

| Lake and series | UTC date | Mapped water (km²) | Sensitivity low–high (km²) | Eligible lake/shore support | Relative quality |
| --- | --- | ---: | ---: | ---: | --- |
| Batken Glacial Lake · optical | 2024-09-04 | 0.0135 | 0.0122–0.0143 | 100.0% | Reviewed |
| Batken Glacial Lake · optical | 2024-09-14 | 0.0078 | 0.0036–0.0087 | 100.0% | Reviewed |
| Petrov Lake · radar | 2026-08-17 | 4.5288 | 3.8788–4.8576 | 99.9% | Reviewed |
| Petrov Lake · radar | 2026-09-10 | 4.4676 | 3.8076–4.8356 | 99.9% | Reviewed |
| Petrov Lake · optical | 2020-07-16 | 3.8775 | 3.8614–4.2248 | 95.0% | Reviewed |
| Petrov Lake · optical | 2025-07-12 | 4.2899 | 4.0313–4.5570 | 95.0% | Reviewed |
| Petrov Lake · optical | 2026-07-27 | 4.0479 | 4.0293–4.2792 | 98.4% | Reviewed |
| Lake Ala-Kol · optical | 2017-07-27 | 1.2002 | 1.1865–1.3309 | 91.6% | Coverage-limited |
| Lake Ala-Kol · optical | 2024-08-09 | 1.2068 | 1.2015–1.3299 | 91.6% | Coverage-limited |
| Lake Ala-Kol · optical | 2026-08-29 | 1.1922 | 1.1849–1.3222 | 91.3% | Coverage-limited |

## Interpretation

- NISAR's 17 August and 10 September Petrov extents differ by approximately −0.06 km². Both are compatible within the tested sensitivity ranges. Approximate shared-pixel optical agreement is 81% and 89%. Independent reference dates differ by three and eight days.
- The before-and-after viewer requires 100% eligible coverage on both dates and over the combined water outline plus its shoreline buffer. The nominal decrease must reach 0.005 km² and the conservative decrease must reach 20% of the earlier upper estimate.
- The 10 m optical mask inherits 20 m SWIR and SCL limitations. Refer to the individual scene records for sensor availability and edge notes.
