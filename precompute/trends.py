import pandas as pd
from pathlib import Path
from app.utils.data_loader import df

OUTPUT_DIR = Path("precomputed_data/trends")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_base_fields(df_in: pd.DataFrame) -> pd.DataFrame:
    df2 = df_in.copy()
    df2["Month"] = df2["CREATED DATE"].dt.month_name()
    df2["Month_Year"] = df2["CREATED DATE"].dt.to_period("M").astype(str)
    df2["Year"] = df2["CREATED DATE"].dt.year
    df2["MonthNum"] = df2["CREATED DATE"].dt.month
    return df2


def compute_cleaned_neighborhood_list(df_in: pd.DataFrame):
    neighborhoods = (
        df_in["NEIGHBORHOOD"]
        .dropna()
        .loc[lambda s: (s.str.strip() != "") & (s != "None")]
        .unique()
    )

    out = pd.DataFrame({"NEIGHBORHOOD": sorted(neighborhoods)})
    out.to_parquet(OUTPUT_DIR / "neighborhoods_cleaned.parquet", index=False)


def precompute_monthly(df_in):
    """Unified monthly dataset: city + neighborhood."""
    # Citywide
    city = (
        df_in.groupby("Month_Year")
        .size()
        .reset_index(name="Count")
        .assign(NEIGHBORHOOD=None, Level="city")
    )

    # Neighborhood-level
    neigh = (
        df_in.groupby(["NEIGHBORHOOD", "Month_Year"])
        .size()
        .reset_index(name="Count")
        .assign(Level="neigh")
    )

    monthly_all = pd.concat([city, neigh], ignore_index=True)
    monthly_all.sort_values("Month_Year", inplace=True)

    monthly_all.to_parquet(OUTPUT_DIR / "monthly_all.parquet", index=False)
    print("✓ monthly_all.parquet generated")


def precompute_seasonal(df_in):
    """Unified seasonal dataset: city + neighborhood."""
    df2 = df_in.copy()
    df2["Month"] = df2["CREATED DATE"].dt.month_name()
    df2["MonthNum"] = df2["CREATED DATE"].dt.month
    df2["Year"] = df2["CREATED DATE"].dt.year

    # Citywide
    city = (
        df2.groupby(["Year", "Month", "MonthNum"])
        .size()
        .reset_index(name="Count")
        .assign(NEIGHBORHOOD=None, Level="city")
    )

    # Neighborhood-level
    neigh = (
        df2.groupby(["NEIGHBORHOOD", "Year", "Month", "MonthNum"])
        .size()
        .reset_index(name="Count")
        .assign(Level="neigh")
    )

    seasonal_all = pd.concat([city, neigh], ignore_index=True)
    seasonal_all.sort_values(["Year", "MonthNum"], inplace=True)

    seasonal_all.to_parquet(OUTPUT_DIR / "seasonal_all.parquet", index=False)
    print("✓ seasonal_all.parquet generated")


def run_precompute_timeseries():
    print("🧮 Precomputing unified complaint trends…")

    df2 = compute_base_fields(df)

    compute_cleaned_neighborhood_list(df2)
    precompute_monthly(df2)
    precompute_seasonal(df2)

    print("✅ Complaint Trends precompute complete!")


if __name__ == "__main__":
    run_precompute_timeseries()