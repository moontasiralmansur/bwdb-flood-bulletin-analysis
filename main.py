import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cross_validate import cross_validate
from pipeline import process_dataset


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data" / "raw"
    pdf_files = ["dataset1.pdf", "dataset2.pdf"]

    results = {}
    for pdf_file in pdf_files:
        df, validation_report = process_dataset(
            str(data_dir / pdf_file), pdf_file, export=True
        )
        results[pdf_file] = (df, validation_report)

    df1, report1 = results["dataset1.pdf"]
    df2, report2 = results["dataset2.pdf"]
    cross_report = cross_validate(df1, df2)

    print("\n" + "=" * 60)
    print("Flood Project - Execution Summary")
    print("=" * 60)

    for pdf_file in pdf_files:
        df, report = results[pdf_file]
        print(f"\n{pdf_file}")
        print(f"  rows: {len(df)}, columns: {len(df.columns)}")
        print(f"  validation anomalies: {len(report['numeric_validation']['parsing_anomalies'])}")
        print(f"  duplicate serials: {report['serial_number']['duplicates']}")
        print(f"  stations above danger level: {int(df['above_danger'].sum())}")

    print("\nCross validation")
    print(f"  matching locations: {cross_report['matching_locations']}")
    print(
        "  duplicate serials: "
        f"dataset1={cross_report['duplicate_serials']['dataset1'] or 'none'}, "
        f"dataset2={cross_report['duplicate_serials']['dataset2'] or 'none'}"
    )
    print(f"  source-data issues: {len(cross_report['potential_source_data_issues'])}")


if __name__ == "__main__":
    main()