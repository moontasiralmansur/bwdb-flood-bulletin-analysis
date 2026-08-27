import numpy as np
import pandas as pd

DEFAULT_SEED = 42


def _check_sample_size(df: pd.DataFrame, sample_size: int) -> None:
    if sample_size > len(df):
        raise ValueError(
            f"sample_size {sample_size} exceeds available rows ({len(df)})"
        )


def simple_random_sample(
    df: pd.DataFrame, sample_size: int = 70, seed: int = DEFAULT_SEED
) -> pd.DataFrame:
    _check_sample_size(df, sample_size)
    return df.sample(n=sample_size, random_state=seed)


def systematic_sample(
    df: pd.DataFrame, sample_size: int = 70, seed: int = DEFAULT_SEED
) -> pd.DataFrame:
    """Draw a standard systematic sample of ``sample_size`` rows.

    Algorithm:
      1. Compute the sampling interval k = N / n (N = number of rows,
         n = sample size).
      2. Draw a random start r ~ Uniform(0, k) from a seeded RNG so the
         result is reproducible.
      3. Select the n rows at indices floor(r + i * k) for i = 0 .. n-1.

    Because r < k, the last selected index is strictly below N, so exactly
    n distinct rows are returned. The original DataFrame is not modified
    and column dtypes are preserved (selection is by position via iloc).
    """
    _check_sample_size(df, sample_size)
    n = len(df)
    interval = n / sample_size
    rng = np.random.default_rng(seed)
    start = rng.uniform(0.0, interval)
    indices = np.floor(start + np.arange(sample_size) * interval).astype(int)
    return df.iloc[indices]


def stratified_sample(
    df: pd.DataFrame, sample_size: int = 70, seed: int = DEFAULT_SEED
) -> pd.DataFrame:
    _check_sample_size(df, sample_size)

    if "basin" not in df.columns:
        raise ValueError(
            "Column 'basin' not found. Enrich the dataset with "
            "enrich_with_basin() before stratifying."
        )

    proportions = sample_size * df["basin"].value_counts() / len(df)
    counts = np.floor(proportions).astype(int)

    remainder = sample_size - counts.sum()
    if remainder > 0:
        fractional = proportions - counts
        largest = fractional.sort_values(ascending=False).index[:remainder]
        counts[largest] += 1

    sampled = []
    for basin in counts.index:
        subset = df[df["basin"] == basin]
        sampled.append(subset.sample(n=counts[basin], random_state=seed))

    return pd.concat(sampled)


def summarize_sample(name: str, sample: pd.DataFrame) -> None:
    print(f"\n{name}:")
    print(f"  Sample size: {len(sample)}")
    print(f"  Unique stations: {sample['station_location'].nunique()}")
    print(f"  Above-danger stations: {int(sample['above_danger'].sum())}")
    print(f"  Mean current water level: {sample['current_water_level_m'].mean():.3f}")
    print(f"  Std of current water level: {sample['current_water_level_m'].std():.3f}")


def main() -> None:
    from pathlib import Path

    from data_manager import load_dataset
    from enrich import enrich_with_basin

    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    df = load_dataset("dataset1")
    enriched = enrich_with_basin(df, str(data_dir / "dataset1.pdf"))

    summarize_sample("Population (reference)", enriched)
    summarize_sample("Simple random sample (seed=42)", simple_random_sample(enriched))
    summarize_sample("Systematic sample", systematic_sample(enriched))
    summarize_sample("Stratified sample (basin, seed=42)", stratified_sample(enriched))


if __name__ == "__main__":
    main()