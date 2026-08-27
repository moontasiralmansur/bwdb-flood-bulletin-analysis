import pdfplumber
from pathlib import Path


def inspect_pdf(pdf_path: Path) -> None:
    print(f"\n{'=' * 70}")
    print(f"File name: {pdf_path.name}")
    print(f"Path: {pdf_path}")
    print(f"{'=' * 70}")

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        print(f"Number of pages: {num_pages}")

        for page_idx, page in enumerate(pdf.pages):
            print(f"\n--- Page {page_idx + 1} ---")

            tables = page.extract_tables()
            has_tables = len(tables) > 0

            print(f"Tables detected on this page: {has_tables}")
            print(f"Number of detected tables: {len(tables)}")

            for table_idx, table in enumerate(tables):
                if table:
                    num_rows = len(table)
                    num_cols = len(table[0]) if table[0] else 0
                    print(f"\n  Table {table_idx + 1}: {num_rows} rows x {num_cols} columns")
                    print("  First 5 rows:")
                    for row in table[:5]:
                        print(f"    {row}")
                else:
                    print(f"\n  Table {table_idx + 1}: Empty table detected")


def main() -> None:
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    pdf_files = sorted(raw_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {raw_dir}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in {raw_dir}:")
    for p in pdf_files:
        print(f"  - {p.name}")

    for pdf_file in pdf_files:
        inspect_pdf(pdf_file)


if __name__ == "__main__":
    main()
