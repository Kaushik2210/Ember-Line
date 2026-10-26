# Validation report: Punjab & Haryana, India

Period 2000-11-01 to 2026-06-30. Metric: `frp_sum_mw`. Grid: regular (0.25 deg). Day/night: both.

## Data

| source | min_date | max_date | rows |
|---|---|---|---|
| MODIS_SP | 2000-11-01 | 2026-08-01 | 1,127,226 |
| VIIRS_SNPP_SP | 2012-06-01 | 2026-06-30 | 2,162,581 |

Quality policy kept 1,749,134 of 1,967,014 detections (MODIS 482,397, VIIRS 1,266,737); 3 persistent heat-source cells masked.

## 1. The sensors disagree (raw, before normalisation)

**det_count**: VIIRS / MODIS over all overlap weeks = 4.70

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 18,626.00 | 85,232.00 | 31 | 4.58 |
| 2013 | 22,506.00 | 98,926.00 | 52 | 4.40 |
| 2014 | 22,515.00 | 111,831.00 | 52 | 4.97 |
| 2015 | 18,071.00 | 94,529.00 | 52 | 5.23 |
| 2016 | 26,318.00 | 127,836.00 | 52 | 4.86 |
| 2017 | 18,770.00 | 95,700.00 | 52 | 5.10 |
| 2018 | 22,194.00 | 101,318.00 | 53 | 4.57 |
| 2019 | 18,276.00 | 81,928.00 | 52 | 4.48 |
| 2020 | 22,284.00 | 102,188.00 | 52 | 4.59 |
| 2021 | 25,101.00 | 117,117.00 | 52 | 4.67 |
| 2022 | 18,241.00 | 81,798.00 | 52 | 4.48 |
| 2023 | 12,877.00 | 58,709.00 | 52 | 4.56 |
| 2024 | 11,515.00 | 49,041.00 | 53 | 4.26 |
| 2025 | 8,996.00 | 37,753.00 | 52 | 4.20 |
| 2026 | 2,844.00 | 21,994.00 | 25 | 7.73 |

**active_1km**: VIIRS / MODIS over all overlap weeks = 3.90

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 18,274.00 | 69,975.00 | 31 | 3.83 |
| 2013 | 22,106.00 | 80,203.00 | 52 | 3.63 |
| 2014 | 22,071.00 | 90,317.00 | 52 | 4.09 |
| 2015 | 17,734.00 | 77,701.00 | 52 | 4.38 |
| 2016 | 25,822.00 | 102,508.00 | 52 | 3.97 |
| 2017 | 18,449.00 | 78,251.00 | 52 | 4.24 |
| 2018 | 21,728.00 | 82,307.00 | 53 | 3.79 |
| 2019 | 17,916.00 | 66,453.00 | 52 | 3.71 |
| 2020 | 21,850.00 | 82,716.00 | 52 | 3.79 |
| 2021 | 24,578.00 | 94,363.00 | 52 | 3.84 |
| 2022 | 17,877.00 | 66,533.00 | 52 | 3.72 |
| 2023 | 12,685.00 | 49,262.00 | 52 | 3.88 |
| 2024 | 11,305.00 | 39,300.00 | 53 | 3.48 |
| 2025 | 8,843.00 | 30,840.00 | 52 | 3.49 |
| 2026 | 2,811.00 | 17,867.00 | 25 | 6.36 |

**frp_sum_mw**: VIIRS / MODIS over all overlap weeks = 1.73

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 296,134.00 | 564,418.19 | 31 | 1.91 |
| 2013 | 412,012.20 | 674,070.62 | 52 | 1.64 |
| 2014 | 397,646.80 | 772,765.19 | 52 | 1.94 |
| 2015 | 297,249.80 | 616,398.57 | 52 | 2.07 |
| 2016 | 479,416.90 | 855,533.73 | 52 | 1.78 |
| 2017 | 312,681.70 | 587,836.09 | 52 | 1.88 |
| 2018 | 397,051.80 | 641,805.14 | 53 | 1.62 |
| 2019 | 367,066.30 | 563,068.27 | 52 | 1.53 |
| 2020 | 412,786.60 | 702,255.52 | 52 | 1.70 |
| 2021 | 478,077.70 | 812,391.48 | 52 | 1.70 |
| 2022 | 333,744.60 | 542,167.06 | 52 | 1.62 |
| 2023 | 204,029.60 | 359,971.97 | 52 | 1.76 |
| 2024 | 210,849.40 | 303,561.34 | 53 | 1.44 |
| 2025 | 170,873.10 | 226,691.08 | 52 | 1.33 |
| 2026 | 46,152.80 | 124,146.06 | 25 | 2.69 |

## 2. Coincident overpasses: Aqua-MODIS vs SNPP-VIIRS

Pairs within 750 m and 30 min. 123,284 MODIS and 439,714 VIIRS detections were co-observed (100,300 MODIS / 827,023 VIIRS excluded because the other sensor had no detection nearby in that window).

- MODIS detections also seen by VIIRS: **32.7%**
- VIIRS detections also seen by MODIS: **13.5%**
- FRP of matched fires, VIIRS (summed over its pixels) / MODIS: median 0.60 (P10 0.18, P90 1.94, n=40,552)

by FRP (MW):

| frp_bin | n_modis | modis_corroborated | n_viirs | viirs_corroborated |
|---|---|---|---|---|
| <5 | 4,135 | 0.211 | 207,908 | 0.101 |
| 5-10 | 41,050 | 0.283 | 148,931 | 0.145 |
| 10-20 | 46,939 | 0.334 | 63,242 | 0.187 |
| 20-50 | 26,928 | 0.382 | 18,141 | 0.241 |
| >=50 | 4,232 | 0.425 | 1,492 | 0.313 |

by day/night:

| daynight | n_modis | modis_corroborated | n_viirs | viirs_corroborated |
|---|---|---|---|---|
| D | 122,819 | 0.325 | 435,784 | 0.134 |
| N | 465 | 0.789 | 3,930 | 0.240 |

by MODIS pixel size (km):

| scan_bin | n_modis | modis_corroborated |
|---|---|---|
| <1.5 | 98,514 | 0.335 |
| 1.5-2 | 14,925 | 0.287 |
| 2-3 | 7,836 | 0.331 |
| >=3 | 2,009 | 0.217 |

## 3. Normalisation (leave-one-year-out cross-validation)

734 overlapping weeks, years 2012-2026. Chosen model: **quantile**. `raw` and `scale` are baselines, not candidates.

| model | r2_log | mae_log | mae_raw | bias_rel | spearman | coverage |
|---|---|---|---|---|---|---|
| huber | 0.853 | 0.576 | 3,276.915 | -0.131 | 0.951 | 0.902 |
| theilsen | 0.853 | 0.578 | 3,331.418 | -0.131 | 0.951 | 0.901 |
| quantile | 0.892 | 0.514 | 2,490.434 | 0.014 | 0.959 | 0.899 |
| isotonic | 0.869 | 0.575 | 2,940.004 | -0.039 | 0.944 | 0.899 |
| raw | 0.769 | 0.922 | 5,132.177 | -0.423 | 0.951 | 0.902 |
| scale | 0.848 | 0.603 | 3,375.933 | 0.177 | 0.951 | 0.902 |

Interval half-width in log1p units: 1.144 at 90% nominal coverage.

### Terra-only years (before 2002-07-04)

Only Terra reported, so a separate model is calibrated on Terra's overlap with VIIRS (734 weeks). Chosen: **quantile**.

| model | r2_log | mae_log | mae_raw | bias_rel | spearman | coverage |
|---|---|---|---|---|---|---|
| huber | 0.583 | 1.107 | 8,339.137 | -0.594 | 0.792 | 0.901 |
| theilsen | 0.582 | 1.106 | 8,326.590 | -0.632 | 0.792 | 0.898 |
| quantile | 0.777 | 0.777 | 4,948.612 | 0.006 | 0.879 | 0.902 |
| isotonic | 0.614 | 1.103 | 8,249.890 | -0.405 | 0.773 | 0.899 |
| raw | -0.320 | 2.352 | 10,217.573 | -0.898 | 0.795 | 0.903 |
| scale | 0.538 | 1.200 | 10,759.706 | -0.161 | 0.793 | 0.903 |

## 4. Harmonised record

9,373 days, of which 4,225 reconstructed from MODIS.

## 5. Seasonality

Fire season (10% / 50% / 90% of cumulative activity): day of year 291 / 308 / 131, about 206 days long.

This region burns in more than one season:

- day of year 290 / 303 / 312 (about 23 days, 75% of seasonal activity)
- day of year 122 / 129 / 136 (about 15 days, 25% of seasonal activity)

STL decomposition of 1338 weekly totals (log1p scale): the seasonal component spans -5.25 to 5.19; the trend moves from 7.46 to 6.27.

## 6. Most unusual seasons

- 2024-25 was 3.8 robust standard deviations below the median of the other 23 fire years.
- 2023-24 was 1.6 robust standard deviations below the median of the other 23 fire years.
- 2001-02 was 1.5 robust standard deviations above the median of the other 23 fire years.
- 2019-20 was 1.3 robust standard deviations below the median of the other 23 fire years.
- 2002-03 was 1.3 robust standard deviations below the median of the other 23 fire years.

## 7. Sustained unusual periods

- 29 Oct 2001 to 13 Nov 2001 (16 days): activity ran 4.5 robust standard deviations below the typical level for those dates (peak 10.3). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 03 Nov 2024 to 06 Nov 2024 (4 days): activity ran 6.8 robust standard deviations below the typical level for those dates (peak 8.2). Baseline is built from the other years only.
- 16 Oct 2023 to 19 Oct 2023 (4 days): activity ran 4.7 robust standard deviations below the typical level for those dates (peak 6.4). Baseline is built from the other years only.
- 12 Nov 2000 to 17 Nov 2000 (6 days): activity ran 2.9 robust standard deviations below the typical level for those dates (peak 4.5). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 02 May 2020 to 06 May 2020 (5 days): activity ran 3.1 robust standard deviations below the typical level for those dates (peak 3.6). Baseline is built from the other years only.
- 25 Sep 2001 to 30 Sep 2001 (6 days): activity ran 2.5 robust standard deviations above the typical level for those dates (peak 3.4). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 31 Oct 2019 to 02 Nov 2019 (3 days): activity ran 4.8 robust standard deviations below the typical level for those dates (peak 7.6). Baseline is built from the other years only.
- 16 Nov 2001 to 20 Nov 2001 (5 days): activity ran 2.6 robust standard deviations below the typical level for those dates (peak 4.2). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.

## 8. Data-quality timeline

Platforms present in the loaded data:

| sensor | platform | first | last | detections |
|---|---|---|---|---|
| modis | Terra | 2000-11-01 | 2026-06-30 | 119,114 |
| modis | Aqua | 2002-07-13 | 2026-06-29 | 386,448 |
| viirs | SNPP | 2012-06-01 | 2026-06-30 | 1,461,452 |

Documented events (NASA sources; undated where the source gives no date):

- **2000-11** Terra active-fire record begins. NASA describes high quality active fire observations from Terra as available starting November 2000. Until Aqua, MODIS fire data come from one satellite, with fewer overpasses. [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2002-05-04** Aqua launched. Second MODIS, on Aqua, which crosses the equator in the afternoon (south to north). [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2002-07-04** Aqua active-fire record begins. High quality active fire observations from Aqua start on this date. From here MODIS samples the day twice at different local times (Terra morning, Aqua afternoon). [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2011-10-28** VIIRS launched on Suomi NPP. First VIIRS sensor, with 375 m I-band channels used for active fire detection. [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5189)
- **2012-01-20** Suomi NPP VIIRS fire record begins in FIRMS. FIRMS lists S-NPP VIIRS 375 m active fire temporal coverage as starting 20 January 2012. This is the start of the overlap with MODIS used to fit the normalisation. [source](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
- **2015** VIIRS 375 m fire radiative power uses 750 m data from 2015. FIRMS states that FRP retrievals combine 375 m and 750 m data and that starting in 2015 the algorithm incorporated the M13 channel. FRP may not be homogeneous across this change; the source gives the year only. [source](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
- **2017-11-18** VIIRS launched on NOAA-20. Second VIIRS sensor, on NOAA-20 (not used in this version of the harmonisation). [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5189)
- **2020-02-27** Terra's last inclination maneuver; orbit drift begins. After the final maneuver on this date Terra was allowed to drift to an earlier equator crossing than 10:30. NASA expects the impact on science to be minimal, but the morning sampling time of Terra-MODIS fire detections is no longer fixed after this point. [source](https://terra.nasa.gov/about/terras-orbit-changes/terra-orbital-drift-information)
- **undated** MODIS Collection 6.1 processing. FIRMS near-real-time MODIS data use Collection 6.1. NASA says C6.1 contains no change to the science algorithm; changes improve the calibration of the Level 1B inputs. The source page gives no switch-over date, so none is placed on the timeline. [source](https://www.earthdata.nasa.gov/data/catalog/lancemodis-mcd14dl-6.1nrt)

## Notes

- 3 persistent heat-source cells (flares, industry, volcanoes) were removed.
- MODIS reports from Terra alone before 2002-07-18, with fewer overpasses; reconstructed values there are less certain.
- VIIRS is observed from 2012-06-01; 4230 days have no data.
- Prediction intervals are about x3.1 wide on weekly totals at 90% nominal coverage: the sensors' weekly totals disagree by more than a constant factor.
- Before 2002-07-04 only Terra reports, with far fewer detections. Those weeks use a Terra-only model (quantile, cross-validated error 0.78 in log units, intervals about x6.6) so they are not mistaken for quiet years.
- 4225 of 9373 days are reconstructed from MODIS (VIIRS-equivalent, with prediction bands); the rest are observed by VIIRS.
