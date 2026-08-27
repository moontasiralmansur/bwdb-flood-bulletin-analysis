from pathlib import Path

import pandas as pd

from clean import clean_dataframe
from extract_pdf import extract_lines_with_pages, filter_station_rows
from parse_records import build_dataframe, parse_records


def _duplicates(series: pd.Series) -> list:
    counts = series.dropna().value_counts()
    return sorted(counts[counts > 1].index.tolist())


def _normalize_location(location: str) -> str:
    return "".join(location.split())


def cross_validate(df1: pd.DataFrame, df2: pd.DataFrame) -> dict:
    loc1 = set(df1["station_location"])
    loc2 = set(df2["station_location"])

    matching = loc1 & loc2
    missing_in_1 = sorted(loc2 - loc1)
    missing_in_2 = sorted(loc1 - loc2)

    dup_locations_1 = _duplicates(df1["station_location"])
    dup_locations_2 = _duplicates(df2["station_location"])

    dup_serials_1 = _duplicates(df1["station_number"])
    dup_serials_2 = _duplicates(df2["station_number"])

    norm1 = {_normalize_location(loc): loc for loc in loc1}
    norm2 = {_normalize_location(loc): loc for loc in loc2}
    spelling_differences = sorted(
        (norm1[n], norm2[n]) for n in norm1.keys() & norm2.keys() if norm1[n] != norm2[n]
    )

    column_structure = {
        "columns_match": list(df1.columns) == list(df2.columns),
        "dataset1_columns": list(df1.columns),
        "dataset2_columns": list(df2.columns),
    }
    dtype_differences = {
        col: (str(df1[col].dtype), str(df2[col].dtype))
        for col in df1.columns
        if col in df2.columns and str(df1[col].dtype) != str(df2[col].dtype)
    }
    column_structure["dtype_differences"] = dtype_differences

    issues: list[str] = []
    if dup_serials_1:
        issues.append(f"duplicate serial numbers in dataset1: {dup_serials_1}")
    if dup_serials_2:
        issues.append(f"duplicate serial numbers in dataset2: {dup_serials_2}")
    if spelling_differences:
        issues.append(
            f"location spelling differs between datasets: {len(spelling_differences)} location(s)"
        )

    merged = df1.merge(df2, on="station_location", suffixes=("_1", "_2"))
    for col in ("rhwl_m", "danger_level_m"):
        col1, col2 = f"{col}_1", f"{col}_2"
        mismatches = merged[
            merged[col1].notna() & merged[col2].notna() & (merged[col1] != merged[col2])
        ]
        for _, row in mismatches.iterrows():
            issues.append(
                f"{col} differs for {row['station_location']}: "
                f"dataset1={row[col1]}, dataset2={row[col2]}"
            )

    return {
        "rows": {"dataset1": len(df1), "dataset2": len(df2), "difference": abs(len(df1) - len(df2))},
        "matching_locations": len(matching),
        "missing_locations": {
            "in_dataset1_not_dataset2": missing_in_2,
            "in_dataset2_not_dataset1": missing_in_1,
        },
        "duplicate_locations": {"dataset1": dup_locations_1, "dataset2": dup_locations_2},
        "duplicate_serials": {"dataset1": dup_serials_1, "dataset2": dup_serials_2},
        "location_spelling_differences": spelling_differences,
        "column_structure": column_structure,
        "potential_source_data_issues": issues,
    }


def print_report(report: dict) -> None:
    print("\n" + "=" * 60)
    print("Dataset Comparison")
    print("=" * 60)

    rows = report["rows"]
    print("\nRows")
    print(f"  dataset1: {rows['dataset1']}")
    print(f"  dataset2: {rows['dataset2']}")
    print(f"  difference: {rows['difference']}")

    print(f"\nMatching locations: {report['matching_locations']}")

    missing = report["missing_locations"]
    print("\nMissing locations")
    print(f"  in dataset1, not dataset2: {missing['in_dataset1_not_dataset2'] or 'none'}")
    print(f"  in dataset2, not dataset1: {missing['in_dataset2_not_dataset1'] or 'none'}")

    dup_locations = report["duplicate_locations"]
    print("\nDuplicate locations")
    print(f"  dataset1: {dup_locations['dataset1'] or 'none'}")
    print(f"  dataset2: {dup_locations['dataset2'] or 'none'}")

    dup_serials = report["duplicate_serials"]
    print("\nDuplicate serials")
    print(f"  dataset1: {dup_serials['dataset1'] or 'none'}")
    print(f"  dataset2: {dup_serials['dataset2'] or 'none'}")

    spelling = report["location_spelling_differences"]
    print("\nLocation spelling differences")
    if spelling:
        for loc1, loc2 in spelling:
            print(f"  dataset1: {loc1!r}")
            print(f"  dataset2: {loc2!r}")
    else:
        print("  none")

    structure = report["column_structure"]
    print("\nColumn structure")
    print(f"  columns match: {structure['columns_match']}")
    if structure["dtype_differences"]:
        print("  dtype differences:")
        for col, (dtype1, dtype2) in structure["dtype_differences"].items():
            print(f"    {col}: dataset1={dtype1}, dataset2={dtype2}")

    issues = report["potential_source_data_issues"]
    print("\nPotential source-data issues")
    if issues:
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("  none")


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    dfs = {}
    for pdf_file in pdf_files:
        pdf_path = str(data_dir / pdf_file)
        station_records = filter_station_rows(extract_lines_with_pages(pdf_path), pdf_file)
        df = build_dataframe(parse_records(station_records))
        dfs[pdf_file] = clean_dataframe(df, pdf_file)

    report = cross_validate(dfs["dataset1.pdf"], dfs["dataset2.pdf"])
    print_report(report)


if __name__ == "__main__":
    main()