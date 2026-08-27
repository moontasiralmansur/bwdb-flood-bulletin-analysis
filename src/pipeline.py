from pathlib import Path

import pandas as pd

from clean import clean_dataframe
from export import export_to_excel
from extract_pdf import extract_lines_with_pages, filter_station_rows
from parse_records import build_dataframe, parse_records
from validate import validate_dataframe


def process_dataset(
    pdf_path: str, dataset_name: str, export: bool = False
) -> tuple[pd.DataFrame, dict]:
    station_records = filter_station_rows(extract_lines_with_pages(pdf_path), dataset_name)

    df = build_dataframe(parse_records(station_records))
    validation_report = validate_dataframe(df)

    cleaned = clean_dataframe(df, dataset_name)

    if export:
        processed_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
        output_path = processed_dir / f"{Path(dataset_name).stem}_clean.xlsx"
        export_to_excel(cleaned, str(output_path))

    return cleaned, validation_report