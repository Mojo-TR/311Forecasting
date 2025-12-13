import pandas as pd
from pathlib import Path
from app.utils.data_loader import df

OUTPUT = Path("precomputed_data/resolution")
OUTPUT.mkdir(parents=True, exist_ok=True)


# BASE CLEANING
def prepare_base(df_in):
    df2 = df_in.copy()

    df2["MonthName"] = df2["CREATED DATE"].dt.month_name()
    df2["YearMonth"] = df2["CREATED DATE"].dt.to_period("M")

    # Clean neighborhoods
    df2 = df2.dropna(subset=["NEIGHBORHOOD"])
    df2 = df2[df2["NEIGHBORHOOD"].str.strip() != ""]
    df2 = df2[df2["NEIGHBORHOOD"] != "None"]

    return df2


# PER-MONTH PER-NEIGHBORHOOD STATS
def compute_resolution_stats(df2):
    stats = (
        df2.groupby(["NEIGHBORHOOD", "MonthName"])["RESOLUTION_TIME_DAYS"]
        .agg(["mean", "median", "max", "count"])
        .reset_index()
        .rename(columns={
            "mean": "Avg_Resolution",
            "median": "Median_Resolution",
            "max": "Max_Resolution",
            "count": "Volume"
        })
    )
    stats.to_parquet(OUTPUT / "resolution_stats.parquet", index=False)


# ALL-MONTH AGGREGATE STATS (important!)
def compute_resolution_stats_all_months(df2):
    all_months = (
        df2.groupby("NEIGHBORHOOD")["RESOLUTION_TIME_DAYS"]
        .agg(["mean", "median", "max", "count"])
        .reset_index()
        .rename(columns={
            "mean": "Avg_Resolution",
            "median": "Median_Resolution",
            "max": "Max_Resolution",
            "count": "Volume"
        })
        .sort_values("Avg_Resolution")
    )
    all_months.to_parquet(OUTPUT / "resolution_stats_all_months.parquet", index=False)


# CITYWIDE KPI VALUES (per month + overall)

def compute_citywide_kpis(df2):
    monthly = (
        df2.groupby("MonthName")["RESOLUTION_TIME_DAYS"]
        .agg(["mean", "median"])
        .reset_index()
        .rename(columns={"mean": "Avg_Resolution", "median": "Median_Resolution"})
    )

    # Add ALL MONTHS row
    all_row = pd.DataFrame([{
        "MonthName": "all",
        "Avg_Resolution": df2["RESOLUTION_TIME_DAYS"].mean(),
        "Median_Resolution": df2["RESOLUTION_TIME_DAYS"].median()
    }])

    out = pd.concat([monthly, all_row], ignore_index=True)
    out.to_parquet(OUTPUT / "resolution_citywide.parquet", index=False)


# FASTEST & SLOWEST NEIGHBORHOODS (per month + overall)
def compute_fastest_slowest(df2):
    rows = []

    for m in df2["MonthName"].unique():
        subset = df2[df2["MonthName"] == m]
        if subset.empty:
            continue

        agg = (
            subset.groupby("NEIGHBORHOOD")["RESOLUTION_TIME_DAYS"]
            .mean()
            .reset_index(name="Avg_Resolution")
        )

        fastest = agg.nsmallest(1, "Avg_Resolution").iloc[0]
        slowest = agg.nlargest(1, "Avg_Resolution").iloc[0]

        rows.append({
            "MonthName": m,
            "Fastest": fastest["NEIGHBORHOOD"],
            "FastestValue": fastest["Avg_Resolution"],
            "Slowest": slowest["NEIGHBORHOOD"],
            "SlowestValue": slowest["Avg_Resolution"],
        })

    # ALL MONTHS
    all_agg = (
        df2.groupby("NEIGHBORHOOD")["RESOLUTION_TIME_DAYS"]
        .mean()
        .reset_index(name="Avg_Resolution")
    )

    fast_all = all_agg.nsmallest(1, "Avg_Resolution").iloc[0]
    slow_all = all_agg.nlargest(1, "Avg_Resolution").iloc[0]

    rows.append({
        "MonthName": "all",
        "Fastest": fast_all["NEIGHBORHOOD"],
        "FastestValue": fast_all["Avg_Resolution"],
        "Slowest": slow_all["NEIGHBORHOOD"],
        "SlowestValue": slow_all["Avg_Resolution"],
    })

    pd.DataFrame(rows).to_parquet(OUTPUT / "fastest_slowest.parquet", index=False)


# SLA BUCKETS + HEATMAP MATRIX

def compute_sla_buckets_and_heatmap(df2):
    df2 = df2.copy()
    df2["MonthName"] = df2["CREATED DATE"].dt.month_name()

    df2["WithinSLA"] = df2["RESOLUTION_TIME_DAYS"] <= 3

    sla_matrix = (
        df2.groupby(["NEIGHBORHOOD", "MonthName"])["WithinSLA"]
        .mean()
        .reset_index()
        .pivot(index="NEIGHBORHOOD", columns="MonthName", values="WithinSLA")
        * 100
    )

    sla_matrix = sla_matrix.fillna(0)
    sla_matrix.to_parquet(OUTPUT / "sla_heatmap_matrix.parquet")


# RESOLUTION TREND OVER TIME

def compute_resolution_trend(df2):
    trend = (
        df2.groupby("YearMonth")["RESOLUTION_TIME_DAYS"]
        .mean()
        .reset_index()
    )
    trend["Month"] = trend["YearMonth"].dt.to_timestamp()
    trend.to_parquet(OUTPUT / "trend.parquet", index=False)


# LIST FILES
def compute_lists(df2):
    months = sorted(df2["MonthName"].dropna().unique())
    neigh = sorted(df2["NEIGHBORHOOD"].dropna().unique())

    pd.DataFrame({"MonthName": months}).to_parquet(OUTPUT / "months.parquet", index=False)
    pd.DataFrame({"NEIGHBORHOOD": neigh}).to_parquet(OUTPUT / "neighborhoods.parquet", index=False)


# MAIN

def run_precompute_resolution():
    print("🔧 Precomputing: Resolution Insights…")

    df2 = prepare_base(df)

    compute_lists(df2)
    compute_resolution_stats(df2)
    compute_resolution_stats_all_months(df2)
    compute_citywide_kpis(df2)
    compute_fastest_slowest(df2)
    compute_sla_buckets_and_heatmap(df2)
    compute_resolution_trend(df2)

    print("✅ Completed: Resolution Insights Precompute")


if __name__ == "__main__":
    run_precompute_resolution()
