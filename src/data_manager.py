from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

EXPECTED_COLUMNS = [
    "dataset",
    "station_number",
    "station_location",
    "rhwl_m",
    "danger_level_m",
    "previous_water_level_m",
    "current_water_level_m",
    "rise_cm",
    "fall_cm",
    "water_level_change_m",
    "water_level_change_cm",
    "above_danger",
    "above_danger_distance",
    "below_danger_distance",
]


def _resolve_dataset_name(dataset_name: str) -> str:
    name = Path(dataset_name).stem
    name = name.replace("_clean", "")
    if name not in ("dataset1", "dataset2"):
        raise ValueError(f"Unknown dataset name: {dataset_name!r}")
    return name


def load_dataset(dataset_name: str) -> pd.DataFrame:
    name = _resolve_dataset_name(dataset_name)
    path = PROCESSED_DIR / f"{name}_clean.xlsx"

    if not path.exists():
        raise FileNotFoundError(f"Missing processed dataset: {path}")

    df = pd.read_excel(path)
    validate_required_columns(df)
    print(f"Loaded: {path.name} ({len(df)} rows, {len(df.columns)} columns)")
    return df


def load_all_datasets() -> dict[str, pd.DataFrame]:
    return {
        "dataset1": load_dataset("dataset1"),
        "dataset2": load_dataset("dataset2"),
    }


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Expected {len(EXPECTED_COLUMNS)} columns."
        )
    print(f"All required columns present ({len(EXPECTED_COLUMNS)})")