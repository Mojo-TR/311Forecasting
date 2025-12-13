import pandas as pd
from pathlib import Path
from app.utils.data_loader import df

OUTPUT = Path("precomputed_data/summary")
OUTPUT.mkdir(parents=True, exist_ok=True)


# BASE PREP

def prepare_base(df_in):
    df2 = df_in.copy()

    df2["MonthName"] = df2["CREATED DATE"].dt.month_name()
    df2["YearMonth"] = df2["CREATED DATE"].dt.to_period("M")

    # SLA DAYS (80th percentile rule)
    valid = df2.dropna(subset=["CATEGORY", "RESOLUTION_TIME_DAYS"])
    sla_by_cat = (
        valid.groupby("CATEGORY")["RESOLUTION_TIME_DAYS"]
        .quantile(0.80)
        .round(1)
        .to_dict()
    )
    df2["SLA_DAYS"] = df2["CATEGORY"].map(sla_by_cat)

    return df2


# KPI MONTHLY + "ALL"

def compute_kpi_monthly(df2):

    def calc_kpis(dff):
        total = len(dff)
        median_res = dff["RESOLUTION_TIME_DAYS"].median()

        # SLA %
        sla_df = dff.dropna(subset=["SLA_DAYS", "RESOLUTION_TIME_DAYS"])
        if sla_df.empty:
            sla_pct = None
        else:
            sla_pct = (sla_df["RESOLUTION_TIME_DAYS"] <= sla_df["SLA_DAYS"]).mean() * 100

        months_present = dff["YearMonth"].nunique()
        avg_month = total / months_present if months_present > 0 else None

        return total, median_res, sla_pct, avg_month

    rows = []

    for month in sorted(df2["MonthName"].unique()):
        subset = df2[df2["MonthName"] == month]
        total, med, sla, avg = calc_kpis(subset)
        rows.append({
            "MonthName": month,
            "Total": total,
            "MedianRes": med,
            "SLA_Rate": sla,
            "AvgPerMonth": avg
        })

    # ALL MONTHS ROW
    total, med, sla, avg = calc_kpis(df2)
    rows.append({
        "MonthName": "all",
        "Total": total,
        "MedianRes": med,
        "SLA_Rate": sla,
        "AvgPerMonth": avg
    })

    out = pd.DataFrame(rows)
    out.to_parquet(OUTPUT / "kpi_monthly.parquet", index=False)


# SLOWEST GROUPS + GLOBAL “ALL MONTHS” ROLLUP

def compute_slowest(df2):

    groups = ["DEPARTMENT", "CATEGORY", "NEIGHBORHOOD"]

    for col in groups:
        # per-month
        monthly = (
            df2.dropna(subset=[col, "RESOLUTION_TIME_DAYS"])
            .groupby([col, "MonthName"])
            .agg(
                MedianDays=("RESOLUTION_TIME_DAYS", "median"),
                CaseCount=("RESOLUTION_TIME_DAYS", "count")
            )
            .reset_index()
        )

        # all-months
        all_months = (
            df2.dropna(subset=[col, "RESOLUTION_TIME_DAYS"])
            .groupby(col)
            .agg(
                MedianDays=("RESOLUTION_TIME_DAYS", "median"),
                CaseCount=("RESOLUTION_TIME_DAYS", "count")
            )
            .reset_index()
        )
        all_months["MonthName"] = "all"

        out = pd.concat([monthly, all_months], ignore_index=True)
        out.to_parquet(OUTPUT / f"slowest_{col.lower()}.parquet", index=False)


# SLA RISK GROUPS + ALL MONTHS

def compute_sla_risk(df2):

    df_sla = df2.dropna(subset=["SLA_DAYS", "RESOLUTION_TIME_DAYS"]).copy()
    df_sla["WITHIN_SLA"] = df_sla["RESOLUTION_TIME_DAYS"] <= df_sla["SLA_DAYS"]

    groups = ["DEPARTMENT", "CATEGORY", "NEIGHBORHOOD"]

    for col in groups:
        monthly = (
            df_sla.dropna(subset=[col])
            .groupby([col, "MonthName"])
            .agg(
                CaseCount=("WITHIN_SLA", "size"),
                SLA_Percent=("WITHIN_SLA", lambda x: x.mean() * 100)
            )
            .reset_index()
        )

        all_months = (
            df_sla.dropna(subset=[col])
            .groupby(col)
            .agg(
                CaseCount=("WITHIN_SLA", "size"),
                SLA_Percent=("WITHIN_SLA", lambda x: x.mean() * 100)
            )
            .reset_index()
        )
        all_months["MonthName"] = "all"

        out = pd.concat([monthly, all_months], ignore_index=True)
        out.to_parquet(OUTPUT / f"sla_risk_{col.lower()}.parquet", index=False)


# VOLUME COUNTS + ALL MONTHS

def compute_volume_counts(df2):

    frames = []

    for col in ["CATEGORY", "DEPARTMENT", "NEIGHBORHOOD"]:
        monthly = (
            df2.dropna(subset=[col])
            .groupby([col, "MonthName"])
            .size()
            .reset_index(name="Count")
        )
        monthly["GroupColumn"] = col
        monthly.rename(columns={col: "GroupValue"}, inplace=True)

        # all months
        overall = (
            df2.dropna(subset=[col])
            .groupby(col)
            .size()
            .reset_index(name="Count")
        )
        overall["GroupColumn"] = col
        overall["MonthName"] = "all"
        overall.rename(columns={col: "GroupValue"}, inplace=True)

        frames.append(pd.concat([monthly, overall], ignore_index=True))

    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(OUTPUT / "volume_counts.parquet", index=False)


# MONTHLY VOLUME TREND (LAST 12 MONTHS ONLY)

def compute_monthly_trend(df2):

    trend = (
        df2.groupby("YearMonth")
        .size()
        .reset_index(name="Count")
        .sort_values("YearMonth")
    )

    trend["YearMonth"] = trend["YearMonth"].astype(str)
    trend_last12 = trend.tail(12)

    trend_last12.to_parquet(OUTPUT / "volume_monthly.parquet", index=False)


# CATEGORY → CASE TYPES

def compute_category_case_types(df2):

    mapping = (
        df2.dropna(subset=["CATEGORY", "CASE TYPE"])
        .groupby("CATEGORY")["CASE TYPE"]
        .apply(lambda s: sorted(s.unique()))
        .reset_index(name="CaseTypes")
    )

    mapping.to_parquet(OUTPUT / "category_case_types.parquet", index=False)


# MASTER RUNNER

def run_precompute_summary():
    print("🔧 Precomputing Summary Page...")

    df2 = prepare_base(df)

    compute_kpi_monthly(df2)
    compute_slowest(df2)
    compute_sla_risk(df2)
    compute_volume_counts(df2)
    compute_monthly_trend(df2)
    compute_category_case_types(df2)

    print("✅ Summary Page Precompute Complete!")


if __name__ == "__main__":
    run_precompute_summary()