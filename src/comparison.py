from pathlib import Path

import pandas as pd

from data_manager import load_dataset
from enrich import enrich_with_basin
from probability import probability_summary

KEY_VARIABLES = [
    "rhwl_m",
    "danger_level_m",
    "previous_water_level_m",
    "current_water_level_m",
    "rise_cm",
    "fall_cm",
]

STATS = ["mean", "median", "std", "min", "max"]

PROBABILITIES = [
    "p_above_danger",
    "p_below_danger",
    "p_rise",
    "p_fall",
    "p_no_change",
]


def _overview(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
    }


def _descriptive_comparison(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    part1 = df1[KEY_VARIABLES].agg(STATS).T
    part2 = df2[KEY_VARIABLES].agg(STATS).T
    return pd.concat({"dataset1": part1, "dataset2": part2}, axis=1)


def _probability_comparison(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    overall1, _ = probability_summary(df1)
    overall2, _ = probability_summary(df2)
    return pd.DataFrame(
        {"dataset1": [overall1[p] for p in PROBABILITIES],
         "dataset2": [overall2[p] for p in PROBABILITIES]},
        index=PROBABILITIES,
    )


def _basin_comparison(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    def basin_stats(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby("basin").agg(
            n_stations=("current_water_level_m", "count"),
            n_above=("above_danger", "sum"),
            mean_wl=("current_water_level_m", "mean"),
        )

    return pd.concat({"dataset1": basin_stats(df1), "dataset2": basin_stats(df2)}, axis=1)


def _change_summary(df1: pd.DataFrame, df2: pd.DataFrame) -> dict:
    k1 = df1["station_location"].str.replace(" ", "")
    k2 = df2["station_location"].str.replace(" ", "")

    merged = df1.assign(_k=k1)[["_k", "station_location", "current_water_level_m"]].rename(
        columns={"station_location": "location"}
    ).merge(
        df2.assign(_k=k2)[["_k", "current_water_level_m"]],
        on="_k",
        suffixes=("_09", "_15"),
    )
    merged["change_m"] = merged["current_water_level_m_15"] - merged["current_water_level_m_09"]

    above_09 = set(df1.loc[df1["above_danger"], "station_location"].str.replace(" ", ""))
    above_15 = set(df2.loc[df2["above_danger"], "station_location"].str.replace(" ", ""))

    rises = merged.nlargest(3, "change_m")
    falls = merged.nsmallest(3, "change_m")

    mean_delta = df2["current_water_level_m"].mean() - df1["current_water_level_m"].mean()
    if mean_delta > 0:
        mean_point = (
            f"Mean current water level rose from {df1['current_water_level_m'].mean():.3f} m "
            f"to {df2['current_water_level_m'].mean():.3f} m between 09:00 and 15:00"
        )
    elif mean_delta < 0:
        mean_point = (
            f"Mean current water level fell from {df1['current_water_level_m'].mean():.3f} m "
            f"to {df2['current_water_level_m'].mean():.3f} m between 09:00 and 15:00"
        )
    else:
        mean_point = (
            f"Mean current water level was unchanged at {df1['current_water_level_m'].mean():.3f} m "
            f"between 09:00 and 15:00"
        )

    above_delta = len(above_15) - len(above_09)
    if above_delta > 0:
        above_point = (
            f"Above-danger stations increased from {len(above_09)} to {len(above_15)}"
        )
    elif above_delta < 0:
        above_point = (
            f"Above-danger stations decreased from {len(above_09)} to {len(above_15)}"
        )
    else:
        above_point = f"Above-danger stations stayed at {len(above_09)}"

    points = [
        mean_point,
        above_point,
        f"{len(merged)} stations matched; {int((merged['change_m'] > 0).sum())} rose, "
        f"{int((merged['change_m'] < 0).sum())} fell between bulletins",
    ]
    for i, (_, row) in enumerate(rises.iterrows(), start=1):
        points.append(f"Largest rise #{i}: {row['location']} +{row['change_m']:.2f} m")
    for i, (_, row) in enumerate(falls.iterrows(), start=1):
        points.append(f"Largest fall #{i}: {row['location']} {row['change_m']:.2f} m")

    return {
        "bulletins": "09:00 vs 15:00",
        "n_stations_rising": int((merged["change_m"] > 0).sum()),
        "n_stations_falling": int((merged["change_m"] < 0).sum()),
        "newly_above_danger": sorted(
            df2.loc[df2["station_location"].str.replace(" ", "").isin(above_15 - above_09),
                    "station_location"].tolist()
        ),
        "biggest_rises": rises[["location", "change_m"]].round(2).to_dict("records"),
        "biggest_falls": falls[["location", "change_m"]].round(2).to_dict("records"),
        "points": points,
    }


def compare_datasets(df1: pd.DataFrame, df2: pd.DataFrame) -> tuple[dict, dict[str, pd.DataFrame]]:
    comparison = {
        "overview": {"dataset1": _overview(df1), "dataset2": _overview(df2)},
        "descriptive": _descriptive_comparison(df1, df2),
        "probability": _probability_comparison(df1, df2),
        "basin": _basin_comparison(df1, df2),
        "change_summary": _change_summary(df1, df2),
    }
    report_dfs = {
        "descriptive": comparison["descriptive"],
        "probability": comparison["probability"],
        "basin": comparison["basin"],
    }
    return comparison, report_dfs


def print_comparison_report(comparison: dict) -> None:
    print("\n" + "=" * 60)
    print("Dataset Comparison Report (09:00 vs 15:00)")
    print("=" * 60)

    print("\n1. Dataset Overview")
    for name, overview in comparison["overview"].items():
        print(f"  {name}: {overview['rows']} rows, {overview['columns']} columns, "
              f"{overview['missing_values']} missing values")

    print("\n2. Descriptive Comparison")
    print(comparison["descriptive"].round(4).to_string())

    print("\n3. Probability Comparison")
    print(comparison["probability"].round(4).to_string())

    print("\n4. Basin Comparison")
    print(comparison["basin"].round(4).to_string())

    print("\n5. Change Summary")
    for point in comparison["change_summary"]["points"]:
        print(f"  - {point}")


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    dfs = {}
    for name in ("dataset1", "dataset2"):
        df = load_dataset(name)
        dfs[name] = enrich_with_basin(df, str(data_dir / f"{name}.pdf"))

    comparison, _ = compare_datasets(dfs["dataset1"], dfs["dataset2"])
    print_comparison_report(comparison)


if __name__ == "__main__":
    main()