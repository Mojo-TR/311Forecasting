import pandas as pd
import numpy as np
from pathlib import Path
from app.utils.data_loader import df

OUTPUT = Path("precomputed_data/forecast")
OUTPUT.mkdir(parents=True, exist_ok=True)

# Base Preparation
def prepare_base(df_in):
    df2 = df_in.copy()
    df2["ds"] = df2["CREATED DATE"].dt.to_period("M").dt.to_timestamp("M")
    return df2


# MONTHLY VOLUME BASE
def compute_monthly_volume(df2):

    rows = []

    for neigh, group in df2.groupby(df2["NEIGHBORHOOD"].fillna("CITYWIDE")):
        temp = (
            group
            .groupby("ds")
            .size()
            .reset_index(name="Count")
        )
        temp["NEIGHBORHOOD"] = neigh
        rows.append(temp)

    out = pd.concat(rows, ignore_index=True)

    # To support citywide correctness:
    out["YearMonthStr"] = out["ds"].dt.strftime("%Y-%m")

    out.to_parquet(OUTPUT / "monthly_volume_full.parquet", index=False)
    print("✓ monthly_volume_full.parquet created:", len(out))


# VALID CITYWIDE MONTHS
def compute_valid_citywide(df2):
    monthly = (
        df2.groupby("ds")
        .size()
        .reset_index(name="Count")
        .sort_values("ds")
    )
    monthly["YearMonth"] = monthly["ds"].dt.strftime("%Y-%m")

    monthly.to_parquet(OUTPUT / "valid_citywide_months.parquet", index=False)
    print("✓ valid_citywide_months.parquet created")


# SEVERITY METRIC
def compute_severity(df2):
    """
    Severity = monthly mean of capped resolution time
    Matches notebook logic exactly.
    """

    df2 = df2.copy()

    # 1. Global 95% cap
    cap = df2["RESOLUTION_TIME_DAYS"].quantile(0.95)
    df2["RESOLUTION"] = df2["RESOLUTION_TIME_DAYS"].clip(upper=cap)

    # 2. Drop last 2 months (incomplete)
    latest = df2["ds"].max()
    cutoff = (latest.to_period("M") - 1).to_timestamp("M")
    df2 = df2[df2["ds"] < cutoff]

    # 3. Fill missing resolution by CASE TYPE median
    medians = df2.groupby("CASE TYPE")["RESOLUTION"].median()
    df2["RESOLUTION"] = df2.apply(
        lambda r: medians.get(r["CASE TYPE"])
        if pd.isna(r["RESOLUTION"]) else r["RESOLUTION"],
        axis=1
    )

    # 4. Drop remaining NaNs
    df2 = df2.dropna(subset=["RESOLUTION"])

    # ---- AGGREGATIONS ----

    # CITYWIDE
    city = (
        df2.groupby("ds")["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    city.to_parquet(OUTPUT / "monthly_severity_citywide.parquet", index=False)

    # NEIGHBORHOOD
    neigh = (
        df2.groupby(["ds", "NEIGHBORHOOD"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    neigh.to_parquet(OUTPUT / "monthly_severity_neighborhood.parquet", index=False)

    # DEPARTMENT
    dept = (
        df2.groupby(["ds", "DEPARTMENT"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    dept.to_parquet(OUTPUT / "monthly_severity_department.parquet", index=False)

    # DIVISION
    div = (
        df2.groupby(["ds", "DIVISION"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    div.to_parquet(OUTPUT / "monthly_severity_division.parquet", index=False)

    # CATEGORY
    cat = (
        df2.groupby(["ds", "CATEGORY"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    cat.to_parquet(OUTPUT / "monthly_severity_category.parquet", index=False)

    print("✓ Severity precompute matches notebook")


# MAIN RUNNER
def run_precompute_forecast_inputs():
    print("🔧 Precomputing Forecast Inputs...")
    df2 = prepare_base(df)

    compute_monthly_volume(df2)
    compute_valid_citywide(df2)
    compute_severity(df2)

    print("✅ Forecast Precompute Complete!")


if __name__ == "__main__":
    run_precompute_forecast_inputs()
