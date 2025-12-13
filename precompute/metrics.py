import pandas as pd
from pathlib import Path
from app.utils.data_loader import df

OUTPUT = Path("precomputed_data/metrics")
OUTPUT.mkdir(parents=True, exist_ok=True)


def prepare_base(df_in):
    df2 = df_in.copy()
    df2["MonthName"] = df2["CREATED DATE"].dt.month_name()

    # Clean neighborhoods
    df2 = df2.dropna(subset=["NEIGHBORHOOD"])
    df2 = df2[df2["NEIGHBORHOOD"].str.strip() != ""]
    df2 = df2[df2["NEIGHBORHOOD"] != "None"]

    return df2

def compute_all_months_groupings():
    print("📦 Computing ALL-month grouped tables...")

    metrics = ["category", "department", "division"]

    for metric in metrics:
        file_path = OUTPUT / f"by_{metric}_neigh.parquet"
        df_metric = pd.read_parquet(file_path)

        # Collapse across all months → total count per neighborhood/metric
        out = (
            df_metric.groupby(["NEIGHBORHOOD", metric.upper()])
            .agg({"Count": "sum"})
            .reset_index()
        )

        out.sort_values("Count", ascending=False).to_parquet(
            OUTPUT / f"by_{metric}_neigh_allmonths.parquet",
            index=False
        )

def compute_neighborhood_list(df_in):
    neigh = df_in["NEIGHBORHOOD"].dropna().unique()

    pd.DataFrame({"NEIGHBORHOOD": sorted(neigh)}).to_parquet(
        OUTPUT / "neighborhood_list.parquet",
        index=False
    )


def compute_metric_groupings(df_in):
    metrics = ["CATEGORY", "DEPARTMENT", "DIVISION"]

    for metric in metrics:
        out = (
            df_in.groupby([metric, "NEIGHBORHOOD", "MonthName"])
            .size()
            .reset_index(name="Count")
        )
        out.to_parquet(OUTPUT / f"by_{metric.lower()}_neigh.parquet", index=False)

        totals = (
            df_in.groupby(metric)
            .size()
            .reset_index(name="Count")
        )
        totals.to_parquet(OUTPUT / f"by_{metric.lower()}.parquet", index=False)


def compute_totals(df_in):
    totals = (
        df_in.groupby("NEIGHBORHOOD")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    totals.to_parquet(OUTPUT / "neighborhood_totals.parquet", index=False)


def compute_month_filter(df_in):
    months = df_in["MonthName"].dropna().unique()

    pd.DataFrame({"MonthName": sorted(months)}).to_parquet(
        OUTPUT / "month_list.parquet",
        index=False
    )


def run_precompute_neighborhood_metrics():
    print("🔧 Precomputing: Neighborhood Metrics...")

    df2 = prepare_base(df)

    compute_neighborhood_list(df2)
    compute_month_filter(df2)
    compute_metric_groupings(df2)
    compute_all_months_groupings() 
    compute_totals(df2)

    print("✅ Precompute Complete: Neighborhood Metrics")


if __name__ == "__main__":
    run_precompute_neighborhood_metrics()