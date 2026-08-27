# Project Overview

This project analyses flood bulletins published by the Bangladesh Water Development Board (BWDB) for 20-07-2026. Two bulletins (09:00 and 15:00) covering 127 monitoring stations across 4 river basins were extracted from PDF, parsed line-by-line, validated, cleaned and enriched with basin information. The analysis covers sampling, empirical probability analysis, exploratory data analysis (EDA) and a statistical comparison of the two bulletins.

## Dataset Summary

| Dataset | Rows | Columns | Missing values |
| --- | --- | --- | --- |
| dataset1 | 128 | 15 | 160 |
| dataset2 | 128 | 15 | 172 |

### Basin distribution (dataset1)

| Basin | Stations |
| --- | --- |
| BRAHMAPUTRA BASIN | 51 |
| MEGHNA BASIN | 35 |
| GANGES BASIN | 25 |
| SOUTH EASTERN HILL BASIN | 17 |

## Sampling Summary

Samples of size 70 were drawn from dataset1 (09:00 bulletin) with a fixed random seed (42).

| Method | Size | Unique stations | Above danger | Mean WL (m) | Std WL (m) |
| --- | --- | --- | --- | --- | --- |
| simple random | 70 | 70 | 3 | 11.7593 | 10.3912 |
| systematic | 70 | 70 | 4 | 10.528 | 9.2333 |
| stratified | 70 | 70 | 2 | 12.0724 | 10.7691 |

## Probability Analysis

### Overall probabilities

| Probability | dataset1 (09:00) | dataset2 (15:00) |
| --- | --- | --- |
| p_above_danger | 0.0323 | 0.041 |
| p_below_danger | 0.9677 | 0.959 |
| p_rise | 0.6016 | 0.6667 |
| p_fall | 0.3828 | 0.2698 |
| p_no_change | 0.0156 | 0.0635 |

### P(Above Danger | Basin)

| Basin | dataset1 (09:00) | dataset2 (15:00) |
| --- | --- | --- |
| BRAHMAPUTRA BASIN | 0.0 | 0.0 |
| MEGHNA BASIN | 0.125 | 0.1333 |
| GANGES BASIN | 0.0 | 0.04 |
| SOUTH EASTERN HILL BASIN | 0.0 | 0.0 |

## Exploratory Data Analysis

### Key statistics

| Variable | Mean d1 | Median d1 | Mean d2 | Median d2 |
| --- | --- | --- | --- | --- |
| rhwl_m | 14.9167 | 12.4900 | 14.9167 | 12.4900 |
| danger_level_m | 13.2287 | 10.8750 | 13.2287 | 10.8750 |
| current_water_level_m | 11.1964 | 8.1000 | 11.4234 | 8.2650 |
| rise_cm | 8.9453 | 3.0000 | 9.0397 | 3.0000 |
| fall_cm | -209.8871 | -165.5000 | -202.8770 | -150.5000 |

### Strongest correlations (dataset1)

| Variable 1 | Variable 2 | Correlation |
| --- | --- | --- |
| previous_water_level_m | current_water_level_m | 0.9994 |
| current_water_level_m | previous_water_level_m | 0.9994 |
| danger_level_m | rhwl_m | 0.9949 |

## Dataset Comparison

### Probability comparison

| Probability | dataset1 (09:00) | dataset2 (15:00) |
| --- | --- | --- |
| p_above_danger | 0.0323 | 0.041 |
| p_below_danger | 0.9677 | 0.959 |
| p_rise | 0.6016 | 0.6667 |
| p_fall | 0.3828 | 0.2698 |
| p_no_change | 0.0156 | 0.0635 |

### Change summary (09:00 to 15:00)

- Mean current water level rose from 11.196 m to 11.423 m between 09:00 and 15:00
- Above-danger stations increased from 4 to 5
- 128 stations matched; 84 rose, 34 fell between bulletins
- Largest rise #1: ICHAMATI SAKRA +3.84 m
- Largest rise #2: LITTLE FENI COMPANYGANJ +3.54 m
- Largest rise #3: PASHURE MONGLA +2.03 m
- Largest fall #1: LOWER MEGHNA DAULATKHAN -2.15 m
- Largest fall #2: KIRTONKHOLA BARISAL -0.72 m
- Largest fall #3: FENI SONAPUR -0.60 m


## Key Findings

- Above-danger stations increased from 4 to 5 between 09:00 and 15:00; PASHURE MONGLA crossed its danger level in the GANGES BASIN.
- P(Rise) increased from 0.6016 to 0.6667 between the bulletins, while P(No Change) increased from 0.0156 to 0.0635 (+307.1%).
- The highest P(Rise | Basin) at 09:00 was 0.7059 (BRAHMAPUTRA BASIN).
- Largest water-level jump between bulletins: ICHAMATI SAKRA +3.84 m.
- RHWL and Danger Level correlate at 0.995, confirming stable station reference levels.

