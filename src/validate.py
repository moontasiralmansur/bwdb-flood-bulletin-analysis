from pathlib import Path

import numpy as np
import pandas as pd

from extract_pdf import extract_lines_with_pages, filter_station_rows
from parse_records import build_dataframe, parse_records

WATER_LEVEL_COLUMNS = [
    "rhwl",
    "danger_level",
    "previous_water_level",
    "current_water_level",
]

CONSISTENCY_TOLERANCE_CM = 3


def _count_missing(df: pd.DataFrame) -> dict[str, int]:
    return {col: int(df[col].isna().sum()) for col in df.columns}


def _serial_stats(df: pd.DataFrame) -> dict[str, int]:
    present = df["serial_number"].dropna()
    duplicated_occurrences = present[present.duplicated(keep=False)]
    return {
        "missing": int(df["serial_number"].isna().sum()),
        "duplicates": int(duplicated_occurrences.duplicated().sum()),
        "unique": int(df["serial_number"].nunique()),
    }


def _negative_water_levels(df: pd.DataFrame) -> dict[str, int]:
    result: dict[str, int] = {}
    for col in WATER_LEVEL_COLUMNS:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            result[col] = int((df[col] < 0).sum())
    return result


def _invalid_numeric_values(df: pd.DataFrame) -> dict[str, int]:
    result: dict[str, int] = {}
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            result[col] = int(np.isinf(df[col].to_numpy(dtype=float)).sum())
        else:
            coerced = pd.to_numeric(df[col].dropna(), errors="coerce")
            result[col] = int(coerced.isna().sum())
    return result


def _parsing_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies: list[dict] = []

    if "serial_number" in df.columns:
        for idx in df.index[df["serial_number"].isna()]:
            anomalies.append(
                {"index": int(idx), "reason": "missing serial number (continuation row)"}
            )

    if "location" in df.columns:
        for idx in df.index[df["location"].astype(str).str.contains(r"\*", regex=True)]:
            anomalies.append({"index": int(idx), "reason": "location contains '*' marker"})

    required_fall = {"danger_level", "current_water_level", "fall_cm"}
    if required_fall.issubset(df.columns):
        for idx, row in df.iterrows():
            if row[["danger_level", "current_water_level", "fall_cm"]].isna().any():
                continue
            expected = round((row["current_water_level"] - row["danger_level"]) * 100)
            if abs(expected - row["fall_cm"]) > CONSISTENCY_TOLERANCE_CM:
                anomalies.append(
                    {
                        "index": int(idx),
                        "reason": (
                            f"fall_cm {row['fall_cm']} inconsistent with "
                            f"(WL - D.L.) * 100 = {expected}"
                        ),
                    }
                )

    required_rise = {"previous_water_level", "current_water_level", "rise_cm"}
    if required_rise.issubset(df.columns):
        for idx, row in df.iterrows():
            if row[["previous_water_level", "current_water_level", "rise_cm"]].isna().any():
                continue
            expected = round((row["current_water_level"] - row["previous_water_level"]) * 100)
            if abs(expected - row["rise_cm"]) > CONSISTENCY_TOLERANCE_CM:
                anomalies.append(
                    {
                        "index": int(idx),
                        "reason": (
                            f"rise_cm {row['rise_cm']} inconsistent with "
                            f"(WL_curr - WL_prev) * 100 = {expected}"
                        ),
                    }
                )

    return anomalies


def validate_dataframe(df: pd.DataFrame) -> dict:
    report = {
        "general": {"total_rows": len(df), "total_columns": len(df.columns)},
        "serial_number": _serial_stats(df),
        "missing_values": _count_missing(df),
        "numeric_validation": {
            "negative_water_levels": _negative_water_levels(df),
            "invalid_numeric_values": _invalid_numeric_values(df),
            "parsing_anomalies": _parsing_anomalies(df),
        },
    }
    return report


def print_report(title: str, report: dict) -> None:
    print("\n" + "=" * 60)
    print(f"Validation Report: {title}")
    print("=" * 60)

    print("\nGeneral")
    print(f"  Total rows: {report['general']['total_rows']}")
    print(f"  Total columns: {report['general']['total_columns']}")

    print("\nSerial Number")
    serial = report["serial_number"]
    print(f"  Missing serial numbers: {serial['missing']}")
    print(f"  Duplicate serial numbers: {serial['duplicates']}")
    print(f"  Unique serial numbers: {serial['unique']}")

    print("\nMissing Values")
    for col, count in report["missing_values"].items():
        print(f"  {col}: {count}")

    print("\nNumeric Validation")
    print("  Negative water levels:")
    for col, count in report["numeric_validation"]["negative_water_levels"].items():
        print(f"    {col}: {count}")
    print("  Invalid numeric values:")
    for col, count in report["numeric_validation"]["invalid_numeric_values"].items():
        print(f"    {col}: {count}")

    anomalies = report["numeric_validation"]["parsing_anomalies"]
    print(f"  Parsing anomalies: {len(anomalies)}")
    for anomaly in anomalies:
        print(f"    row {anomaly['index']}: {anomaly['reason']}")


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    for pdf_file in pdf_files:
        pdf_path = str(data_dir / pdf_file)
        station_records = filter_station_rows(extract_lines_with_pages(pdf_path), pdf_file)
        df = build_dataframe(parse_records(station_records))

        report = validate_dataframe(df)
        print_report(pdf_file, report)


if __name__ == "__main__":
    main()