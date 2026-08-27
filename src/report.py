from pathlib import Path

import pandas as pd

from comparison import compare_datasets
from data_manager import load_dataset
from eda import numerical_eda
from enrich import enrich_with_basin
from probability import probability_summary
from sampling import (
    DEFAULT_SEED,
    simple_random_sample,
    stratified_sample,
    systematic_sample,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
TABLES_DIR = OUTPUT_DIR / "tables"
SAMPLES_DIR = OUTPUT_DIR / "samples"
REPORTS_DIR = OUTPUT_DIR / "reports"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

SAMPLE_SIZE = 70

KEY_STATS_VARIABLES = [
    "rhwl_m",
    "danger_level_m",
    "current_water_level_m",
    "rise_cm",
    "fall_cm",
]


def ensure_output_dirs() -> None:
    for directory in (TABLES_DIR, SAMPLES_DIR, REPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(str(part) for part in col) for col in df.columns]
    return df


def export_descriptive_statistics(
    dfs: dict[str, pd.DataFrame], output_path: Path
) -> Path:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for name, df in dfs.items():
            _, summary, _ = numerical_eda(df)
            summary.to_excel(writer, sheet_name=name)
    print(f"Exported: {output_path}")
    return output_path


def export_probability_summary(
    dfs: dict[str, pd.DataFrame], output_path: Path
) -> Path:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for name, df in dfs.items():
            overall, rest = probability_summary(df)
            pd.Series(overall).to_frame("value").to_excel(
                writer, sheet_name=f"{name}_overall"
            )
            conditional = rest["conditional"]
            pd.DataFrame(
                {
                    "p_above_danger": conditional["p_above_danger_by_basin"],
                    "p_rise": conditional["p_rise_by_basin"],
                }
            ).to_excel(writer, sheet_name=f"{name}_conditional")

            frequencies = rest["frequencies"]
            for key, label in (("danger", "danger"), ("change", "change"), ("basin", "basin")):
                frequencies[key].to_excel(writer, sheet_name=f"{name}_frequency_{label}")
    print(f"Exported: {output_path}")
    return output_path


def export_comparison(comparison: dict, output_path: Path) -> Path:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        flatten_columns(comparison["descriptive"]).to_excel(writer, sheet_name="descriptive")
        comparison["probability"].to_excel(writer, sheet_name="probability")
        flatten_columns(comparison["basin"]).to_excel(writer, sheet_name="basin")
        pd.DataFrame({"point": comparison["change_summary"]["points"]}).to_excel(
            writer, sheet_name="change_summary"
        )
    print(f"Exported: {output_path}")
    return output_path


def export_basin_summary(dfs: dict[str, pd.DataFrame], output_path: Path) -> Path:
    comparison, report_dfs = compare_datasets(dfs["dataset1"], dfs["dataset2"])
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        flatten_columns(report_dfs["basin"]).to_excel(writer, sheet_name="basin_comparison")
        for name, df in dfs.items():
            df["basin"].value_counts().rename("count").to_frame().to_excel(
                writer, sheet_name=f"{name}_counts"
            )
    print(f"Exported: {output_path}")
    return output_path


def export_samples(df: pd.DataFrame, samples_dir: Path = SAMPLES_DIR) -> dict[str, Path]:
    samples = {
        "simple_random_sample": simple_random_sample(df, SAMPLE_SIZE, DEFAULT_SEED),
        "systematic_sample": systematic_sample(df, SAMPLE_SIZE),
        "stratified_sample": stratified_sample(df, SAMPLE_SIZE, DEFAULT_SEED),
    }
    paths = {}
    for key, sample in samples.items():
        path = samples_dir / f"{key}.xlsx"
        sample.to_excel(path, index=False)
        print(f"Exported: {path}")
        paths[key] = path
    return paths


def _md_table(rows: list[list], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def build_markdown_report(
    overviews: dict,
    basin_counts: dict,
    sampling_summaries: dict,
    probability_results: dict,
    eda_results: dict,
    comparison: dict,
    dfs: dict[str, pd.DataFrame],
) -> str:
    sections: list[str] = []

    sections.append("# Project Overview\n")
    n_stations = int(dfs["dataset1"]["station_number"].notna().sum())
    n_basins = int(dfs["dataset1"]["basin"].nunique())
    sections.append(
        "This project analyses flood bulletins published by the Bangladesh Water "
        "Development Board (BWDB) for 20-07-2026. Two bulletins (09:00 and 15:00) "
        f"covering {n_stations} monitoring stations across {n_basins} river basins "
        "were extracted from "
        "PDF, parsed line-by-line, validated, cleaned and enriched with basin "
        "information. The analysis covers sampling, empirical probability analysis, "
        "exploratory data analysis (EDA) and a statistical comparison of the two "
        "bulletins.\n"
    )

    sections.append("## Dataset Summary\n")
    sections.append(
        _md_table(
            [
                [
                    name,
                    overview["rows"],
                    overview["columns"],
                    overview["missing_values"],
                ]
                for name, overview in overviews.items()
            ],
            ["Dataset", "Rows", "Columns", "Missing values"],
        )
        + "\n"
    )
    first_name = list(basin_counts)[0]
    sections.append(f"### Basin distribution ({first_name})\n")
    sections.append(
        _md_table(
            [[basin, count] for basin, count in basin_counts[first_name].items()],
            ["Basin", "Stations"],
        )
        + "\n"
    )

    sections.append("## Sampling Summary\n")
    sections.append(
        "Samples of size 70 were drawn from dataset1 (09:00 bulletin) with a fixed "
        f"random seed ({DEFAULT_SEED}).\n"
    )
    sections.append(
        _md_table(
            [
                [name] + [summary[stat] for stat in ("size", "unique_stations", "above_danger", "mean_wl", "std_wl")]
                for name, summary in sampling_summaries.items()
            ],
            ["Method", "Size", "Unique stations", "Above danger", "Mean WL (m)", "Std WL (m)"],
        )
        + "\n"
    )

    sections.append("## Probability Analysis\n")
    sections.append("### Overall probabilities\n")
    sections.append(
        _md_table(
            [
                [metric]
                + [probability_results[name]["overall"][metric] for name in ("dataset1", "dataset2")]
                for metric in ("p_above_danger", "p_below_danger", "p_rise", "p_fall", "p_no_change")
            ],
            ["Probability", "dataset1 (09:00)", "dataset2 (15:00)"],
        )
        + "\n"
    )
    sections.append("### P(Above Danger | Basin)\n")
    sections.append(
        _md_table(
            [
                [basin]
                + [
                    probability_results[name]["conditional"]["p_above_danger_by_basin"][basin]
                    for name in ("dataset1", "dataset2")
                ]
                for basin in basin_counts["dataset1"].index
            ],
            ["Basin", "dataset1 (09:00)", "dataset2 (15:00)"],
        )
        + "\n"
    )

    sections.append("## Exploratory Data Analysis\n")
    sections.append("### Key statistics\n")
    sections.append(
        _md_table(
            [
                [variable]
                + [
                    f"{eda_results[name]['descriptive'].loc[variable, stat]:.4f}"
                    for name in ("dataset1", "dataset2")
                    for stat in ("mean", "median")
                ]
                for variable in KEY_STATS_VARIABLES
            ],
            ["Variable", "Mean d1", "Median d1", "Mean d2", "Median d2"],
        )
        + "\n"
    )
    sections.append("### Strongest correlations (dataset1)\n")
    sections.append(
        _md_table(
            [
                [var1, var2, f"{corr:.4f}"]
                for var1, var2, corr in eda_results["dataset1"]["top_correlations"]
            ],
            ["Variable 1", "Variable 2", "Correlation"],
        )
        + "\n"
    )

    sections.append("## Dataset Comparison\n")
    sections.append("### Probability comparison\n")
    sections.append(
        _md_table(
            [
                [metric, comparison["probability"].loc[metric, "dataset1"],
                 comparison["probability"].loc[metric, "dataset2"]]
                for metric in comparison["probability"].index
            ],
            ["Probability", "dataset1 (09:00)", "dataset2 (15:00)"],
        )
        + "\n"
    )
    sections.append("### Change summary (09:00 to 15:00)\n")
    sections.append("\n".join(f"- {point}" for point in comparison["change_summary"]["points"]))
    sections.append("\n")

    sections.append("## Key Findings\n")
    sections.append("\n".join(f"- {finding}" for finding in build_key_findings(comparison, probability_results, eda_results, dfs)))
    sections.append("\n")

    return "\n".join(sections)


def build_key_findings(comparison: dict, probability_results: dict, eda_results: dict, dfs: dict[str, pd.DataFrame]) -> list[str]:
    findings = []
    df1, df2 = dfs["dataset1"], dfs["dataset2"]

    def _trend(before: float, after: float) -> str:
        if after > before:
            return "increased"
        if after < before:
            return "decreased"
        return "remained unchanged"

    n_above_d1 = int(df1["above_danger"].sum())
    n_above_d2 = int(df2["above_danger"].sum())
    newly_above = comparison["change_summary"]["newly_above_danger"]

    if n_above_d2 > n_above_d1:
        trend_text = f"Above-danger stations increased from {n_above_d1} to {n_above_d2}"
    elif n_above_d2 < n_above_d1:
        trend_text = f"Above-danger stations decreased from {n_above_d1} to {n_above_d2}"
    else:
        trend_text = f"Above-danger stations stayed at {n_above_d1}"

    if newly_above:
        basin_names = sorted(
            {
                df2.loc[df2["station_location"] == loc, "basin"].iloc[0]
                for loc in newly_above
                if (df2["station_location"] == loc).any()
            }
        )
        basin_text = (
            f" in the {' and '.join(basin_names)}" if basin_names else ""
        )
        names_text = (
            ", ".join(newly_above)
            if len(newly_above) > 1
            else f"{newly_above[0]} crossed its danger level"
        )
        if len(newly_above) > 1:
            names_text = f"{names_text} crossed their danger levels"
        findings.append(
            f"{trend_text} between 09:00 and 15:00; {names_text}{basin_text}."
        )
    else:
        findings.append(
            f"{trend_text} between 09:00 and 15:00; no station crossed its danger level."
        )

    p_rise_d1 = probability_results["dataset1"]["overall"]["p_rise"]
    p_rise_d2 = probability_results["dataset2"]["overall"]["p_rise"]
    p_nc_d1 = probability_results["dataset1"]["overall"]["p_no_change"]
    p_nc_d2 = probability_results["dataset2"]["overall"]["p_no_change"]

    nc_pct = (p_nc_d2 - p_nc_d1) / p_nc_d1 * 100 if p_nc_d1 > 0 else None
    pct_text = f" ({nc_pct:+.1f}%)" if nc_pct is not None else ""
    findings.append(
        f"P(Rise) {_trend(p_rise_d1, p_rise_d2)} from {p_rise_d1:.4f} to {p_rise_d2:.4f} "
        f"between the bulletins, while P(No Change) {_trend(p_nc_d1, p_nc_d2)} "
        f"from {p_nc_d1:.4f} to {p_nc_d2:.4f}{pct_text}."
    )

    brahmaputra = probability_results["dataset1"]["conditional"]["p_rise_by_basin"]
    if brahmaputra:
        top_basin = max(brahmaputra, key=brahmaputra.get)
        findings.append(
            f"The highest P(Rise | Basin) at 09:00 was {brahmaputra[top_basin]:.4f} "
            f"({top_basin})."
        )

    rises = comparison["change_summary"]["biggest_rises"]
    if rises:
        biggest = rises[0]
        findings.append(
            f"Largest water-level jump between bulletins: {biggest['location']} "
            f"+{biggest['change_m']:.2f} m."
        )

    top_corr = eda_results["dataset1"]["rhwl_danger_level_corr"]
    findings.append(
        f"RHWL and Danger Level correlate at {top_corr:.3f}, confirming stable "
        "station reference levels."
    )

    return findings


def build_eda_results(dfs: dict[str, pd.DataFrame]) -> dict:
    results = {}
    for name, df in dfs.items():
        _, summary, correlation = numerical_eda(df)

        kept = correlation.drop(
            columns=["rise_cm", "water_level_change_cm", "fall_cm",
                     "below_danger_distance", "above_danger_distance",
                     "water_level_change_m"],
            errors="ignore",
        )
        upper = kept.where(
            ~pd.DataFrame(
                {col: kept.index == col for col in kept.columns},
                index=kept.index,
            )
        )
        pairs = upper.stack().dropna()
        top = pairs.abs().sort_values(ascending=False).head(3)
        top_correlations = [(pair[0], pair[1], float(pairs[pair])) for pair in top.index]

        results[name] = {
            "descriptive": summary[["mean", "median"]],
            "top_correlations": top_correlations,
            "rhwl_danger_level_corr": float(correlation.loc["rhwl_m", "danger_level_m"]),
        }
    return results


def generate_all() -> None:
    ensure_output_dirs()

    dfs = {
        name: enrich_with_basin(load_dataset(name), str(RAW_DIR / f"{name}.pdf"))
        for name in ("dataset1", "dataset2")
    }

    overviews = {
        name: {
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": int(df.isna().sum().sum()),
        }
        for name, df in dfs.items()
    }
    basin_counts = {
        name: df["basin"].value_counts() for name, df in dfs.items()
    }

    comparison, _ = compare_datasets(dfs["dataset1"], dfs["dataset2"])

    probability_results = {}
    for name, df in dfs.items():
        overall, rest = probability_summary(df)
        probability_results[name] = {"overall": overall, "conditional": rest["conditional"]}

    eda_results = build_eda_results(dfs)

    sampling_summaries = {
        "simple random": {"size": SAMPLE_SIZE},
        "systematic": {"size": SAMPLE_SIZE},
        "stratified": {"size": SAMPLE_SIZE},
    }
    samples = {
        "simple random": simple_random_sample(dfs["dataset1"], SAMPLE_SIZE, DEFAULT_SEED),
        "systematic": systematic_sample(dfs["dataset1"], SAMPLE_SIZE),
        "stratified": stratified_sample(dfs["dataset1"], SAMPLE_SIZE, DEFAULT_SEED),
    }
    for key, sample in samples.items():
        sampling_summaries[key].update(
            {
                "unique_stations": sample["station_location"].nunique(),
                "above_danger": int(sample["above_danger"].sum()),
                "mean_wl": round(sample["current_water_level_m"].mean(), 4),
                "std_wl": round(sample["current_water_level_m"].std(), 4),
            }
        )

    export_descriptive_statistics(dfs, TABLES_DIR / "descriptive_statistics.xlsx")
    export_probability_summary(dfs, TABLES_DIR / "probability_summary.xlsx")
    export_comparison(comparison, TABLES_DIR / "dataset_comparison.xlsx")
    export_basin_summary(dfs, TABLES_DIR / "basin_summary.xlsx")

    export_samples(dfs["dataset1"], SAMPLES_DIR)

    markdown = build_markdown_report(
        overviews,
        basin_counts,
        sampling_summaries,
        probability_results,
        eda_results,
        comparison,
        dfs,
    )
    report_path = REPORTS_DIR / "analysis_summary.md"
    report_path.write_text(markdown, encoding="utf-8")
    print(f"Report written: {report_path}")


if __name__ == "__main__":
    generate_all()