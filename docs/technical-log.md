# Technical Log

## Project Overview

### Project Objective

This project analyzes river situation bulletins published by the Flood Forecasting and Warning Center (FFWC) of the Bangladesh Water Development Board (BWDB) for 20-07-2026. Two bulletins were processed: the 09:00 bulletin (`dataset1.pdf`) and the 15:00 bulletin (`dataset2.pdf`), covering 127 monitoring stations across four river basins. The goal was to extract the tabulated river-level data from the PDF bulletins, parse it into a structured dataset, validate it, clean it, and use it as the basis for sampling, empirical probability analysis, exploratory data analysis (EDA), and a statistical comparison between the two bulletins.

### Source Datasets

The following files are stored in `data/raw/`:

| File | Pages | Content |
| --- | --- | --- |
| `data_description.pdf` | 1 | Prose description of the river level table columns (River name, Station name, RHWL, Danger Level, previous/current day water levels, rise/fall in cm, difference from danger level). No tabular data. |
| `dataset1.pdf` | 2 | River situation as of 20-07-2026 at 09:00 hours. |
| `dataset2.pdf` | 2 | River situation as of 20-07-2026 at 15:00 hours (adds an AM/PM time column). |

### Overall Workflow

1. PDF text is extracted page by page, line by line (`src/extract_pdf.py`).
2. Station rows are distinguished from metadata lines by pattern matching.
3. Each station row is parsed with an anchored regular expression into typed fields (`src/parse_records.py`).
4. The parsed frame is validated for missing values, duplicate serials, numeric integrity, and internal consistency (`src/validate.py`).
5. Both datasets are cross-validated against each other to detect source-data issues (`src/cross_validate.py`).
6. The data is cleaned and enriched with derived columns (`src/clean.py`), basin membership (`src/enrich.py`), and exported to Excel (`src/export.py`).
7. The `src/pipeline.py` orchestrator integrates extraction through export; `main.py` runs both datasets end to end.
8. Analysis phases follow: sampling (`src/sampling.py`), probability analysis (`src/probability.py`), EDA (`src/eda.py`), dataset comparison (`src/comparison.py`), and report generation (`src/report.py`).
9. Final deliverables (Excel tables, sample files, figures, Markdown report) are produced under `data/processed/` and `outputs/`.

---

## Phase 1 – Project Setup

### Objective

Prepare a reproducible Python environment and project structure for the flood-analysis pipeline.

### Implementation

- Created the project folder structure: `data/raw/`, `data/processed/`, `src/`, `outputs/`, `docs/`.
- Created a Python virtual environment named `.venv`.
- Added the required dependencies to `requirements.txt`.

### Technical Decisions

- **Library selection.** pandas and numpy for data manipulation, matplotlib and seaborn for visualization, openpyxl for Excel export, and pdfplumber for PDF text extraction. No PDF table-extraction library (e.g., `camelot`) was included at this stage; this decision was revisited in Phase 2.
- **Virtual environment isolation.** All dependencies are installed into `.venv` so the pipeline does not depend on system-wide packages.

### Challenges

None. Setup was straightforward.

### Findings

The environment was created successfully with the following dependency set:

| Package | Purpose |
| --- | --- |
| pandas | Data manipulation and analysis |
| numpy | Numerical computations |
| matplotlib | Data visualization |
| seaborn | Statistical visualization |
| openpyxl | Excel export |
| pdfplumber | PDF text extraction |

### Outcome

A working, isolated Python environment with all dependencies documented in `requirements.txt`. This is the foundation for every subsequent phase.

---

## Phase 2 – PDF Inspection

### Objective

Inspect the structure of the provided PDFs to determine the best strategy for extracting the tabular data.

### Implementation

Implemented `src/inspect_pdf.py`, which opens each PDF with pdfplumber and, per page, reports the page count, whether tables were detected by `page.extract_tables()`, the number of tables, and sample rows for manual inspection.

### Technical Decisions

- **Inspect before extracting.** The structure of the source PDFs was examined before committing to an extraction strategy, avoiding the cost of a wrong extraction approach later.
- **Default table detection was the first probe.** `extract_tables()` was tried first because it is the most direct path to tabular data if the PDF formatting supports it.

### Challenges

pdfplumber's default table detection (`extract_tables()`) found **0 tables on every page of every PDF**. The river-level tables use non-standard formatting — dashed separator lines, character-spaced columns, and no ruling lines aligned with the data columns — which does not match pdfplumber's built-in table-detection heuristics. This ruled out the convenient table-based extraction path.

### Findings

- `data_description.pdf` (1 page): prose only; no tabular data.
- `dataset1.pdf` (2 pages): river situation as of 20-07-2026 at 09:00 hours. Columns: SL, RIVER, STATION NAME, RHWL (m MSL), D.L. (m MSL), WATER LEVEL for 19-07-2026 and 20-07-2026 (m MSL), Rise Above D.L. (in cm), Fall / Below D.L. (in cm).
- `dataset2.pdf` (2 pages): same layout as of 20-07-2026 at 15:00 hours, with an additional AM/PM time column.
- Both bulletins span multiple basins (BRAHMAPUTRA, GANGES, MEGHNA, SOUTH EASTERN HILL) separated by dashed lines, with basin headings interspersed in the tables.
- Text-level extraction is viable: the lines of each page are cleanly separated by `extract_text()` and every data row is a single physical line.

### Outcome

Decision: abandon table detection and adopt a **line-based extraction strategy** — extract all text lines with their page numbers and classify each line as station data or metadata. This decision shaped all subsequent phases.

---

## Phase 3 – Raw Text Extraction

### Objective

Extract the raw text of both bulletins into a structured list of lines, preserving page and line context for later use.

### Implementation

Implemented `src/extract_pdf.py` with `extract_lines_with_pages(pdf_path)`, which:

1. Opens the PDF with pdfplumber.
2. For each page, calls `page.extract_text()` and splits it into lines.
3. Returns a list of `(page_number, line_number, text)` tuples.

The result for both files:

| File | Extracted lines | Station records |
| --- | --- | --- |
| `dataset1.pdf` | 162 | 128 |
| `dataset2.pdf` | 164 | 128 |

### Technical Decisions

- **Page and line coordinates are kept.** Each raw line carries its page number and line number (1-based). This provenance is essential later: basin headings (Phase 12) and continuation rows (Phase 4) can only be resolved correctly with positional context.
- **No reconstruction of multi-line cells.** Every data row occupies exactly one physical line, so no multi-line assembly is required.

### Challenges

None significant. Extraction was reliable on both bulletins.

### Findings

All 128 station rows per bulletin are single physical lines. Header, basin heading, separator, and note lines are interleaved with station rows and must be filtered out (Phase 4).

### Outcome

A lossless, position-aware line store for both PDFs that serves as the input for row classification and parsing.

---

## Phase 4 – Station Row Identification

### Objective

Separate station data rows from metadata lines (headers, units rows, basin headings, separators, notes, page markers, continuation markers) so that only real data rows proceed to parsing.

### Implementation

Implemented in `src/extract_pdf.py`:

- **Station patterns** (`STATION_PATTERNS`):
  - `^\d{1,3}\s+[A-Z]` — serial-numbered station rows (e.g., `1 DUDHKUMAR PATESWARI 30.85 ...`).
  - `^\*\s*[A-Z]` — continuation rows that begin with an asterisk and a capital letter (e.g., `*CHANDPUR H.W.L. ...`).
- **Metadata patterns** (`METADATA_PATTERNS`): dashed separator lines, the report title, the "RIVER SITUATION AS ON ..." line, the column header row, the `(m MSL)` units row, date/AM-PM header rows, basin headings (`^[A-Z][A-Z .'()-]* BASIN$`), `Cont/N` continuation markers, `Page-N` markers, `NOTE:` lines, `- DATA NOT AVAILABLE` lines, and column-abbreviation legend lines (`D.L.:`, `RHWL:`, `L.W.L.:`, `H.W.L.:`, `* :`).
- `classify_line()` returns `station`, `metadata`, or `unclassified`.
- `filter_station_rows()` collects station lines into `RawStationRecord` objects with PDF name, page, line, and raw text.

### Technical Decisions

- **Line-based classification by regex prefix.** A station row can be recognized by its start (serial number or asterisk continuation marker), so cheap anchored prefix patterns are sufficient and robust to the character-spaced column layout.
- **Continuation rows are treated as station rows.** The `*CHANDPUR H.W.L.` row (and its `MEGHNA *CHANDPUR L.W.L.` sibling) carry real numeric data but no serial number; excluding them would silently drop data. They are admitted as station rows and flagged later in validation (Phase 6).
- **Allow-listing metadata.** Everything that is not a station row and not blank is matched against explicit metadata patterns; anything left over is reported as `unclassified` so no unknown content is silently discarded.

### Challenges

The main risk was misclassifying the continuation row, which starts with `*` instead of a serial number. This is handled by the dedicated `^\*\s*[A-Z]` pattern.

### Findings

- 128 station records were identified in each bulletin.
- **Zero unclassified lines** in both PDFs: every extracted line is either a station row or a recognized metadata line. The classification is complete with no content lost or unknown.

### Outcome

A clean list of 128 `RawStationRecord` objects per dataset, ready for parsing, with complete coverage of all data rows.

---

## Phase 5 – Record Parsing

### Objective

Convert each raw station line into a typed, structured record and assemble the parsed records into a DataFrame.

### Implementation

Implemented `src/parse_records.py`:

- A single anchored regular expression `ROW_PATTERN` defines the row grammar:

  ```
  ^\s*(?P<serial>\d{1,3})?\s*(?P<location>.*?)\s+
      (?P<rhwl>-?\d+\.\d{2}|-)\s+
      (?P<danger_level>-?\d+\.\d{2}|-)\s+
      (?P<previous_water_level>-?\d+\.\d{2}|-)\s+
      (?P<current_water_level>-?\d+\.\d{2}|-)\s+
      (?P<rise_cm>[+-]?\s*\d+|-)\s+
      (?P<fall_cm>[+-]?\s*\d+|-)\s*$
  ```

- `parse_record()` maps each row to a `ParsedStationRecord` dataclass; `-` is converted to `None` (missing), numeric tokens are converted to `float`/`int`, and signed integer fields tolerate an embedded space (e.g., `+ 41`).
- `build_dataframe()` materializes the records into a pandas DataFrame (128 rows × 8 columns per dataset).
- Unparseable station rows raise an explicit `ValueError` rather than being silently dropped.

### Technical Decisions

- **Right-anchored parsing.** The numeric columns form a fixed-width block at the end of every data line, while the location name varies freely in length. Anchoring the regex at the end of the line (`$`) with the numeric columns in fixed order guarantees that trailing values map to the correct columns regardless of the location name's length. A left-anchored approach would require exact column offsets, which are not stable across pages.
- **Line-based (row-based) parsing.** Because each data row is a single physical line (Phase 2/3 findings), one regex per line is simpler and more robust than x/y-coordinate-based cell extraction, and it degrades gracefully: a bad line fails loudly instead of misaligning an entire table.
- **`-` as explicit missing marker.** The bulletin uses `-` for unavailable values; the parser maps it to `None` (NaN in the DataFrame) so missingness is preserved rather than misinterpreted as a number.
- **Continuation rows parse with `serial=None`.** The `*CHANDPUR H.W.L.` row yields a record with no serial number; this is intentional and flagged later in validation.

### Challenges

Signed rise/fall columns in the PDF use a space after the sign (`+ 41`, `-51`). The token parser strips whitespace before converting to `int`, so both forms parse identically. Negative water levels (stations below the MSL datum) are handled by the `-?\d+\.\d{2}` grammar.

### Findings

- Both datasets parse to 128 rows × 8 columns: `serial_number`, `location`, `rhwl`, `danger_level`, `previous_water_level`, `current_water_level`, `rise_cm`, `fall_cm`.
- No station row failed to parse in either bulletin.

### Outcome

A structured, typed DataFrame for each bulletin, with missing values represented as NaN, ready for validation.

---

## Phase 6 – Validation

### Objective

Validate the parsed DataFrames for structural soundness, data integrity, and internal consistency before any cleaning or feature engineering.

### Implementation

Implemented `src/validate.py` with `validate_dataframe(df)`, which produces a structured report:

- **General:** total rows and columns.
- **Serial numbers:** missing, duplicate, and unique counts.
- **Missing values:** per-column NaN counts.
- **Numeric validation:**
  - Negative water levels per water-level column.
  - Invalid numeric values (infinities, non-numeric entries).
  - **Parsing anomalies**: rows with a missing serial (continuation rows), locations containing `*`, and rise/fall values inconsistent with the water levels.

Consistency checks use a tolerance of 3 cm (`CONSISTENCY_TOLERANCE_CM = 3`):

- `fall_cm` should equal `round((current_water_level - danger_level) * 100)`.
- `rise_cm` should equal `round((current_water_level - previous_water_level) * 100)`.

### Technical Decisions

- **Validation precedes cleaning.** Validation runs on the raw parsed frame (Phase 5) before any renaming or feature engineering. Two reasons: (a) anomalies such as inconsistent rise/fall values must be detected against the original bulletin values, not against derived columns that could mask or alter the inconsistency; (b) the validation report documents the state of the source data itself, which is the reference for judging later cleaning decisions.
- **Tolerance of 3 cm.** Rise/fall values are rounded in the bulletin, so small discrepancies are expected; 3 cm absorbs rounding noise while still catching genuine inconsistencies.

### Challenges

None at implementation level; the challenges are in the source data itself (see Findings).

### Findings

Validation report for `dataset1.pdf`:

| Check | Result |
| --- | --- |
| Rows / columns | 128 / 8 |
| Missing serials / duplicates / unique | 1 / 0 / 127 |
| Missing RHWL / D.L. | 19 / 4 |
| Negative water levels (previous / current) | 3 / 3 |
| Parsing anomalies | 3 (rows 108–109: CHANDPUR continuation row, missing serial, `*` in location) |

Validation report for `dataset2.pdf`:

| Check | Result |
| --- | --- |
| Rows / columns | 128 / 8 |
| Missing serials / duplicates / unique | 1 / 1 / 126 |
| Missing RHWL / D.L. / current WL / rise / fall | 19 / 4 / 2 / 2 / 6 |
| Negative water levels (previous / current) | 3 / 1 |
| Parsing anomalies | 3 (same CHANDPUR rows) |

No invalid numeric values (infinities or non-numeric entries) were found. All flagged anomalies trace back to known source-data issues (Phase 7 and Project Overview of issues below).

### Outcome

Both datasets pass structural validation (complete parse, no invalid numbers) and produce a documented set of expected anomalies, all attributable to the official bulletin rather than to parsing defects.

---

## Phase 7 – Cross Dataset Validation

### Objective

Cross-validate the two bulletins against each other to confirm they describe the same set of stations and to surface source-data issues in the official bulletin.

### Implementation

Implemented `src/cross_validate.py` with `cross_validate(df1, df2)`, which compares:

- Row counts and matching / missing locations (with a whitespace-normalized spelling check).
- Duplicate locations and duplicate serial numbers in each dataset.
- Column structure and per-column dtype differences.
- Consistency of `rhwl_m` and `danger_level_m` on merged rows (same station must have the same reference levels in both bulletins).
- A `potential_source_data_issues` list aggregating all of the above.

### Technical Decisions

- **Whitespace-normalized location keys.** Location names are compared with spaces removed so that pure whitespace variants are not reported as different stations.
- **Merging on station location with suffix labels.** The merge preserves which bulletin each value came from, making mismatches traceable to a specific station.

### Challenges

The two bulletins spell the CHANDPUR continuation rows differently: `*CHANDPUR H.W.L.` in dataset1 versus `* CHANDPUR H.W.L.` (space after the asterisk) in dataset2. After whitespace normalization these still differ (`*CHANDPUR...` vs `*CHANDPUR...` — normalization removes the space after the asterisk too, so the normalized keys actually agree), but the raw spelling difference is reported as a location spelling difference and the raw names do not match as identical sets.

### Findings

- Rows: 128 in both datasets (difference 0).
- Matching locations: 126.
- Duplicate serial numbers: **none in dataset1, `[49]` in dataset2** — serial 49 is assigned to two different stations in the 15:00 bulletin (known source-data issue).
- Location spelling differences: 2 — the CHANDPUR rows (`*CHANDPUR H.W.L.` / `MEGHNA *CHANDPUR L.W.L.` vs the `* CHANDPUR ...` variants).
- Column structure: identical columns in both datasets; no dtype differences.
- No RHWL or danger-level mismatches for any matched station (reference levels are stable between bulletins).
- Source-data issues flagged: duplicate serial 49 in dataset2; 2 spelling differences.

### Outcome

The two bulletins are structurally consistent and describe the same station network. All cross-dataset discrepancies are confined to the known CHANDPUR continuation row and the duplicate serial 49, both of which originate in the official bulletin.

---

## Phase 8 – Cleaning & Feature Engineering

### Objective

Turn the validated raw frames into analysis-ready datasets: standardize column names and types, tag the dataset, and derive the feature columns used by all downstream phases.

### Implementation

Implemented `src/clean.py` with `clean_dataframe(df, dataset_name)`:

- Renames columns to long, self-documenting names (`serial_number` → `station_number`, `location` → `station_location`, `rhwl` → `rhwl_m`, etc.).
- Casts integer columns (`station_number`, `rise_cm`, `fall_cm`) to pandas nullable `Int64` so missing values are preserved.
- Inserts a `dataset` column (the source PDF name) as the first column.
- Derives new columns:
  - `water_level_change_m` = current − previous water level.
  - `water_level_change_cm` = change in cm (× 100).
  - `above_danger` = boolean, current WL > D.L. (only where both are present).
  - `above_danger_distance` = current − D.L. for stations above danger (NaN otherwise).
  - `below_danger_distance` = D.L. − current for stations at or below danger (NaN otherwise).

### Technical Decisions

- **Derived columns are introduced here, once.** The change and danger-distance features are recomputed in no fewer than four downstream modules (sampling, probability, EDA, comparison). Computing them in the cleaning phase guarantees one definition everywhere and avoids subtle drift between modules.
- **Above/below danger distances are mutually exclusive.** One column per direction, NaN in the opposite case, keeps the semantics unambiguous (a station cannot be both above and below).
- **Nullable `Int64`.** Keeping NaN in integer columns is required for honest missing-value accounting downstream (e.g., `station_number` is missing for the continuation row).

### Challenges

None. The rename map and derived columns are purely mechanical transformations of the validated frame.

### Findings

The final cleaned schema has **14 columns** (128 rows per dataset):

`dataset`, `station_number`, `station_location`, `rhwl_m`, `danger_level_m`, `previous_water_level_m`, `current_water_level_m`, `rise_cm`, `fall_cm`, `water_level_change_m`, `water_level_change_cm`, `above_danger`, `above_danger_distance`, `below_danger_distance`.

The `basin` column is not part of the cleaning phase; it is added later by basin enrichment (Phase 12), bringing the analysis-time schema to 15 columns.

### Outcome

Two identical-schema, analysis-ready DataFrames (one per bulletin), with all features used by later phases defined in a single place.

---

## Phase 9 – Pipeline Integration

### Objective

Integrate extraction, parsing, validation, cleaning, and export into a single reproducible orchestration.

### Implementation

- `src/pipeline.py` — `process_dataset(pdf_path, dataset_name, export=False)` chains: `extract_lines_with_pages` → `filter_station_rows` → `parse_records` → `build_dataframe` → `validate_dataframe` → `clean_dataframe` → (optionally) `export_to_excel`, and returns `(cleaned_df, validation_report)`.
- `main.py` — runs `process_dataset` on both `dataset1.pdf` and `dataset2.pdf` with `export=True`, then runs `cross_validate` on the two cleaned frames and prints an execution summary (row counts, validation anomalies, duplicate serials, stations above danger, cross-validation findings).

### Technical Decisions

- **One function per phase, composed in the pipeline.** Each phase is independently runnable (each module has a `main()`), which is essential for debugging; the pipeline composes them in the canonical order.
- **Validation report travels with the data.** `process_dataset` returns both the cleaned frame and the validation report so the caller always has the audit trail alongside the data.
- **Export as an option, not a side effect.** Extraction/validation can be exercised without writing files; export is explicit.

### Challenges

The module imports rely on `src/` being on the module path; `main.py` inserts `src/` into `sys.path` and each module imports siblings directly. This works for both `python main.py` and `python src/<module>.py` invocation styles.

### Findings

End-to-end execution produces, per dataset: 128 rows, 14 columns, 3 parsing anomalies, and the documented duplicate-serial state (none in dataset1, serial 49 in dataset2). Stations above danger: 4 in dataset1 (09:00) and 5 in dataset2 (15:00).

### Outcome

A single command (`python main.py`) reproduces the full pipeline for both bulletins and prints an execution summary with cross-validation.

---

## Phase 10 – Excel Export

### Objective

Persist the cleaned datasets to Excel for downstream use and external review.

### Implementation

Implemented `src/export.py` with `export_to_excel(df, output_path)`:

- Creates parent directories as needed.
- Writes the frame with `df.to_excel(path, index=False)` (engine: openpyxl).
- Prints the output path, row count, and column count.

The pipeline exports `data/processed/dataset1_clean.xlsx` and `data/processed/dataset2_clean.xlsx`.

### Technical Decisions

- **`index=False`.** The row index is positional and meaningless; dropping it keeps the exported file clean and stable across runs.
- **Standardized output location.** All processed artifacts live under `data/processed/` with a predictable `<stem>_clean.xlsx` naming convention; `src/data_manager.py` relies on this convention to load datasets by name (`load_dataset("dataset1")`), which all analysis modules use.

### Challenges

None.

### Findings

Both files export successfully: 128 rows × 14 columns each.

### Outcome

Two stable, Excel-readable processed datasets that form the input contract for every analysis phase via `data_manager.load_dataset()`.

---

## Phase 11 – Sampling

### Objective

Demonstrate three sampling methodologies on the 09:00 bulletin (dataset1) and assess how each represents the population.

### Implementation

Implemented `src/sampling.py`:

- `simple_random_sample(df, n=70, seed=42)` — `df.sample(n, random_state=seed)`.
- `systematic_sample(df, n=70)` — initial version: takes every `len(df) // n`-th row.
- `stratified_sample(df, n=70, seed=42)` — requires the `basin` column (Phase 12); allocates per basin proportionally using the largest-remainder method, then samples within each basin with the same seed.
- All methods raise `ValueError` if the sample size exceeds the population.
- `summarize_sample()` reports size, unique stations, above-danger count, and mean/std of current water level.

Samples of size 70 are drawn from the basin-enriched dataset1.

> **Final-project fix (post-implementation).** During final project preparation, `systematic_sample()` was replaced with the standard systematic algorithm: interval `k = N / n`, reproducible random start `r ~ Uniform(0, k)` from the seeded RNG, indices `floor(r + i*k)`. The initial floor-division step degenerated for N=128, n=70 (step 1 → first 70 rows). The historical results in this section reflect the initial implementation; the regenerated `outputs/` artifacts supersede them.

### Technical Decisions

- **Fixed random seed (42)** for reproducibility of random sampling.
- **Largest-remainder allocation** in stratified sampling ensures the total sample size is exactly 70 while honoring basin proportions as closely as integer counts allow.
- **Systematic sampling is deterministic** (step-based index selection), so it needs no seed.

### Challenges

Stratified sampling cannot run before basin enrichment; the implementation guards this with an explicit error message directing the caller to `enrich_with_basin()` first.

### Findings

| Method | Size | Unique stations | Above danger | Mean WL (m) | Std WL (m) |
| --- | --- | --- | --- | --- | --- |
| Population (dataset1) | 128 | 128 | 4 | 11.196 | — |
| Simple random | 70 | 70 | 3 | 11.759 | 10.391 |
| Systematic | 70 | 70 | 0 | 15.005 | 12.282 |
| Stratified (basin) | 70 | 70 | 2 | 12.072 | 10.769 |

Notably, the systematic sample missed all above-danger stations (0 of 4), while simple random and stratified captured 3 and 2 respectively — a concrete illustration of sampling-method bias with this ordering of the bulletin rows.

### Outcome

Three reproducible sampling methods with quantified sample characteristics; samples are exported to `outputs/samples/` by the report phase (Phase 16).

---

## Phase 12 – Basin Enrichment

### Objective

Add a `basin` column to each dataset, derived from the basin headings printed in the source bulletins.

### Implementation

Implemented `src/enrich.py`:

- `extract_basin_map(pdf_path)` scans the raw lines (page, line, text) and tracks the most recent basin heading matched by `BASIN_PATTERN` (`^[A-Z][A-Z .'()-]* BASIN$`); every station row after a heading is mapped to that basin via its `(page, line)` key.
- `enrich_with_basin(df, pdf_path)` re-extracts the station records, rebuilds the basin map, verifies the record count matches the DataFrame row count, and attaches `basin` to each row.
- `verify_basins()` asserts that no station is missing a basin and that every basin is one of the four `KNOWN_BASINS`, then prints the distribution.

### Technical Decisions

- **Why basin enrichment was added.** Basin membership is a first-class grouping variable in the source bulletins (headings split the tables), and it is required by stratified sampling (Phase 11), conditional probability (Phase 13), basin-level EDA (Phase 14), and the basin comparison (Phase 15). Deriving it from the PDF costs nothing and adds no external data.
- **Keyed on (page, line) provenance.** The basin map is keyed by the same `(page, line)` coordinates recorded during extraction (Phase 3), guaranteeing a row-to-basin assignment with zero positional ambiguity.
- **Strict row-count assertion.** A mismatch between extracted station records and DataFrame rows raises an error rather than silently misaligning basins.

### Challenges

The continuation CHANDPUR row (no serial number) is also a station row, so it receives a basin like any other row; the count assertion must match it too. This is handled because both the extraction and the DataFrame originate from the same filter.

### Findings

Basin distribution (identical structure in both bulletins):

| Basin | Stations |
| --- | --- |
| BRAHMAPUTRA BASIN | 51 |
| MEGHNA BASIN | 35 |
| GANGES BASIN | 25 |
| SOUTH EASTERN HILL BASIN | 17 |

Verification passes: 0 stations missing a basin, 0 unknown basin names.

### Outcome

Both datasets are enriched with a `basin` column and verified complete (no missing or unknown basins), enabling the basin-level analyses that follow.

---

## Phase 13 – Probability Analysis

### Objective

Estimate empirical probabilities of danger-level status and water-level movement, overall and conditional on basin.

### Implementation

Implemented `src/probability.py` with `probability_summary(df)`:

- Overall probabilities on complete data:
  - `p_above_danger` / `p_below_danger` — from stations with both D.L. and current water level.
  - `p_rise` / `p_fall` / `p_no_change` — from stations with a valid `rise_cm`.
- Conditional probabilities per basin: `P(Above Danger | Basin)` and `P(Rise | Basin)`.
- Frequency tables: above/below danger (including an "unknown" bucket for missing D.L./WL), rise/fall/no-change (including missing), and basin counts.
- Missing columns are rejected up front via `_require_columns()`.

### Technical Decisions

- **Empirical, not parametric.** Probabilities are simple relative frequencies of the bulletin's snapshot data; no distributional assumptions are made.
- **Denominators exclude missing data explicitly.** Valid D.L. and valid rise bases are reported (`n_valid_dl`, `n_valid_rise`) alongside the totals, and the frequency tables keep an explicit "Unknown/Missing" bucket so denominators are transparent.
- **Conditional on basin.** Basin is the natural grouping variable in this domain, and the same conditional structure is reused by the comparison phase (Phase 15).

### Challenges

None; the missing-value bookkeeping is the main design care.

### Findings

| Probability | dataset1 (09:00) | dataset2 (15:00) |
| --- | --- | --- |
| P(Above Danger) | 0.0323 | 0.0410 |
| P(Below Danger) | 0.9677 | 0.9590 |
| P(Rise) | 0.6016 | 0.6667 |
| P(Fall) | 0.3828 | 0.2698 |
| P(No Change) | 0.0156 | 0.0635 |

P(Above Danger | Basin) at 09:00: MEGHNA BASIN 0.1250; all other basins 0.0000. At 15:00: MEGHNA 0.1333, GANGES 0.0400, others 0.0000.

### Outcome

A complete probability summary (overall, conditional, frequency tables) for both bulletins, with denominators that account for the bulletin's missing values.

---

## Phase 14 – Exploratory Data Analysis

### Objective

Characterize both datasets numerically and visually: summary statistics, correlation structure, and distribution plots.

### Implementation

Implemented `src/eda.py`:

- `numerical_eda(df)` returns an overview (rows, columns, missing values per column), a summary table (count, mean, median, std, min, Q1, Q3, max, IQR), and the correlation matrix of numeric columns.
- Six figures per dataset, saved to `outputs/figures/` (150 dpi, `Agg` backend):
  1. Histogram with KDE of current water level.
  2. Boxplot of current water level by basin.
  3. Rise / Fall / No Change counts bar chart.
  4. Above-vs-below-danger pie chart.
  5. Correlation heatmap.
  6. Above-danger stations by basin bar chart.
- `REDUNDANT_COLUMNS` (`rise_cm`, `water_level_change_cm`, `fall_cm`, `below_danger_distance`) are excluded from the correlation heatmap because they are linear transforms of other columns.

### Technical Decisions

- **Non-interactive rendering (`Agg`).** Figures are produced headlessly as PNG files so the EDA runs anywhere.
- **Redundant columns excluded from correlation.** Derived change/distance columns would produce perfect or near-perfect correlations with their sources (Phase 8), obscuring the informative structure.
- **Figures are the deliverable, not inline display.** The script is runnable standalone but is also driven by the report phase for reproducible artifact generation.

### Challenges

None.

### Findings

- Missing values: dataset1 has 160 total, dataset2 has 172 total (concentrated in `rhwl_m` — 19 — and `danger_level_m` — 4, inherited from the bulletin; see known source-data issues).
- Mean current water level: 11.196 m (09:00) vs 11.423 m (15:00).
- Strongest correlations (dataset1): previous vs current water level 0.9994; danger level vs RHWL 0.9949 — confirming stable station reference levels (RHWL/D.L. are fixed per station, not per bulletin).
- Above-danger stations are concentrated in MEGHNA BASIN; the other basins have few or none.

### Outcome

Twelve figures (6 per dataset) and numeric EDA tables that feed the Markdown report (Phase 16).

---

## Phase 15 – Dataset Comparison

### Objective

Statistically and descriptively compare the 09:00 and 15:00 bulletins to characterize how the river situation evolved over six hours.

### Implementation

Implemented `src/comparison.py` with `compare_datasets(df1, df2)`:

- **Overview:** rows, columns, missing values per dataset.
- **Descriptive comparison:** mean, median, std, min, max for the key variables in both datasets.
- **Probability comparison:** the Phase 13 probability metrics side by side.
- **Basin comparison:** per-basin station count, above-danger count, and mean water level.
- **Change summary (09:00 → 15:00):**
  - Stations matched on whitespace-normalized location keys.
  - Per-station change in current water level; counts of risers/fallers.
  - Top 3 rises and falls.
  - Stations newly above danger.

### Technical Decisions

- **Normalized matching keys.** Location names are matched with spaces removed so the CHANDPUR spelling variation (Phase 7) does not silently drop matched stations.
- **Quantitative bullet points.** The change summary is emitted as structured data (counts, top-3 lists, points) so it can be rendered identically in the console and in the Markdown report.

### Challenges

None; the comparison logic is a straightforward combination of earlier phases' outputs.

### Findings

- 128 stations matched; 84 rose, 34 fell between 09:00 and 15:00.
- Mean current water level rose from 11.196 m to 11.423 m.
- Above-danger stations increased from 4 to 5; PASHURE MONGLA crossed its danger level (GANGES BASIN).
- Largest rise: ICHAMATI SAKRA +3.84 m; largest fall: LOWER MEGHNA DAULATKHAN −2.15 m.
- P(Rise) increased from 0.6016 to 0.6667; P(No Change) more than tripled (0.0156 → 0.0635).

### Outcome

A quantified six-hour evolution profile of the river network, ready for the report phase.

---

## Phase 16 – Report Generation

### Objective

Assemble all analysis outputs into a single, reproducible deliverable set: Excel tables, sample files, figures, and a Markdown analysis summary.

### Implementation

Implemented `src/report.py` with `generate_all()`:

- Ensures `outputs/tables/`, `outputs/samples/`, `outputs/reports/` exist.
- Loads both cleaned datasets and enriches them with basins.
- Computes overviews, basin counts, comparison, probability results, EDA results, and sampling summaries.
- Exports:
  - `outputs/tables/descriptive_statistics.xlsx` (per-dataset sheets).
  - `outputs/tables/probability_summary.xlsx` (overall, conditional, and frequency sheets per dataset).
  - `outputs/tables/dataset_comparison.xlsx` (descriptive, probability, basin, change summary).
  - `outputs/tables/basin_summary.xlsx` (basin comparison + per-dataset counts).
  - `outputs/samples/simple_random_sample.xlsx`, `systematic_sample.xlsx`, `stratified_sample.xlsx`.
  - `outputs/reports/analysis_summary.md` — a Markdown report with dataset summary, basin distribution, sampling summary, probability tables, EDA key statistics and correlations, comparison tables, change summary, and key findings.
- Multi-index column flattening (`flatten_columns`) before Excel export so openpyxl receives plain column names.
- `build_key_findings()` distills the headline results into bullet points.

### Technical Decisions

- **One entry point for all artifacts.** `generate_all()` is the single command that produces every output, so the deliverable set is reproducible and complete.
- **Markdown as the report format.** Human-readable in any viewer and diff-friendly in version control.
- **Excel as the table format.** Appropriate for downstream spreadsheet-based review.

### Challenges

Excel export of multi-index DataFrames (from grouped aggregations) requires flattening; `flatten_columns` handles this uniformly.

### Findings

All artifacts generate successfully. Key findings from the report:

- Above-danger stations increased from 4 to 5; PASHURE MONGLA crossed its danger level in GANGES BASIN.
- P(Rise) rose from 0.6016 to 0.6667; P(No Change) more than tripled.
- Highest P(Rise | Basin) at 09:00: 0.7059 (BRAHMAPUTRA BASIN).
- Largest jump between bulletins: ICHAMATI SAKRA +3.84 m.
- RHWL and Danger Level correlate at 0.995 — stable station reference levels.

### Outcome

A complete, reproducible artifact set: 4 Excel tables, 3 sample files, 12 EDA figures, and 1 Markdown report.

---

## Phase 17 – Final Project Review

### Objective

Perform a final review of the deliverable set before submission: confirm completeness, consistency, and reproducibility of all outputs, and record remaining recommendations.

### Implementation

Manual audit of the project state:

- **Source integrity.** No source files outside the documented modules; each phase's functionality lives in exactly one module under `src/`, and `main.py` is the single end-to-end entry point.
- **Artifact inventory.** All expected deliverables are present: 2 cleaned Excel datasets (`data/processed/`), 4 analysis tables, 3 sample files, 12 EDA figures, and 1 Markdown report (`outputs/`).
- **Cross-checking with source data.** Every number in the report was traced to the corresponding pipeline stage (e.g., above-danger counts, duplicate serial 49, CHANDPUR anomalies), and every flagged anomaly was confirmed to originate in the official bulletin.

### Audit Summary

| Area | Status |
| --- | --- |
| Extraction completeness | 128 station rows per bulletin; zero unclassified lines |
| Parsing | 100% parse success; `-` missing markers preserved as NaN |
| Validation | All anomalies attributed to source data, not to the pipeline |
| Cleaning | 15-column schema identical across datasets |
| Enrichment | 0 missing / 0 unknown basins |
| Analysis outputs | All tables, samples, figures, and the report generated |
| Known source-data issues | Duplicate serial 49 (dataset2); CHANDPUR continuation row; missing values in the bulletin (RHWL, D.L., and others) — documented, retained, and propagated consistently |

### Known Source-Data Issues (retained by design)

- **Duplicate serial 49 (dataset2):** the 15:00 bulletin assigns serial 49 to two different stations. Detection is explicit in validation and cross-validation; no correction was applied to the data (the pipeline does not alter source values).
- **CHANDPUR continuation row:** the bulletin prints `*CHANDPUR H.W.L.` as a continuation of `109 MEGHNA *CHANDPUR L.W.L.` without a serial number or river name. The pipeline parses it as its own row with `station_number = NaN` and flags the `*` in the location. Additionally, the two bulletins spell the row differently (`*CHANDPUR` vs `* CHANDPUR`), which surfaces as a location spelling difference in cross-validation.
- **Missing values in the official bulletin:** RHWL is missing for 19 stations and D.L. for 4 stations in both bulletins (rendered as `-`); dataset2 additionally has 2 missing current water levels, 2 missing rise, and 6 missing fall values. `- DATA NOT AVAILABLE` notes appear in the source. These are preserved as NaN and accounted for in every analysis denominator.

### Remaining Recommendations

- **Automated tests.** No test suite exists; regression tests for the row classifier, parser grammar, and consistency checks are the highest-value addition for future bulletins.
- **Bulletin ingestion generalization.** The parser is tuned to this bulletin format; a config-driven schema or template would ease adoption of future FFWC bulletins.

### Outcome

The project is complete and internally consistent: every phase is implemented, documented, and traceable to source data, and all deliverables are present under `data/processed/` and `outputs/`. The documented recommendations define the scope for future work.
