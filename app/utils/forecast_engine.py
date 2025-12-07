import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error
from app.utils.data_loader import df

df_local = df.copy()

df_local["year_month"] = df_local["CREATED DATE"].dt.to_period("M")

monthly_counts_citywide = (
    df_local.groupby("year_month")
            .size()
            .reset_index(name="total_y")
)

VALID_CITYWIDE_MONTHS = set(
    monthly_counts_citywide.loc[
        monthly_counts_citywide["total_y"] >= 1000, 
        "year_month"
    ].tolist()
)

# Constants
FORECAST_CONFIG = {
    "volume": {
        "min_months": 12,
        "max_mape": 50,
        "horizon_months": 12,
        "trend_window": 3
    },

    "severity": {
        "min_months": 6,
        "max_mape": 70,
        "horizon_months": 6,
        "trend_window": 2
    }
}

# Helper Functions
def new_prophet():
    return Prophet(interval_width=0.95, yearly_seasonality=True)

def rolling_trend(series, window=3):
    return series.rolling(window=window, min_periods=1, center=True).mean()

def classify_reliability(mape, max_mape):
    if mape is None:
        return "Unreliable"
    if mape <= 0.6 * max_mape:
        return "Reliable"
    if mape <= max_mape:
        return "Possibly Unreliable"
    return "Unreliable"

def compute_recent_mape(merged, years=3):
    """
    Compute MAPE on the last N years of overlapping y & yhat data.
    """
    if merged.empty or "y" not in merged or "yhat" not in merged:
        return None

    cutoff = merged["ds"].max() - pd.DateOffset(years=years)

    recent = merged[merged["ds"] >= cutoff].copy()
    recent = recent.dropna(subset=["y", "yhat"])
    recent = recent[recent["y"] > 0]

    if len(recent) == 0:
        return None

    mape = (abs(recent["y"] - recent["yhat"]) / recent["y"]).mean() * 100
    return mape

# Forecast Functions
def compute_forecast(ts, config, horizon=None):
    horizon = horizon or config["horizon_months"]
    min_months = config.get("min_months", 12)
    max_mape = config.get("max_mape", 50)
    trend_window = config.get("trend_window", 3)

    ts = ts.sort_values("ds")

    # Drop last incomplete month
    if len(ts) > 0:
        last_month = ts["ds"].max()
        ts = ts[ts["ds"] < last_month]

    # Not enough data
    if len(ts) < min_months or ts["y"].nunique() < 2:
        ts = ts.copy()
        ts["yhat"] = ts["y"]
        ts["yhat_lower"] = ts["y"]
        ts["yhat_upper"] = ts["y"]
        ts["Rolling_Trend"] = rolling_trend(ts["y"], window=trend_window)
        ts["Rolling_%_Change"] = ts["y"].pct_change().fillna(0) * 100
        fc = ts.copy()  # return a forecast dataframe with the same structure
        reliable = "Unreliable"
        mape = None
        return ts, fc, reliable, mape

    # Fit Prophet
    model = new_prophet()
    model.fit(ts)

    # Forecast
    future = model.make_future_dataframe(periods=horizon, freq="ME")
    fc = model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    # Merge historical + predictions
    merged = pd.merge(ts, fc, on="ds", how="outer").sort_values("ds")

    # Unified Rolling Trend and % Change
    merged["Rolling_Trend"] = rolling_trend(
        merged["y"].fillna(merged["yhat"]),  # fallback to forecast for future rows
        window=trend_window
    )

    merged["Rolling_%_Change"] = (
        merged["y"].fillna(merged["yhat"]).pct_change().fillna(0) * 100
    )

    # Historical MAPE
    valid = merged.dropna(subset=["y", "yhat"])
    valid = valid[valid["y"] > 0]

    if len(valid) > 0:
        mape = compute_recent_mape(merged, years=3)
    else:
        mape = None
        
    reliable = classify_reliability(mape, max_mape)

    # Monthly bias (error pattern)
    merged["error"] = merged["y"] - merged["yhat"]
    merged["month"] = merged["ds"].dt.month

    hist = merged[merged["y"].notna()].copy()
    fc_only = merged[merged["y"].isna()].copy()

    return hist, fc_only, reliable, mape


def get_forecast(neigh, item, level, config, horizon=None):

    local = df.copy()

    # Column mapping
    level_col = {
        "category": "CATEGORY",
        "department": "DEPARTMENT",
        "division": "DIVISION"
    }.get(level.lower(), "CATEGORY")

    # CITYWIDE uses month filter — neighborhoods should NOT
    if neigh == "CITYWIDE":
        df_filtered = local[local["CREATED DATE"].dt.to_period("M").isin(VALID_CITYWIDE_MONTHS)]
        ts = df_filtered.copy()
    else:
        ts = local[local["NEIGHBORHOOD"].str.strip() == neigh.strip()].copy()

    # Apply item filter
    if item != "ALL":
        ts = ts[ts[level_col].astype(str).str.strip() == str(item).strip()]

    # Monthly aggregation
    ts_grouped = (
        ts.groupby(pd.Grouper(key="CREATED DATE", freq="ME"))
          .size()
          .reset_index(name="y")
          .rename(columns={"CREATED DATE": "ds"})
    )

    if ts_grouped.empty:
        return (
            pd.DataFrame(columns=["ds","y","yhat","yhat_lower","yhat_upper","Rolling_Trend","Rolling_%_Change"]),
            pd.DataFrame(),
            "Unreliable",
            None
        )

    # Fix month range (ensure continuous months)
    full_range = pd.date_range(ts_grouped["ds"].min(), ts_grouped["ds"].max(), freq="ME")
    ts_grouped = (
        ts_grouped.set_index("ds")
                  .reindex(full_range)
                  .rename_axis("ds")
                  .reset_index()
                  .sort_values("ds") 
    )
    ts_grouped["y"] = ts_grouped["y"].interpolate().bfill().ffill()

    # Call forecast engine
    hist, fc, reliable, mape = compute_forecast(ts_grouped, config, horizon=horizon)

    reliability_text = classify_reliability(mape, config["max_mape"])

    return hist, fc, reliability_text, mape

def get_severity_forecast(neigh, item, level, config, horizon=None):
    local = df.copy()

    # Column mapping
    level_col = {
        "category": "CATEGORY",
        "department": "DEPARTMENT",
        "division": "DIVISION"
    }.get(level.lower(), "CATEGORY")

    # Cap extreme severity outliers
    cap = local["RESOLUTION_TIME_DAYS"].quantile(0.95)
    local["RESOLUTION_TIME_DAYS"] = local["RESOLUTION_TIME_DAYS"].clip(upper=cap)

    # Remove last 2 months for modeling stability
    latest_date = local["CREATED DATE"].max()
    latest_month_start = latest_date.replace(day=1)
    cutoff = latest_month_start - pd.DateOffset(months=1)
    ts = local[local["CREATED DATE"] < cutoff].copy()

    # Apply neighborhood & item filters
    if neigh != "CITYWIDE":
        ts = ts[ts["NEIGHBORHOOD"] == neigh]

    if item != "ALL":
        ts = ts[ts[level_col].astype(str).str.strip() == str(item).strip()]

    if ts.empty:
        return None, None, "No data after filtering", None

    # Impute missing severity by case-type median
    medians_by_type = ts.groupby("CASE TYPE")["RESOLUTION_TIME_DAYS"].median()
    ts["RESOLUTION_TIME_DAYS"] = ts.apply(
        lambda r: medians_by_type[r["CASE TYPE"]] if pd.isna(r["RESOLUTION_TIME_DAYS"]) else r["RESOLUTION_TIME_DAYS"],
        axis=1
    )

    # Monthly severity aggregation
    ts_grouped = (
        ts.groupby(pd.Grouper(key="CREATED DATE", freq="ME"))["RESOLUTION_TIME_DAYS"]
        .mean()
        .reset_index()
        .rename(columns={"CREATED DATE": "ds", "RESOLUTION_TIME_DAYS": "y"})
    )

    # Monthly regressors
    monthly_volume = (
        ts.groupby(pd.Grouper(key="CREATED DATE", freq="ME"))
          .size()
          .reset_index(name="case_volume")
          .rename(columns={"CREATED DATE": "ds"})
    )

    # Case-type dominance regressor
    ct_monthly = (
        ts.groupby([pd.Grouper(key="CREATED DATE", freq="ME"), "CASE TYPE"])
        .size()
        .reset_index(name="count")
    )
    totals = ct_monthly.groupby("CREATED DATE")["count"].sum()
    ct_monthly["prop"] = ct_monthly.apply(
        lambda r: r["count"] / totals[r["CREATED DATE"]],
        axis=1
    )

    dominant_prop = (
        ct_monthly.sort_values(["CREATED DATE", "prop"], ascending=[True, False])
        .groupby("CREATED DATE").first()[["prop"]]
        .reset_index()
        .rename(columns={"CREATED DATE": "ds", "prop": "dominant_case_prop"})
    )

    # Merge regressors
    ts_grouped = (
        ts_grouped
        .merge(monthly_volume, on="ds", how="left")
        .merge(dominant_prop, on="ds", how="left")
    )

    # Build full timeline and interpolate missing
    full_range = pd.date_range(ts_grouped["ds"].min(), ts_grouped["ds"].max(), freq="ME")
    ts_grouped = ts_grouped.set_index("ds").reindex(full_range).rename_axis("ds").reset_index()
    for col in ["y", "case_volume", "dominant_case_prop"]:
        ts_grouped[col] = ts_grouped[col].interpolate().bfill().ffill()

    # Train full model on history
    model = Prophet(yearly_seasonality=True, changepoint_prior_scale=0.8)
    model.add_regressor("case_volume")
    model.add_regressor("dominant_case_prop")
    model.fit(ts_grouped)

    # Build future dataframe
    horizon = horizon or config.get("horizon_months", 12)
    future = model.make_future_dataframe(periods=horizon, freq="ME")
    future = future.merge(ts_grouped[["ds", "case_volume", "dominant_case_prop"]], on="ds", how="left")

    # FFill regressor values for future months
    future["case_volume"] = future["case_volume"].ffill()
    future["dominant_case_prop"] = future["dominant_case_prop"].ffill()

    # Predict
    forecast = model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    # Merge real history + predictions
    merged = pd.merge(ts_grouped, forecast, on="ds", how="outer").sort_values("ds")

    # Compute MAPE only on last 3 years of overlap
    recent_cutoff = merged["ds"].max() - pd.DateOffset(years=3)
    valid = merged[(merged["ds"] >= recent_cutoff) & merged["y"].notna() & merged["yhat"].notna() & (merged["y"] > 0)]

    mape = None if valid.empty else (abs(valid["y"] - valid["yhat"]) / valid["y"]).mean() * 100
    reliability = classify_reliability(mape, config["max_mape"])

    # Rolling metrics (needed for dashboard table)
    trend_window = config["trend_window"]
    merged["Rolling_Trend"] = rolling_trend(
        merged["y"].fillna(merged["yhat"]), 
        window=trend_window
    )
    merged["Rolling_%_Change"] = merged["y"].fillna(merged["yhat"]).pct_change() * 100

    # Split into: history vs future (MUST MATCH volume forecast behavior)
    last_actual = ts_grouped["ds"].max()

    hist = merged[merged["ds"] <= last_actual].copy()
    fc_only = merged[merged["ds"] > last_actual].copy()

    return hist, fc_only, reliability, mape