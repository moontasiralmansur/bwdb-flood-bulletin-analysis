from pathlib import Path

import pandas as pd


def export_to_excel(df: pd.DataFrame, output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(path, index=False)

    print(f"Output filename: {path}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return path