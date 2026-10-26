# Validation report: Punjab & Haryana, India

Period 2000-11-01 to 2015-06-30. Metric: `frp_sum_mw`. Grid: regular (0.25 deg). Day/night: both.

## Data

| source | min_date | max_date | rows |
|---|---|---|---|
| MODIS_SP | 2000-11-01 | 2026-07-16 | 521,643 |
| VIIRS_SNPP_SP | 2012-06-01 | 2019-11-07 | 483,383 |

Quality policy kept 595,989 of 650,098 detections (MODIS 280,681, VIIRS 315,308); 1 persistent heat-source cells masked.

## 1. The sensors disagree (raw, before normalisation)

**det_count**: VIIRS / MODIS over all overlap weeks = 4.66

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 18,626.00 | 85,238.00 | 31 | 4.58 |
| 2013 | 22,506.00 | 98,938.00 | 52 | 4.40 |
| 2014 | 22,515.00 | 111,839.00 | 52 | 4.97 |
| 2015 | 3,780.00 | 18,518.00 | 25 | 4.90 |

**active_1km**: VIIRS / MODIS over all overlap weeks = 3.86

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 18,274.00 | 69,981.00 | 31 | 3.83 |
| 2013 | 22,106.00 | 80,214.00 | 52 | 3.63 |
| 2014 | 22,071.00 | 90,325.00 | 52 | 4.09 |
| 2015 | 3,694.00 | 14,955.00 | 25 | 4.05 |

**frp_sum_mw**: VIIRS / MODIS over all overlap weeks = 1.80

| year | modis | viirs | weeks | viirs/modis |
|---|---|---|---|---|
| 2012 | 296,134.00 | 564,426.66 | 31 | 1.91 |
| 2013 | 412,012.20 | 674,084.15 | 52 | 1.64 |
| 2014 | 397,646.80 | 772,774.76 | 52 | 1.94 |
| 2015 | 72,515.60 | 114,501.46 | 25 | 1.58 |

## 2. Coincident overpasses: Aqua-MODIS vs SNPP-VIIRS

Pairs within 750 m and 30 min. 31,923 MODIS and 116,061 VIIRS detections were co-observed (25,048 MODIS / 199,247 VIIRS excluded because the other sensor had no detection nearby in that window).

- MODIS detections also seen by VIIRS: **32.7%**
- VIIRS detections also seen by MODIS: **13.1%**
- FRP of matched fires, VIIRS (summed over its pixels) / MODIS: median 0.61 (P10 0.18, P90 1.99, n=10,492)

by FRP (MW):

| frp_bin | n_modis | modis_corroborated | n_viirs | viirs_corroborated |
|---|---|---|---|---|
| <5 | 1,083 | 0.210 | 55,072 | 0.100 |
| 5-10 | 10,713 | 0.298 | 38,847 | 0.142 |
| 10-20 | 12,189 | 0.333 | 16,648 | 0.174 |
| 20-50 | 6,865 | 0.368 | 5,129 | 0.227 |
| >=50 | 1,073 | 0.414 | 365 | 0.301 |

by day/night:

| daynight | n_modis | modis_corroborated | n_viirs | viirs_corroborated |
|---|---|---|---|---|
| D | 31,813 | 0.325 | 115,285 | 0.130 |
| N | 110 | 0.845 | 776 | 0.298 |

by MODIS pixel size (km):

| scan_bin | n_modis | modis_corroborated |
|---|---|---|
| <1.5 | 25,029 | 0.340 |
| 1.5-2 | 4,086 | 0.263 |
| 2-3 | 2,229 | 0.323 |
| >=3 | 579 | 0.226 |

## 3. Normalisation (leave-one-year-out cross-validation)

160 overlapping weeks, years 2012-2015. Chosen model: **theilsen**. `raw` and `scale` are baselines, not candidates.

| model | r2_log | mae_log | mae_raw | bias_rel | spearman | coverage |
|---|---|---|---|---|---|---|
| huber | 0.824 | 0.649 | 2,907.169 | -0.038 | 0.935 | 0.912 |
| theilsen | 0.822 | 0.649 | 2,782.756 | -0.006 | 0.935 | 0.912 |
| quantile | 0.833 | 0.661 | 2,550.584 | 0.006 | 0.948 | 0.887 |
| isotonic | 0.825 | 0.708 | 3,167.095 | -0.009 | 0.924 | 0.912 |
| raw | 0.803 | 0.928 | 6,061.113 | -0.446 | 0.938 | 0.900 |
| scale | 0.830 | 0.645 | 3,003.591 | 0.122 | 0.938 | 0.906 |

Interval half-width in log1p units: 1.699 at 90% nominal coverage.

### Terra-only years (before 2002-07-04)

Only Terra reported, so a separate model is calibrated on Terra's overlap with VIIRS (160 weeks). Chosen: **quantile**.

| model | r2_log | mae_log | mae_raw | bias_rel | spearman | coverage |
|---|---|---|---|---|---|---|
| huber | 0.643 | 1.196 | 11,197.970 | -0.415 | 0.828 | 0.900 |
| theilsen | 0.644 | 1.194 | 10,753.679 | -0.462 | 0.824 | 0.906 |
| quantile | 0.830 | 0.762 | 5,251.299 | 0.037 | 0.917 | 0.894 |
| isotonic | 0.630 | 1.279 | 11,362.367 | -0.264 | 0.802 | 0.906 |
| raw | 0.152 | 2.052 | 11,853.895 | -0.892 | 0.828 | 0.912 |
| scale | 0.651 | 1.202 | 11,770.596 | -0.308 | 0.827 | 0.906 |

## 4. Harmonised record

5,355 days, of which 4,225 reconstructed from MODIS.

## 5. Seasonality

Fire season (10% / 50% / 90% of cumulative activity): day of year 288 / 306 / 131, about 209 days long.

This region burns in more than one season:

- day of year 286 / 300 / 310 (about 25 days, 71% of seasonal activity)
- day of year 120 / 128 / 137 (about 18 days, 29% of seasonal activity)

STL decomposition of 764 weekly totals (log1p scale): the seasonal component spans -6.06 to 5.30; the trend moves from 7.13 to 6.94.

## 6. Most unusual seasons

- 2003-04 was 1.4 robust standard deviations below the median of the other 12 fire years.
- 2004-05 was 1.3 robust standard deviations below the median of the other 12 fire years.
- 2011-12 was 1.3 robust standard deviations above the median of the other 12 fire years.
- 2006-07 was 1.1 robust standard deviations below the median of the other 12 fire years.
- 2007-08 was 1.1 robust standard deviations above the median of the other 12 fire years.

## 7. Sustained unusual periods

- 20 Jun 2009 to 30 Jun 2009 (11 days): activity ran 9.5 robust standard deviations above the typical level for those dates (peak 14.1). Baseline is built from the other years only.
- 29 Oct 2001 to 13 Nov 2001 (16 days): activity ran 4.6 robust standard deviations below the typical level for those dates (peak 12.6). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 22 Oct 2001 to 26 Oct 2001 (5 days): activity ran 7.9 robust standard deviations below the typical level for those dates (peak 13.4). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 12 Nov 2000 to 17 Nov 2000 (6 days): activity ran 2.5 robust standard deviations below the typical level for those dates (peak 3.8). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 06 Nov 2000 to 08 Nov 2000 (3 days): activity ran 3.8 robust standard deviations below the typical level for those dates (peak 5.9). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.
- 04 Nov 2002 to 06 Nov 2002 (3 days): activity ran 3.7 robust standard deviations below the typical level for those dates (peak 6.1). Baseline is built from the other years only.
- 03 May 2014 to 05 May 2014 (3 days): activity ran 2.3 robust standard deviations below the typical level for those dates (peak 3.2). Baseline is built from the other years only.
- 28 Sep 2001 to 30 Sep 2001 (3 days): activity ran 2.0 robust standard deviations above the typical level for those dates (peak 2.7). Baseline is built from the other years only. Less reliable: this falls in the Terra-only years, when a single morning overpass sampled each day.

## 8. Data-quality timeline

Platforms present in the loaded data:

| sensor | platform | first | last | detections |
|---|---|---|---|---|
| modis | Terra | 2000-11-01 | 2015-06-28 | 82,386 |
| modis | Aqua | 2002-07-13 | 2015-06-27 | 210,809 |
| viirs | SNPP | 2012-06-01 | 2015-06-30 | 356,903 |

Documented events (NASA sources; undated where the source gives no date):

- **2000-11** Terra active-fire record begins. NASA describes high quality active fire observations from Terra as available starting November 2000. Until Aqua, MODIS fire data come from one satellite, with fewer overpasses. [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2002-05-04** Aqua launched. Second MODIS on Aqua (13:30 local equator crossing). [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2002-07-04** Aqua active-fire record begins. High quality active fire observations from Aqua start on this date. From here MODIS samples the day twice at different local times (Terra morning, Aqua afternoon). [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5191)
- **2011-10-28** VIIRS launched on Suomi NPP. First VIIRS sensor, with 375 m I-band channels used for active fire detection. [source](https://forum.earthdata.nasa.gov/viewtopic.php?t=5189)
- **2012-01-20** Suomi NPP VIIRS fire record begins in FIRMS. FIRMS lists S-NPP VIIRS 375 m active fire temporal coverage as starting 20 January 2012. This is the start of the overlap with MODIS used to fit the normalisation. [source](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
- **2015** VIIRS 375 m fire radiative power uses 750 m data from 2015. FIRMS states that FRP retrievals combine 375 m and 750 m data and that starting in 2015 the algorithm incorporated the M13 channel. FRP may not be homogeneous across this change; the source gives the year only. [source](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
- **undated** MODIS Collection 6.1 processing. FIRMS near-real-time MODIS data use Collection 6.1. NASA says C6.1 contains no change to the science algorithm; changes improve the calibration of the Level 1B inputs. The source page gives no switch-over date, so none is placed on the timeline. [source](https://www.earthdata.nasa.gov/data/catalog/lancemodis-mcd14dl-6.1nrt)

## Notes

- 1 persistent heat-source cells (flares, industry, volcanoes) were removed.
- MODIS reports from Terra alone before 2002-07-18, with fewer overpasses; reconstructed values there are less certain.
- VIIRS is observed from 2012-06-01; 4230 days have no data.
- A single multiplicative factor (error 0.65) does about as well as theilsen (0.65) here, so the extra model complexity is not clearly justified for this region.
- Prediction intervals are about x5.5 wide on weekly totals at 90% nominal coverage: the sensors' weekly totals disagree by more than a constant factor.
- Before 2002-07-04 only Terra reports, with far fewer detections. Those weeks use a Terra-only model (quantile, cross-validated error 0.76 in log units, intervals about x6.4) so they are not mistaken for quiet years.
- 4225 of 5355 days are reconstructed from MODIS (VIIRS-equivalent, with prediction bands); the rest are observed by VIIRS.
