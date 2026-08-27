import re
from dataclasses import dataclass
import pdfplumber
from pathlib import Path

STATION_PATTERNS = [
    re.compile(r"^\d{1,3}\s+[A-Z]"),  # serial-numbered station rows
    re.compile(r"^\*\s*[A-Z]"),  # continuation rows (e.g., "*CHANDPUR H.W.L.")
]

METADATA_PATTERNS = [
    re.compile(r"^[-]{5,}.*$"),  # dashed separator / header rules
    re.compile(r"^FLOOD FORECASTING AND WARNING CENTER, BWDB$"),  # report title
    re.compile(r"^RIVER SITUATION AS ON \d{2}-\d{2}-\d{4} AT \d{2}:\d{2} HOURS$"),
    re.compile(r"^SL\s+RIVER\s+STATION NAME"),  # column header
    re.compile(r"^\(m MSL\)"),  # units row
    re.compile(r"^\d{2}-\d{2}-\d{4}\s+\d{2}-\d{2}-\d{4}\s+in cm in cm$"),
    re.compile(r"^\d{1,2}\.\d{2}\s+(?:AM|PM)\s+\d{1,2}\.\d{2}\s+(?:AM|PM)$"),
    re.compile(r"^[A-Z][A-Z .'()-]* BASIN$"),  # basin headings
    re.compile(r"^Cont/\d+$"),  # continuation marker
    re.compile(r"^Page-\d+$"),  # page marker
    re.compile(r"^NOTE:"),
    re.compile(r"^-\s+DATA NOT AVAILABLE"),
    re.compile(r"^D\.L\.:"),
    re.compile(r"^RHWL:"),
    re.compile(r"^L\.W\.L\.:"),
    re.compile(r"^H\.W\.L\.:"),
    re.compile(r"^\*\s*:"),
]


@dataclass
class RawStationRecord:
    pdf_name: str
    page_number: int
    line_number: int
    raw_text: str


def extract_lines_with_pages(pdf_path: str) -> list[tuple[int, int, str]]:
    records: list[tuple[int, int, str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text is None:
                continue
            for line_index, line in enumerate(text.splitlines(), start=1):
                records.append((page_index, line_index, line))

    return records


def is_station_row(line: str) -> bool:
    return any(pattern.match(line) for pattern in STATION_PATTERNS)


def is_metadata_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return any(pattern.match(stripped) for pattern in METADATA_PATTERNS)


def classify_line(line: str) -> str:
    if is_station_row(line):
        return "station"
    if is_metadata_line(line):
        return "metadata"
    return "unclassified"


def filter_station_rows(
    lines: list[tuple[int, int, str]], pdf_name: str
) -> list[RawStationRecord]:
    return [
        RawStationRecord(
            pdf_name=pdf_name,
            page_number=page_number,
            line_number=line_number,
            raw_text=text,
        )
        for page_number, line_number, text in lines
        if is_station_row(text)
    ]


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    for pdf_file in pdf_files:
        pdf_path = str(data_dir / pdf_file)
        lines_with_pages = extract_lines_with_pages(pdf_path)

        station_records = filter_station_rows(lines_with_pages, pdf_file)
        unclassified = [
            (page, line, text)
            for page, line, text in lines_with_pages
            if classify_line(text) == "unclassified"
        ]

        print("\n" + "=" * 70)
        print(f"File name: {pdf_file}")
        print(f"Number of extracted lines: {len(lines_with_pages)}")
        print(f"Total station records: {len(station_records)}")
        print("=" * 70)

        print("\nFirst 5 station records:")
        for record in station_records[:5]:
            print(f"  {record!r}")

        print("\nLast 5 station records:")
        for record in station_records[-5:]:
            print(f"  {record!r}")

        print("\nUnclassified Lines:")
        if unclassified:
            for page, line, text in unclassified:
                print(f"  page {page}, line {line}: {text}")
        else:
            print("  (none)")


if __name__ == "__main__":
    main()