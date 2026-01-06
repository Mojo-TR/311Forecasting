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
    df2 = df2.copy()

    latest = df2["ds"].max()
    df2 = df2[df2["ds"] < latest]   # drops the latest month

    rows = []
    aggregations = [
        ([], "citywide"),

        # CITYWIDE item-level
        (["DEPARTMENT"], "department"),
        (["DIVISION"], "division"),
        (["CATEGORY"], "category"),

        # Neighborhood-level
        (["NEIGHBORHOOD"], "neighborhood"),
        (["NEIGHBORHOOD", "DEPARTMENT"], "neighborhood_department"),
        (["NEIGHBORHOOD", "DIVISION"], "neighborhood_division"),
        (["NEIGHBORHOOD", "CATEGORY"], "neighborhood_category"),
    ]


    for group_cols, level in aggregations:
        temp = (
            df2.groupby(["ds"] + group_cols)
            .size()
            .reset_index(name="Count")
        )

        for col in ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY"]:
            if col not in temp.columns:
                temp[col] = "ALL"

        if level in ["citywide", "department", "division", "category"]:
            temp["NEIGHBORHOOD"] = "CITYWIDE"

        temp["LEVEL"] = level
        rows.append(temp)

    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(OUTPUT / "monthly_volume_full.parquet", index=False)



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

    # Global 95% cap
    cap = df2["RESOLUTION_TIME_DAYS"].quantile(0.95)
    df2["RESOLUTION"] = df2["RESOLUTION_TIME_DAYS"].clip(upper=cap)

    # Drop last 2 months (incomplete)
    latest = df2["ds"].max()
    last_kept = (latest.to_period("M") - 2).to_timestamp("M")
    df2 = df2[df2["ds"] <= last_kept].copy()


    # Fill missing resolution by CASE TYPE median
    medians = df2.groupby("CASE TYPE")["RESOLUTION"].median()
    df2["RESOLUTION"] = df2.apply(
        lambda r: medians.get(r["CASE TYPE"])
        if pd.isna(r["RESOLUTION"]) else r["RESOLUTION"],
        axis=1
    )

    # Drop remaining NaNs
    df2 = df2.dropna(subset=["RESOLUTION"])

    # AGGREGATIONS

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
    
    # NEIGHBORHOOD × DEPARTMENT
    neigh_dept = (
        df2.groupby(["ds", "NEIGHBORHOOD", "DEPARTMENT"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    neigh_dept.to_parquet(
        OUTPUT / "monthly_severity_neighborhood_department.parquet",
        index=False
    )

    # NEIGHBORHOOD × DIVISION
    neigh_div = (
        df2.groupby(["ds", "NEIGHBORHOOD", "DIVISION"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    neigh_div.to_parquet(
        OUTPUT / "monthly_severity_neighborhood_division.parquet",
        index=False
    )
    
    # NEIGHBORHOOD × CATEGORY
    neigh_cat = (
        df2.groupby(["ds", "NEIGHBORHOOD", "CATEGORY"])["RESOLUTION"]
        .mean()
        .reset_index(name="Severity")
    )
    neigh_cat.to_parquet(
        OUTPUT / "monthly_severity_neighborhood_category.parquet",
        index=False
    )


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
