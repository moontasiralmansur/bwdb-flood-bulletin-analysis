# Dataset Specification

## Overview

**Original data source.** River situation bulletins published by the Flood Forecasting and Warning Center (FFWC) of the Bangladesh Water Development Board (BWDB), distributed as PDF files.

**Dataset purpose.** Provide structured, analysis-ready river-level data for this project's processing pipeline: sampling, empirical probability analysis, exploratory data analysis, and bulletin-to-bulletin comparison.

**Number of datasets.** Two bulletin datasets plus one descriptive PDF. The description file defines the column layout; it contains no tabular data and is not processed by the pipeline.

| Dataset | Source file | Observation time |
| --- | --- | --- |
| dataset1 | `dataset1.pdf` | 20-07-2026, 09:00 hours |
| dataset2 | `dataset2.pdf` | 20-07-2026, 15:00 hours |

**Monitoring stations.** Each bulletin reports on **127 monitoring stations** across four river basins: BRAHMAPUTRA, GANGES, MEGHNA, and SOUTH EASTERN HILL.

**Parsed records.** **128 records per bulletin.** The extra record is the `*CHANDPUR H.W.L.` continuation row, which carries data but no serial number and no distinct station identity (see Known Source Data Characteristics).

**Overall workflow from PDF to cleaned dataset.**

1. Raw text extraction — page-by-page, line-by-line (`extract_pdf.py`).
2. Station row identification — classification of station vs. metadata lines.
3. Record parsing — anchored regex per line, `-` mapped to missing (`parse_records.py`).
4. Validation — structural, numeric, and consistency checks (`validate.py`).
5. Cleaning — renaming, typing, and derived features (`clean.py`).
6. Basin enrichment — basin column recovered from PDF basin headings (`enrich.py`).
7. Excel export — `data/processed/<dataset>_clean.xlsx` (`export.py`).
8. Statistical analysis — sampling, probability, EDA, comparison, report (`sampling.py`, `probability.py`, `eda.py`, `comparison.py`, `report.py`).

---

## Source Files

| File | Description |
| --- | --- |
| `data/raw/data_description.pdf` | 1-page prose description of the river-level table columns (river name, station name, RHWL, danger level, previous/current day water levels, rise/fall in cm, difference from danger level). Used as reference only; not parsed by the pipeline. |
| `data/raw/dataset1.pdf` | 2-page river situation bulletin for 20-07-2026 at 09:00 hours. Columns: SL, RIVER, STATION NAME, RHWL (m MSL), D.L. (m MSL), WATER LEVEL for 19-07-2026 and 20-07-2026 (m MSL), Rise Above D.L. (cm), Fall / Below D.L. (cm). Produces `dataset1_clean.xlsx`. |
| `data/raw/dataset2.pdf` | 2-page bulletin for 20-07-2026 at 15:00 hours. Same layout as dataset1 with an additional AM/PM time column in the header. Produces `dataset2_clean.xlsx`. |

---

## Dataset Characteristics

**Plain-text BWDB bulletin format.** The bulletins are text-heavy documents: a title line, header rows with column names and units, dashed separator rules, basin headings, and station rows. Every station row is a single physical line of the form:

```
<serial> <RIVER> <STATION NAME> <RHWL> <D.L.> <WL_prev> <WL_curr> <rise cm> <fall cm>
```

**Two-page reports.** Both bulletins span exactly two pages. Each page repeats the column header and units rows; the table continues across the page break.

**Line-based extraction.** `page.extract_text()` splits each page into lines with 1-based page and line coordinates. No multi-line cell assembly is required.

**No machine-readable tables.** pdfplumber's `extract_tables()` detects zero tables on every page: the tables use character-spaced columns and dashed separators rather than drawn cell borders, which defeats the default table-detection heuristics.

**Basin headings.** Station groups are preceded by capitalized basin headings (e.g., `BRAHMAPUTRA BASIN`), matching `^[A-Z][A-Z .'()-]* BASIN$`. These headings are the only source of basin membership in the data and are recovered during enrichment.

**Continuation rows.** Some stations are split across two rows. The first row carries the serial number and river name (e.g., `109 MEGHNA *CHANDPUR L.W.L.`); the continuation row repeats only the station name with an asterisk prefix and no serial number (e.g., `*CHANDPUR H.W.L.`). Continuation rows are retained as separate records.

**Missing values.** Unavailable values are printed as `-` in the bulletin, and `- DATA NOT AVAILABLE` notes appear in the document. The parser maps `-` to missing (NaN); no imputation is performed.

**Numeric conventions.**

- Water levels (RHWL, D.L., previous, current) are printed to two decimals, e.g., `29.09`.
- Rise/fall values are signed integers that may carry a space after the sign (e.g., `+ 41`, `-51`); the parser normalizes this before conversion.
- Water levels may be negative (stations below the MSL datum).
- `fall_cm` is negative when below D.L.; `rise_cm` is negative for falling water.

**Water level units.** Water levels and reference levels are in **meters above MSL (m MSL)**; rise/fall and danger-level differences are in **centimeters**.

---

## Processing Pipeline

```
BWDB PDF
↓
Raw Text Extraction          (extract_pdf.py: extract_lines_with_pages)
↓
Station Row Identification   (extract_pdf.py: filter_station_rows)
↓
Record Parsing               (parse_records.py: parse_records → build_dataframe)
↓
Validation                   (validate.py: validate_dataframe)
↓
Cleaning                     (clean.py: clean_dataframe)
↓
Basin Enrichment             (enrich.py: enrich_with_basin — analysis time only)
↓
Excel Export                 (export.py: export_to_excel → data/processed)
↓
Statistical Analysis         (sampling / probability / eda / comparison / report)
```

Notes on the flow:

- Basin enrichment is not part of the exported Excel files; it is applied in memory at analysis time, so the pipeline produces **14-column** cleaned files and **15-column** analysis frames.
- Validation runs on the raw parsed frame, before cleaning, so anomalies reflect the source data rather than derived columns.
- `src/pipeline.py` (`process_dataset`) automates extraction through export for one PDF; `main.py` runs both PDFs plus cross-validation.

---

## Dataset Schema

The cleaned dataset (`data/processed/<dataset>_clean.xlsx`, 128 rows × 14 columns). The `basin` column (15th) exists only in analysis frames.

| Column | Data Type | Description | Source / Derived |
| --- | --- | --- | --- |
| `dataset` | string | Source PDF file name, e.g., `dataset1.pdf` | Derived (Phase 8) |
| `station_number` | Int64 (nullable) | Serial number printed in the bulletin; NaN for continuation rows | Source |
| `station_location` | string | Station name as printed, e.g., `DUDHKUMAR PATESWARI`; retains `*` markers | Source |
| `rhwl_m` | float64 | Recorded Highest Water Level, m MSL; NaN when printed as `-` | Source |
| `danger_level_m` | float64 | Danger Level, m MSL; NaN when printed as `-` | Source |
| `previous_water_level_m` | float64 | Water level for 19-07-2026, m MSL | Source |
| `current_water_level_m` | float64 | Water level for 20-07-2026, m MSL | Source |
| `rise_cm` | Int64 (nullable) | Rise above previous day's level, cm; negative = falling | Source |
| `fall_cm` | Int64 (nullable) | Fall below danger level, cm; negative = above danger | Source |
| `water_level_change_m` | float64 | Current minus previous water level, m | Derived |
| `water_level_change_cm` | float64 | `water_level_change_m` × 100, cm | Derived |
| `above_danger` | boolean | True where current water level exceeds danger level (both present) | Derived |
| `above_danger_distance` | float64 | Current minus danger level, m, for above-danger stations; NaN otherwise | Derived |
| `below_danger_distance` | float64 | Danger minus current level, m, for stations at or below danger; NaN otherwise | Derived |
| `basin` | string | Basin name from the PDF basin headings (analysis frames only) | Derived |

**Type note for Excel round-trips.** In memory, `station_number`, `rise_cm`, and `fall_cm` are nullable `Int64`. openpyxl does not preserve nullable integers: after export and re-read, columns containing missing values (`station_number`, `fall_cm`; also `rise_cm` in dataset2) are read back as `float64`. Consumers loading the Excel files should expect this.

---

## Derived Features

All derived features are computed in `src/clean.py` (`clean_dataframe`) unless noted.

- **`dataset`** — The source PDF file name (e.g., `dataset1.pdf`), inserted as the first column. Identifies which bulletin a row belongs to.
- **`water_level_change_m`** — `current_water_level_m − previous_water_level_m`.
- **`water_level_change_cm`** — `water_level_change_m × 100` (the same change expressed in centimeters).
- **`above_danger`** — Boolean mask where both `current_water_level_m` and `danger_level_m` are present and `current_water_level_m > danger_level_m`; otherwise False.
- **`above_danger_distance`** — `current_water_level_m − danger_level_m`, populated only where `above_danger` is True; NaN otherwise.
- **`below_danger_distance`** — `danger_level_m − current_water_level_m`, populated only where the station is at or below danger level; NaN otherwise. The two distance columns are mutually exclusive.
- **`basin`** — Not produced by cleaning. `enrich_with_basin()` (`src/enrich.py`) replays the source PDF, tracks the most recent basin heading per `(page, line)`, and assigns each station record the basin active at its line position. A row-count assertion between extracted records and the DataFrame guards against misalignment.

---

## Known Source Data Characteristics

This section separates what the **source bulletins** contain from how the **parser** behaves.

### Source-data characteristics

- **Duplicate serial number 49 (dataset2).** The 15:00 bulletin assigns serial 49 to two different stations. dataset1 has no duplicates.
- **CHANDPUR continuation row.** The bulletins print `109 MEGHNA *CHANDPUR L.W.L.` and, as a continuation without serial number, `*CHANDPUR H.W.L.`. The two bulletins spell the continuation differently: `*CHANDPUR H.W.L.` (dataset1) vs `* CHANDPUR H.W.L.` (dataset2, space after the asterisk); the L.W.L. rows differ the same way.
- **Missing RHWL values.** 19 stations per bulletin have no RHWL (printed `-`).
- **Missing danger levels.** 4 stations per bulletin have no danger level.
- **Missing water levels.** dataset2 additionally lacks 2 current water levels, 2 rise values, and 6 fall values. dataset1 has no missing values in these columns.
- **Negative water levels.** 3 stations report negative previous water levels (both bulletins); 3 report negative current water levels in dataset1 and 1 in dataset2 — stations below the MSL datum.
- **Lost underline formatting.** Page 2 of each bulletin draws red underline rules beneath four entire station rows (serials 80 SURMA SUNAMGANJ, 83 KUSHIYARA SHEOLA, 85 KUSHIYARA SHERPUR-SYLHET, 98 SOMESWARI DURGAPUR) and one short black rule between serials 81/82. Text extraction does not capture decorative rules, so the data carries no record of them; their intended meaning is not documented in the source materials.
- **Basin headings recovered during enrichment.** Basin membership is implicit in the document layout, not in the rows themselves; it is reconstructed from heading positions by `enrich_with_basin()`.
- **Monitoring stations vs parsed records.** The bulletins describe 127 stations, but each parses to 128 records: 127 serial-numbered station rows plus the CHANDPUR continuation row, which is not a distinct station.

### Parser behavior

- `-` tokens are converted to NaN in all numeric columns; missing values are preserved, never imputed or dropped.
- Continuation rows parse successfully with `station_number = NaN` and are flagged as parsing anomalies during validation (3 anomalies per bulletin: the `*` marker rows and the missing serial).
- The `*` markers are retained verbatim in `station_location` and flagged by validation.
- Signed rise/fall values are normalized (embedded spaces removed) before integer conversion.
- Duplicate serials and spelling variants are detected and reported, never silently corrected.
- The parser raises `ValueError` on any station row that fails the grammar; across both bulletins, zero rows failed, and zero extracted lines were left unclassified.

---

## Data Validation

Implemented in `src/validate.py`, `src/cross_validate.py`, and `src/enrich.py`.

- **Parser validation.** Structural audit of the raw parsed frame: row/column counts, missing serial numbers, duplicate serial numbers, `*` markers in locations, and a completeness audit of extracted lines (station / metadata / unclassified).
- **Numeric validation.** Negative water levels per column; invalid numeric values (infinities, non-numeric entries) per column.
- **Consistency checks.** Cross-field arithmetic within a tolerance of 3 cm: `fall_cm` vs `(current − danger) × 100`, and `rise_cm` vs `(current − previous) × 100`. The tolerance absorbs the bulletin's rounding; genuine inconsistencies would be flagged as anomalies.
- **Cross-dataset validation** (`cross_validate.py`). Compares both bulletins: row counts, matching/missing locations, duplicate locations and serials, location spelling differences (whitespace-normalized keys), column structure and dtypes, and per-station equality of `rhwl_m` and `danger_level_m` across bulletins. Findings are aggregated into a `potential_source_data_issues` list (duplicate serial 49; 2 CHANDPUR spelling differences).
- **Basin verification** (`enrich.py: verify_basins`). Asserts zero stations without a basin, rejects basin names outside the four known basins, and prints the distribution. A row-count assertion in `enrich_with_basin()` fails loudly on any mismatch between extracted records and DataFrame rows.

---

## Statistical Notes

Methodology only; numerical results are in `outputs/reports/analysis_summary.md`.

- **Sampling** (`sampling.py`). Three methods on the enriched dataset1, sample size 70: simple random sampling with a fixed seed; systematic sampling with interval N/n and a seeded random start; stratified sampling proportional to basin counts using the largest-remainder allocation, sampled within each basin with the same fixed seed.
- **Probability analysis** (`probability.py`). Empirical relative frequencies of above/below danger status and of rise/fall/no-change movement, overall and conditional on basin. Denominators exclude missing values and are reported explicitly; frequency tables retain an "unknown/missing" bucket.
- **Numerical EDA** (`eda.py`). Dataset overview (rows, columns, missing values), summary statistics (count, mean, median, std, min, Q1, Q3, max, IQR) per numeric column, and a correlation matrix of numeric columns.
- **Visual EDA** (`eda.py`). Six figure types per dataset rendered headlessly (Agg, PNG, 150 dpi): water-level histogram with KDE, boxplot by basin, rise/fall/no-change bar chart, above/below danger pie chart, correlation heatmap (derived/redundant columns excluded), and above-danger counts by basin.
- **Dataset comparison** (`comparison.py`). Side-by-side overviews, descriptive statistics, probability metrics, and per-basin aggregates of the two bulletins, plus a change summary: per-station water-level change between 09:00 and 15:00 matched on whitespace-normalized location keys, rise/fall counts, top-3 rises and falls, and stations newly above danger.

---

## Limitations

- **Dependence on BWDB bulletin layout.** The row grammar, header patterns, and basin-heading pattern encode the current FFWC layout. A layout change (new columns, multi-line rows, different separators) requires parser maintenance; there is no config-driven schema.
- **Assumption of one-line station records.** Every station row must be a single physical line. This holds for the current bulletins (verified: zero unclassified lines) but would silently break if rows wrapped across lines.
- **Systematic sampling (final-project fix).** The initial implementation used floor division (`N // n`) for the step, which degenerated to the first 70 rows for N=128, n=70. During final project preparation this was replaced with the standard algorithm: interval `k = N / n`, a reproducible random start `r ~ Uniform(0, k)` from a seeded RNG, and indices `floor(r + i*k)`. The sampler now returns exactly `n` rows spread across the full range; it is reproducible via the same fixed seed.
- **Missing values inherited from source.** RHWL (19), danger level (4), and dataset2-specific water-level/rise/fall gaps originate in the bulletin and propagate to all analyses; denominators that exclude them are documented but not imputed.
- **Dataset-specific formatting assumptions.** Character-spaced columns (no detectable tables), dashed separators, spaced signed integers (`+ 41`), the asterisk continuation convention, and dataset2's additional AM/PM header column are all assumed by the parser and classification rules.
- **Underline formatting not represented.** Red underline rules on page 2 of each bulletin are invisible to text extraction; the data cannot distinguish underlined from non-underlined rows, and the meaning of the underlines was never documented in the source materials.
- **Continuation row handling.** The CHANDPUR H.W.L. continuation is a record with `station_number = NaN` and a `*`-bearing location; consumers must account for it when counting stations or joining on serials.
- **Excel type lossiness.** Nullable `Int64` columns round-trip through openpyxl as `float64` when missing values are present.

---

## Reproducibility

- **Fixed random seed.** Simple random, systematic, and stratified sampling use seed 42; outputs are stable across runs.
- **Deterministic parsing workflow.** Extraction, classification, parsing, validation, cleaning, and enrichment are pure, deterministic functions — no randomness anywhere in the pipeline.
- **Pipeline execution.** `python main.py` runs extraction → validation → cleaning → export for both bulletins plus cross-validation. `python src/report.py` (or `python -m report` with `src` on the path) regenerates all analysis tables, samples, figures, and the Markdown report. Each phase module also runs standalone via its own `main()`.
- **Generated outputs.**

| Output | Source command |
| --- | --- |
| `data/processed/dataset1_clean.xlsx`, `dataset2_clean.xlsx` | `main.py` |
| `outputs/tables/descriptive_statistics.xlsx`, `probability_summary.xlsx`, `dataset_comparison.xlsx`, `basin_summary.xlsx` | `report.py` |
| `outputs/samples/simple_random_sample.xlsx`, `systematic_sample.xlsx`, `stratified_sample.xlsx` | `report.py` |
| `outputs/figures/*.png` (12 figures) | `eda.py` / `report.py` |
| `outputs/reports/analysis_summary.md` | `report.py` |

- **Required input files.** `data/raw/dataset1.pdf` and `data/raw/dataset2.pdf`. `data_description.pdf` is reference material only. The environment is the `.venv` virtual environment with the (unpinned) dependencies in `requirements.txt`.

---

## Summary

- **Sections created.** The full specification structure was created in `docs/dataset-specification.md`: Overview, Source Files, Dataset Characteristics, Processing Pipeline, Dataset Schema, Derived Features, Known Source Data Characteristics, Data Validation, Statistical Notes, Limitations, and Reproducibility — plus this summary. All facts were verified against the source code and data files (column counts, dtypes, missing-value counts, underline rules, sampling behavior).
- **Information that could not be verified.** The meaning of the red underline rules (and the short black rule) on page 2 of the bulletins — the source description document does not explain them, and the project never interprets them. The exact interpretation of the CHANDPUR continuation rows and the purpose of the `*` markers likewise come only from observation of the bulletin layout.
- **Source code:** no source code was modified.
- **Outputs:** no project outputs were modified.
- **Documentation only.** One new documentation file was created (`docs/dataset-specification.md`); three factual column-count statements in `docs/technical-log.md` were corrected (14-column cleaned schema; basin added at analysis time), also documentation-only.