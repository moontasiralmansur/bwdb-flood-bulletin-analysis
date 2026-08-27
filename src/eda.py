from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from data_manager import load_dataset
from enrich import enrich_with_basin

SUMMARY_ORDER = ["count", "mean", "median", "std", "min", "Q1", "Q3", "max", "IQR"]

FIGURE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "figures"

REDUNDANT_COLUMNS = [
    "rise_cm",
    "water_level_change_cm",
    "fall_cm",
    "below_danger_distance",
]


def _require_basin(df: pd.DataFrame) -> None:
    if "basin" not in df.columns:
        raise ValueError(
            "Column 'basin' not found. Enrich the dataset with enrich_with_basin() first."
        )


def _save(fig, output_path: Path) -> Path:
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_current_water_level_histogram(df: pd.DataFrame, output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(df["current_water_level_m"].dropna(), bins=25, kde=True, ax=ax, color="steelblue")
    ax.set_title("Distribution of Current Water Level")
    ax.set_xlabel("Current Water Level (m MSL)")
    ax.set_ylabel("Frequency")
    return _save(fig, output_path)


def plot_water_level_boxplot_by_basin(df: pd.DataFrame, output_path: Path) -> Path:
    _require_basin(df)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(x="basin", y="current_water_level_m", data=df, ax=ax, palette="Set2")
    ax.set_title("Current Water Level by Basin")
    ax.set_xlabel("Basin")
    ax.set_ylabel("Current Water Level (m MSL)")
    ax.tick_params(axis="x", rotation=15)
    return _save(fig, output_path)


def plot_rise_fall_bar(df: pd.DataFrame, output_path: Path) -> Path:
    counts = {
        "Rise": int((df["rise_cm"] > 0).sum()),
        "Fall": int((df["rise_cm"] < 0).sum()),
        "No Change": int((df["rise_cm"] == 0).sum()),
    }
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(counts.keys(), counts.values(), color=["#2ca02c", "#d62728", "#7f7f7f"])
    ax.set_title("Rise / Fall / No Change Counts")
    ax.set_xlabel("Trend")
    ax.set_ylabel("Number of Stations")
    for i, (label, count) in enumerate(counts.items()):
        ax.text(i, count + 1, str(count), ha="center")
    return _save(fig, output_path)


def plot_above_below_danger_pie(df: pd.DataFrame, output_path: Path) -> Path:
    n_above = int(df["above_danger"].sum())
    n_below = int(df["below_danger_distance"].notna().sum())
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        [n_above, n_below],
        labels=["Above Danger", "Below Danger"],
        autopct="%1.1f%%",
        colors=["#d62728", "#1f77b4"],
        startangle=90,
    )
    ax.set_title("Above Danger vs Below Danger")
    return _save(fig, output_path)


def plot_correlation_heatmap(df: pd.DataFrame, output_path: Path) -> Path:
    numeric = df.select_dtypes(include="number").drop(columns=REDUNDANT_COLUMNS)
    corr = numeric.corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation Heatmap (redundant derived columns excluded)")
    return _save(fig, output_path)


def plot_above_danger_by_basin_bar(df: pd.DataFrame, output_path: Path) -> Path:
    _require_basin(df)
    counts = df.groupby("basin")["above_danger"].sum()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(counts.index, counts.values, color="#d62728")
    ax.set_title("Above Danger Stations by Basin")
    ax.set_xlabel("Basin")
    ax.set_ylabel("Number of Stations Above Danger")
    ax.tick_params(axis="x", rotation=15)
    return _save(fig, output_path)


def generate_eda_figures(
    df: pd.DataFrame, dataset_name: str, output_dir: Path = FIGURE_DIR
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = dataset_name.replace(".pdf", "").replace(".xlsx", "")

    paths = {
        "current_water_level_histogram": plot_current_water_level_histogram(
            df, output_dir / f"{stem}_current_water_level_histogram.png"
        ),
        "current_water_level_boxplot": plot_water_level_boxplot_by_basin(
            df, output_dir / f"{stem}_current_water_level_by_basin_boxplot.png"
        ),
        "rise_fall_nochange_bar": plot_rise_fall_bar(
            df, output_dir / f"{stem}_rise_fall_nochange_bar.png"
        ),
        "above_below_danger_pie": plot_above_below_danger_pie(
            df, output_dir / f"{stem}_above_vs_below_danger_pie.png"
        ),
        "correlation_heatmap": plot_correlation_heatmap(
            df, output_dir / f"{stem}_correlation_heatmap.png"
        ),
        "above_danger_by_basin_bar": plot_above_danger_by_basin_bar(
            df, output_dir / f"{stem}_above_danger_by_basin_bar.png"
        ),
    }
    return paths


def numerical_eda(df: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    overview = {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": {
            "total": int(df.isna().sum().sum()),
            "per_column": {col: int(count) for col, count in df.isna().sum().items()},
        },
    }

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    overview["numeric_columns"] = numeric_cols

    summary = df[numeric_cols].describe().T
    summary["median"] = summary["50%"]
    summary["Q1"] = summary["25%"]
    summary["Q3"] = summary["75%"]
    summary["IQR"] = summary["Q3"] - summary["Q1"]
    summary = summary[SUMMARY_ORDER]

    correlation = df[numeric_cols].corr()

    return overview, summary, correlation


def print_eda_report(name: str, overview: dict, summary: pd.DataFrame, correlation: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print(f"Numerical EDA: {name}")
    print("=" * 60)

    print("\nDataset overview")
    print(f"  Rows: {overview['rows']}")
    print(f"  Columns: {overview['columns']}")
    print(f"  Missing values: {overview['missing_values']['total']} total")
    missing_cols = {
        col: count
        for col, count in overview["missing_values"]["per_column"].items()
        if count > 0
    }
    if missing_cols:
        print("  Missing per column:")
        for col, count in missing_cols.items():
            print(f"    {col}: {count}")

    print("\nSummary statistics (numeric columns)")
    print(summary.round(4).to_string())

    print("\nCorrelation matrix")
    print(correlation.round(4).to_string())


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    for name in ("dataset1", "dataset2"):
        df = load_dataset(name)
        enriched = enrich_with_basin(df, str(data_dir / f"{name}.pdf"))

        overview, summary, correlation = numerical_eda(enriched)
        print_eda_report(name, overview, summary, correlation)

        figure_paths = generate_eda_figures(enriched, name)
        print("\nSaved figures:")
        for key, path in figure_paths.items():
            print(f"  {key}: {path}")


if __name__ == "__main__":
    main()