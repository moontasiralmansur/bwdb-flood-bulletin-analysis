import re
from pathlib import Path

import pandas as pd

from data_manager import load_dataset
from extract_pdf import extract_lines_with_pages, filter_station_rows, is_station_row

BASIN_PATTERN = re.compile(r"^[A-Z][A-Z .'()-]* BASIN$")

KNOWN_BASINS = {
    "BRAHMAPUTRA BASIN",
    "GANGES BASIN",
    "MEGHNA BASIN",
    "SOUTH EASTERN HILL BASIN",
}


def extract_basin_map(pdf_path: str) -> dict[tuple[int, int], str]:
    basin_map: dict[tuple[int, int], str] = {}
    active_basin: str | None = None

    for page_number, line_number, text in extract_lines_with_pages(pdf_path):
        stripped = text.strip()
        if BASIN_PATTERN.match(stripped):
            active_basin = stripped
        elif is_station_row(text):
            basin_map[(page_number, line_number)] = active_basin

    return basin_map


def enrich_with_basin(df: pd.DataFrame, pdf_path: str) -> pd.DataFrame:
    pdf_name = Path(pdf_path).name
    records = filter_station_rows(extract_lines_with_pages(pdf_path), pdf_name)
    basin_map = extract_basin_map(pdf_path)

    if len(records) != len(df):
        raise ValueError(
            f"Row mismatch: {len(records)} station records vs {len(df)} dataframe rows"
        )

    basins = [basin_map[(r.page_number, r.line_number)] for r in records]

    enriched = df.copy()
    enriched["basin"] = basins
    return enriched


def verify_basins(df: pd.DataFrame) -> None:
    total = len(df)
    missing = int(df["basin"].isna().sum())
    unknown = sorted(set(df["basin"].dropna().unique()) - KNOWN_BASINS)

    print(f"Verification: {total} stations, {total - missing} with a basin, {missing} missing")
    if missing:
        raise ValueError(f"{missing} stations have no basin")
    if unknown:
        raise ValueError(f"Unknown basins: {unknown}")

    print("\nBasin distribution:")
    print(df["basin"].value_counts().to_string())


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    for name in ("dataset1", "dataset2"):
        df = load_dataset(name)
        enriched = enrich_with_basin(df, str(data_dir / f"{name}.pdf"))

        print(f"\n{'=' * 60}")
        print(f"Enriched dataset: {name}")
        print("=" * 60)
        print(f"Rows: {len(enriched)}, Columns: {len(enriched.columns)}")
        verify_basins(enriched)


if __name__ == "__main__":
    main()