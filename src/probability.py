from pathlib import Path

import pandas as pd

from data_manager import load_dataset
from enrich import enrich_with_basin

REQUIRED_COLUMNS = [
    "basin",
    "above_danger",
    "rise_cm",
    "danger_level_m",
    "current_water_level_m",
]


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def probability_summary(df: pd.DataFrame) -> tuple[dict, dict[str, pd.DataFrame]]:
    _require_columns(df, REQUIRED_COLUMNS)
    total = len(df)

    valid_dl = df["danger_level_m"].notna() & df["current_water_level_m"].notna()
    n_valid_dl = int(valid_dl.sum())
    n_above = int(df["above_danger"].sum())
    n_below = n_valid_dl - n_above

    valid_rise = df["rise_cm"].notna()
    n_rise = int((df["rise_cm"] > 0).sum())
    n_fall = int((df["rise_cm"] < 0).sum())
    n_no_change = int((df["rise_cm"] == 0).sum())
    n_valid_rise = n_rise + n_fall + n_no_change

    overall = {
        "p_above_danger": round(n_above / n_valid_dl, 4),
        "p_below_danger": round(n_below / n_valid_dl, 4),
        "p_rise": round(n_rise / n_valid_rise, 4),
        "p_fall": round(n_fall / n_valid_rise, 4),
        "p_no_change": round(n_no_change / n_valid_rise, 4),
        "n_total": total,
        "n_valid_dl": n_valid_dl,
        "n_valid_rise": n_valid_rise,
    }

    cond_above = (
        df[valid_dl].groupby("basin")["above_danger"].mean().round(4).to_dict()
    )
    cond_rise = (
        df[valid_rise]
        .groupby("basin")["rise_cm"]
        .apply(lambda series: (series > 0).mean())
        .round(4)
        .to_dict()
    )

    frequencies = {
        "danger": pd.DataFrame(
            {"count": [n_above, n_below, total - n_valid_dl]},
            index=["Above Danger", "Below Danger", "Unknown (missing D.L./W.L.)"],
        ),
        "change": pd.DataFrame(
            {"count": [n_rise, n_fall, n_no_change, total - n_valid_rise]},
            index=["Rise", "Fall", "No Change", "Missing Data"],
        ),
        "basin": df["basin"].value_counts().rename("count").to_frame(),
    }

    return overall, {"conditional": {"p_above_danger_by_basin": cond_above, "p_rise_by_basin": cond_rise}, "frequencies": frequencies}


def print_probability_summary(name: str, overall: dict, conditional: dict, frequencies: dict[str, pd.DataFrame]) -> None:
    print("\n" + "=" * 60)
    print(f"Probability Analysis: {name}")
    print("=" * 60)

    print("\nOverall probabilities")
    print(
        f"  P(Above Danger) = {overall['p_above_danger']} "
        f"({frequencies['danger'].loc['Above Danger', 'count']}/{overall['n_valid_dl']})"
    )
    print(
        f"  P(Below Danger) = {overall['p_below_danger']} "
        f"({frequencies['danger'].loc['Below Danger', 'count']}/{overall['n_valid_dl']})"
    )
    print(
        f"  P(Rise) = {overall['p_rise']} "
        f"({frequencies['change'].loc['Rise', 'count']}/{overall['n_valid_rise']})"
    )
    print(
        f"  P(Fall) = {overall['p_fall']} "
        f"({frequencies['change'].loc['Fall', 'count']}/{overall['n_valid_rise']})"
    )
    print(
        f"  P(No Change) = {overall['p_no_change']} "
        f"({frequencies['change'].loc['No Change', 'count']}/{overall['n_valid_rise']})"
    )

    print("\nConditional probabilities")
    print("  P(Above Danger | Basin):")
    for basin, p in conditional["p_above_danger_by_basin"].items():
        print(f"    {basin}: {p}")
    print("  P(Rise | Basin):")
    for basin, p in conditional["p_rise_by_basin"].items():
        print(f"    {basin}: {p}")

    print("\nFrequency tables")
    print("  Above/Below danger:")
    print(frequencies["danger"].to_string().replace("\n", "\n    "))
    print("\n  Rise/Fall/No Change:")
    print(frequencies["change"].to_string().replace("\n", "\n    "))
    print("\n  Basin counts:")
    print(frequencies["basin"].to_string().replace("\n", "\n    "))


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"

    for name in ("dataset1", "dataset2"):
        df = load_dataset(name)
        enriched = enrich_with_basin(df, str(data_dir / f"{name}.pdf"))

        overall, rest = probability_summary(enriched)
        print_probability_summary(name, overall, rest["conditional"], rest["frequencies"])


if __name__ == "__main__":
    main()