import re
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd

from extract_pdf import RawStationRecord, extract_lines_with_pages, filter_station_rows

ROW_PATTERN = re.compile(
    r"^\s*"
    r"(?P<serial>\d{1,3})?\s*"
    r"(?P<location>.*?)"
    r"\s+"
    r"(?P<rhwl>-?\d+\.\d{2}|-)"
    r"\s+"
    r"(?P<danger_level>-?\d+\.\d{2}|-)"
    r"\s+"
    r"(?P<previous_water_level>-?\d+\.\d{2}|-)"
    r"\s+"
    r"(?P<current_water_level>-?\d+\.\d{2}|-)"
    r"\s+"
    r"(?P<rise_cm>[+-]?\s*\d+|-)"
    r"\s+"
    r"(?P<fall_cm>[+-]?\s*\d+|-)"
    r"\s*$"
)


@dataclass
class ParsedStationRecord:
    serial_number: int | None
    location: str
    rhwl: float | None
    danger_level: float | None
    previous_water_level: float | None
    current_water_level: float | None
    rise_cm: int | None
    fall_cm: int | None


def _parse_float(token: str) -> float | None:
    return None if token == "-" else float(token)


def _parse_signed_int(token: str) -> int | None:
    token = token.replace(" ", "")
    return None if token == "-" else int(token)


def parse_record(record: RawStationRecord) -> ParsedStationRecord:
    match = ROW_PATTERN.match(record.raw_text)
    if match is None:
        raise ValueError(f"Unparseable station row: {record.raw_text!r}")

    groups = match.groupdict()
    return ParsedStationRecord(
        serial_number=int(groups["serial"]) if groups["serial"] else None,
        location=groups["location"].strip(),
        rhwl=_parse_float(groups["rhwl"]),
        danger_level=_parse_float(groups["danger_level"]),
        previous_water_level=_parse_float(groups["previous_water_level"]),
        current_water_level=_parse_float(groups["current_water_level"]),
        rise_cm=_parse_signed_int(groups["rise_cm"]),
        fall_cm=_parse_signed_int(groups["fall_cm"]),
    )


def parse_records(records: list[RawStationRecord]) -> list[ParsedStationRecord]:
    return [parse_record(record) for record in records]


def build_dataframe(records: list[ParsedStationRecord]) -> pd.DataFrame:
    return pd.DataFrame([asdict(record) for record in records])


def main() -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 60)

    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    for pdf_file in pdf_files:
        pdf_path = str(data_dir / pdf_file)
        station_records = filter_station_rows(extract_lines_with_pages(pdf_path), pdf_file)
        parsed = parse_records(station_records)
        df = build_dataframe(parsed)

        print("\n" + "=" * 70)
        print(f"File name: {pdf_file}")
        print(f"DataFrame shape: {df.shape}")
        print(f"Data types:\n{df.dtypes}")
        print("\nFirst 10 rows:")
        print(df.head(10).to_string())
        print("\nLast 10 rows:")
        print(df.tail(10).to_string())
        print("=" * 70)


if __name__ == "__main__":
    main()