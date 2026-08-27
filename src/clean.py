from pathlib import Path

import pandas as pd

from extract_pdf import extract_lines_with_pages, filter_station_rows
from parse_records import build_dataframe, parse_records

COLUMN_RENAMES = {
    "serial_number": "station_number",
    "location": "station_location",
    "rhwl": "rhwl_m",
    "danger_level": "danger_level_m",
    "previous_water_level": "previous_water_level_m",
    "current_water_level": "current_water_level_m",
}

INT_COLUMNS = ["station_number", "rise_cm", "fall_cm"]


def clean_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned.rename(columns=COLUMN_RENAMES)

    for col in INT_COLUMNS:
        cleaned[col] = cleaned[col].astype("Int64")

    cleaned.insert(0, "dataset", dataset_name)

    cleaned["water_level_change_m"] = (
        cleaned["current_water_level_m"] - cleaned["previous_water_level_m"]
    )
    cleaned["water_level_change_cm"] = cleaned["water_level_change_m"] * 100

    valid = cleaned[["current_water_level_m", "danger_level_m"]].notna().all(axis=1)
    mask_above = valid & (cleaned["current_water_level_m"] > cleaned["danger_level_m"])
    mask_below = valid & (cleaned["current_water_level_m"] <= cleaned["danger_level_m"])

    cleaned["above_danger"] = mask_above
    cleaned["above_danger_distance"] = (
        cleaned["current_water_level_m"] - cleaned["danger_level_m"]
    ).where(mask_above)
    cleaned["below_danger_distance"] = (
        cleaned["danger_level_m"] - cleaned["current_water_level_m"]
    ).where(mask_below)

    return cleaned


def main() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 180)
    pd.set_option("display.max_colwidth", 60)

    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    for pdf_file in pdf_files:
        pdf_path = str(data_dir / pdf_file)
        station_records = filter_station_rows(extract_lines_with_pages(pdf_path), pdf_file)
        df = build_dataframe(parse_records(station_records))

        cleaned = clean_dataframe(df, pdf_file)

        print("\n" + "=" * 70)
        print(f"Cleaned DataFrame: {pdf_file}")
        print("=" * 70)
        print("\nDataFrame info:")
        cleaned.info()
        print("\nColumn names:")
        print(list(cleaned.columns))
        print("\nData types:")
        print(cleaned.dtypes.to_string())
        print("\nFirst 10 rows:")
        print(cleaned.head(10).to_string())


if __name__ == "__main__":
    main()