# Scientific method

The viewer compares only pairs on the same analysis grid with 100% eligible pixels in the individual lake and shoreline checks and in the union of both mapped outlines plus a three-pixel shoreline buffer. The nominal decrease must reach 0.005 km². The difference between the earlier lower sensitivity bound and the later upper bound must reach 20% of the earlier upper bound. These display thresholds screen out small changes. For other series, the viewer presents the observations one date at a time.

## Observation discovery and geometry

`pipeline/catalog.py` queries ASF Search for NISAR GCOV and Element 84 Earth Search for Sentinel-2 L2A. It searches a point on the identified lake. Footprints only establish candidates. Lake and shore pixels are tested in raster subsets before export. When the catalog returns more than a page of items, the search follows the catalog's next link.

The analysis uses documented study points, WGS84 and a metric UTM grid. Published basin outlines from Piroton, Emmer and Havenith inform which connected water body belongs to each lake. The basin search extends beyond the source inventory outline. A detected component reaching the study boundary fails the final quality gate. The Batken locator uses the union of the 2016 and 2024 outlines of the same basin, buffered by 20 m before simplification. [Glacial lakes of Kyrgyzstan](https://doi.org/10.5281/zenodo.17869915)

## Sentinel-2 optical observations

1. Read small windows from the COG distribution. Resample reflectance onto a fixed 10 m UTM grid by bilinear interpolation and scene classification by nearest neighbour. B11 (SWIR) and scene classification are acquired on a 20 m grid.
2. Convert digital numbers using the item-level BOA correction state and scale. The SCL-water NIR sanity check rejected a September 2026 candidate whose reflectance exceeded the workflow's screening limits. Mask missing, cloud, cirrus, cloud shadow, dark/topographic shadow, snow/ice and unclassified cells. Eligible SCL classes are 4, 5 and 6.
3. Select open-water candidates where NDWI = (green − NIR) / (green + NIR) exceeds 0.06, MNDWI = (green − SWIR) / (green + SWIR) exceeds 0.18, and NIR reflectance is below 0.16. Keep an eight-connected component overlapping the lake locator. RGB inspection supports the spectral check. SCL is a quality mask and a cross-check. Its water label can omit anisotropic and mixed shore cells, especially on small lakes.
4. Vary both index thresholds by ±0.05. Include the base classification in the resulting envelope and add unidentified cells in the lake/shore check footprint to the upper end.

## NASA–ISRO NISAR radar observations

Harmony extracted Frequency A HHHH, `mask` and `numberOfLooks` as native 20 m GeoTIFF cutouts. Compare only the same track, direction, collection and Composite Release ID. Valid HH × HH is finite and positive, the subswath flag is 1–254, and the look count is at least 3. The retained mask describes fully focused radar samples. It supplies no guarantee of freedom from layover, shadow, wind or floating ice. [GCOV product documentation](https://nisar-docs.asf.alaska.edu/gcov/) · [Product availability and CRIDs](https://nisar-docs.asf.alaska.edu/availability-overview/)

Convert the diagonal covariance term from linear gamma-zero power to dB using 10 log10. Take the local mean over a 3×3 valid-pixel neighbourhood with at least five valid cells. The threshold of −14.5 dB was selected from an optical-overlap screen on the August scene. The same cutoff was applied to the September scene. Keep the dark cluster overlapping the mapped basin and review the shoreline on the actual radar chips. The accepted pair uses track 63 descending and P05023. An October P05036 candidate was evaluated independently and excluded from the temporal series. The separate October calibration and late-season conditions make a direct change comparison inappropriate here.

The sensitivity envelope varies the threshold by ±1.5 dB and treats excluded cells in the lake/shore check footprint as potential open water in the upper value. An independent optical scene was used for each radar date. Agreement is intersection over union for the two water masks on shared eligible pixels. Only the August reference helped choose the cutoff. Cloud, unequal acquisition times and spatial resolution limit these corroboration checks.

## Area, export and comparison

Area is the count of water cells multiplied by the pixel area (100 m² optical, 400 m² radar), divided by 1,000,000 for km². NoData is 255 and remains excluded. GeoTIFF value 1 is mapped water. Value 0 is eligible background or outside the selected lake component. The exported GeoJSON is derived from the mask and reprojected to WGS84. The visualization and its outline overlay share the same source grid.

Change is B minus A. Relative change is 100 × (B − A) / A. The viewer explains overlap of the sensitivity envelopes and flags dates separated by more than 21 calendar-season days. Sensitivity ranges are deterministic screening bounds and carry no statistical confidence level.
