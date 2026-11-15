# Data sources and granules

Every row below contributes to the public measurements or their checks. Timestamps are UTC.

- **NASA–ISRO NISAR L-band SAR**, NASA / ASF DAAC, Geocoded Polarimetric Covariance L2. The two public observations use version 1 PROVISIONAL, CRID P05023, Frequency A HH × HH, and nominal 20 m posting. Their views and numerical areas come from those rasters. The native subsetting boxes, job IDs, filenames and SHA-256 hashes are in [the inventory](../dist/data/inventory.json). The included cutouts preserve the source GeoTIFFs and metadata. [ASF GCOV documentation](https://nisar-docs.asf.alaska.edu/gcov/) · [NASA collection DOI](https://doi.org/10.5067/ASF/NISAR/L2_GCOV_PROVISIONAL_V1)
- **ESA / Copernicus Sentinel-2 A/B/C MSI**, Level-2A bottom-of-atmosphere surface reflectance from Element 84 Earth Search `sentinel-2-l2a`. B02, B03, B04, B08 and B11 and the SCL quality layer provide backgrounds, numerical optical extent and cross-sensor checks. Raster URLs and BOA metadata are recorded in the inventory. Some Earth Search items expose a full SAFE product identifier in place of a tile-granule identifier. [Sentinel-2 Level-2A](https://sentiwiki.copernicus.eu/web/s2-products) · [Earth Search](https://github.com/Element84/earth-search)
- **Glacial lakes of Kyrgyzstan (2016 & 2024)**, Piroton, Emmer and Havenith. Published 2024 geometries locate basin seeds and support identity checks. See the attributed source and row identifiers in [reference geometries](../pipeline/reference-geometries.json). [Zenodo](https://doi.org/10.5281/zenodo.17869915)
- **Natural Earth**, 1:50m admin-0 country boundaries, for geographic context. Public-domain data. [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/)
- For independently published lake history, see [lake selection](lake-selection.md).

## Measurements displayed

| Lake | Mission and baseline/CRID | Acquired UTC | Full provider granule or SAFE product | Role |
| --- | --- | --- | --- | --- |
| Petrov Lake | NASA–ISRO NISAR P05023 | 2026-08-17T13:52:31Z | `NISAR_L2_PR_GCOV_028_063_D_067_2005_DHDH_A_20260817T135231_20260817T135306_P05023_N_F_J_001` ([source](https://search.earthdata.nasa.gov/search/granules?p=C2854338529-ASF&pg[0][id]=G4285596420-ASF)) | HH backscatter, water detection and area |
| Petrov Lake | NASA–ISRO NISAR P05023 | 2026-09-10T13:52:31Z | `NISAR_L2_PR_GCOV_030_063_D_067_2005_DHDH_A_20260910T135231_20260910T135306_P05023_N_F_J_001` ([source](https://search.earthdata.nasa.gov/search/granules?p=C2854338529-ASF&pg[0][id]=G4309891477-ASF)) | HH backscatter, water detection and area |
| Petrov Lake | Sentinel-2A 05.00 | 2020-07-16T05:47:26.502000Z | `S2A_OPER_MSI_L2A_TL_S2RP_20230323T160944_A026457_T44TKM_N05.00` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_44TKM_20200716_3_L2A)) | RGB imagery, water detection and area |
| Petrov Lake | Sentinel-2A 05.11 | 2025-07-12T05:47:40.675000Z | `S2A_MSIL2A_20250712T054251_N0511_R005_T44TKM_20250712T085313.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_44TKM_20250712_0_L2A)) | RGB imagery, water detection and area |
| Petrov Lake | Sentinel-2A 05.12 | 2026-07-27T05:47:39.329000Z | `S2A_MSIL2A_20260727T054251_N0512_R005_T44TKM_20260727T085910.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_44TKM_20260727_0_L2A)) | RGB imagery, water detection and area |
| Lake Ala-Kol | Sentinel-2B 00.01 | 2017-07-27T05:38:54.945000Z | `S2B_OPER_MSI_L2A_TL_SHIT_20200331T012610_A002033_T44TKM_N00.01` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_44TKM_20170727_0_L2A)) | RGB imagery, water detection and area |
| Lake Ala-Kol | Sentinel-2B 05.11 | 2024-08-09T05:47:10.686000Z | `S2B_OPER_MSI_L2A_TL_2BPS_20240809T094816_A038784_T43TGH_N05.11` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_43TGH_20240809_0_L2A)) | RGB imagery, water detection and area |
| Lake Ala-Kol | Sentinel-2B 05.12 | 2026-08-29T05:47:03.892000Z | `S2B_MSIL2A_20260829T053639_N0512_R005_T43TGH_20260829T091959.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_43TGH_20260829_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 2 | Sentinel-2A 05.11 | 2024-08-20T06:07:09.216000Z | `S2A_OPER_MSI_L2A_TL_2APS_20240820T102355_A047850_T43TDH_N05.11` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_43TDH_20240820_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 2 | Sentinel-2B 05.11 | 2025-08-10T06:07:12.323000Z | `S2B_MSIL2A_20250810T055639_N0511_R091_T43TDH_20250810T080656.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_43TDH_20250810_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 2 | Sentinel-2C 05.12 | 2026-08-17T05:57:16.360000Z | `S2C_MSIL2A_20260817T054631_N0512_R048_T43TDH_20260817T085418.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2C_43TDH_20260817_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 3 | Sentinel-2A 05.11 | 2024-08-27T05:57:11.441000Z | `S2A_OPER_MSI_L2A_TL_2APS_20240827T104448_A047950_T43TDH_N05.11` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_43TDH_20240827_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 3 | Sentinel-2B 05.11 | 2025-08-30T06:07:11.284000Z | `S2B_MSIL2A_20250830T055639_N0511_R091_T43TDH_20250830T081340.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_43TDH_20250830_0_L2A)) | RGB imagery, water detection and area |
| Adygine Lake 3 | Sentinel-2B 05.12 | 2026-09-14T06:07:08.120000Z | `S2B_MSIL2A_20260914T055629_N0512_R091_T43TDH_20260914T093941.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_43TDH_20260914_0_L2A)) | RGB imagery, water detection and area |

## Independent optical agreement checks

| Lake | Radar date | Sentinel-2 reference UTC and baseline | Reference product | Shared-pixel IoU |
| --- | --- | --- | --- | ---: |
| Petrov Lake | 2026-08-17 | 2026-08-14T05:47:20.116000Z, 05.12 | `S2C_MSIL2A_20260814T053641_N0512_R005_T44TKM_20260814T085710.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2C_44TKM_20260814_0_L2A)) | 81.1% |
| Petrov Lake | 2026-09-10 | 2026-09-18T05:47:19.991000Z, 05.12 | `S2B_MSIL2A_20260918T053639_N0512_R005_T44TKM_20260918T092317.SAFE` ([source](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_44TKM_20260918_1_L2A)) | 88.7% |

## Harmony retrieval and investigated datasets

The authenticated browser session submitted explicit CMR granule IDs and a lake bounding box to Harmony. The request is reproducible with the CMR collection, granule IDs, box and layer fields in [radar inputs](../pipeline/radar-inputs.json). Harmony result URLs are temporary. For regeneration, use the archived small cutouts or submit the same request under Earthdata Login.

The workflow also inspected a VALIDATED P05036 scene over Petrov and two PROVISIONAL scenes over Lower Merzbacher. Those exploratory detections do not enter the comparison or observation inventory. [Candidate screening](lake-selection.md) · [Known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)
