import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error
from app.utils.data_loader import df

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
    return Prophet(interval_width=0.95, daily_seasonality=True, mcmc_samples=0)


def rolling_trend(series, window=3):
    return series.rolling(window=window, min_periods=1, center=True).mean()

# Forecast Functions
def compute_forecast(ts, config):
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
        reliable = False
        mape = None
        return ts, fc, reliable, mape

    # Fit Prophet
    model = new_prophet()
    model.fit(ts)

    # Forecast
    horizon = config.get("horizon_months", 12)
    future = model.make_future_dataframe(periods=horizon, freq="ME")
    fc = model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    # Merge historical + predictions
    merged = ts.merge(fc, on="ds", how="left")

    # Historical MAPE
    valid = merged.dropna(subset=["y", "yhat"])
    valid = valid[valid["y"] > 0]

    if len(valid) > 0:
        mape = (abs(valid["y"] - valid["yhat"]) / valid["y"]).mean() * 100
        reliable = mape <= max_mape
    else:
        mape = None
        reliable = False

    # Monthly bias (error pattern)
    merged["error"] = merged["y"] - merged["yhat"]
    merged["month"] = merged["ds"].dt.month

    # Rolling trend + % change
    fc["Rolling_Trend"] = rolling_trend(fc["yhat"], window=trend_window)
    ts["Rolling_%_Change"] = ts["y"].pct_change().fillna(0) * 100
    fc["Rolling_%_Change"] = fc["yhat"].pct_change().fillna(0) * 100

    return ts, fc, reliable, mape


def get_forecast(neigh, item, level, config):

    # Column mapping
    level_col = {
        "category": "CATEGORY",
        "department": "DEPARTMENT",
        "division": "DIVISION"
    }.get(level.lower(), "CATEGORY")

    # Compute citywide monthly counts
    monthly_counts = (
        df.assign(year_month=df["CREATED DATE"].dt.to_period("M"))
        .groupby("year_month")
        .size()
        .reset_index(name="total_y")
    )

    # Keep months with at least 1000 reports
    valid_months = monthly_counts[monthly_counts["total_y"] >= 1000]["year_month"]

    # Filter original df
    df_filtered = df[df["CREATED DATE"].dt.to_period("M").isin(valid_months)]

    # Apply neighborhood filter
    ts = df_filtered.copy() if neigh == "CITYWIDE" else df_filtered[df_filtered["NEIGHBORHOOD"] == neigh]

    # Item filter
    if item != "ALL":
        ts = ts[ts[level_col].astype(str).str.strip() == str(item).strip()]

    # Monthly aggregation
    ts_grouped = (
        ts.groupby(pd.Grouper(key="CREATED DATE", freq="ME"))
          .size()
          .reset_index(name="y")
          .rename(columns={"CREATED DATE": "ds"})
    )

    # If no data → bail
    if ts_grouped.empty:
        ts_empty = pd.DataFrame(columns=["ds","y","yhat","yhat_lower","yhat_upper","Rolling_Trend","Rolling_%_Change"])
        fc_empty = ts_empty.copy()
        reliable = False
        mape = None
        return ts_empty, fc_empty, reliable, mape

    # Uniform month range (no missing months)
    full_range = pd.date_range(ts_grouped["ds"].min(), ts_grouped["ds"].max(), freq="ME")
    ts_grouped = (
        ts_grouped.set_index("ds")
                  .reindex(full_range)
                  .rename_axis("ds")
                  .reset_index()
    )
    ts_grouped["y"] = ts_grouped["y"].interpolate().bfill().ffill()

    # Call the forecasting engine
    hist, fc, reliable, mape = compute_forecast(ts_grouped, config)

    reliability_text = (
        "Reliable" if reliable else
        "Possibly Unreliable" if mape is not None and mape <= config["max_mape"] else
        "Unreliable"
    )

    return hist, fc, reliability_text, mape


def get_severity_forecast(neigh, item, level, config):
    # Column mapping
    level_col = {"category": "CATEGORY", "department": "DEPARTMENT", "division": "DIVISION"}.get(level.lower(), "CATEGORY")

    # Cap extreme resolution times
    cap = df["RESOLUTION_TIME_DAYS"].quantile(0.95)
    df["RESOLUTION_TIME_DAYS"] = df["RESOLUTION_TIME_DAYS"].clip(upper=cap)

    # Remove last 2 months for modeling
    latest_date = df["CREATED DATE"].max()
    latest_month_start = latest_date.replace(day=1)
    second_latest_month_start = latest_month_start - pd.DateOffset(months=1)
    ts = df[df["CREATED DATE"] < second_latest_month_start].copy()

    # Neighborhood and item filtering
    ts = ts if neigh == "CITYWIDE" else ts[ts["NEIGHBORHOOD"] == neigh]
    if item != "ALL":
        ts = ts[ts[level_col].astype(str).str.strip() == str(item).strip()]
        print(f"Filtered rows for {neigh}/{item}: {len(ts)}")

    if ts.empty:
        return None, None, "No data after filtering", None

    # Impute missing RESOLUTION_TIME_DAYS by case-type median
    medians_by_type = ts.groupby('CASE TYPE')['RESOLUTION_TIME_DAYS'].median()
    ts['RESOLUTION_TIME_DAYS'] = ts.apply(
        lambda row: medians_by_type[row['CASE TYPE']]
                    if pd.isna(row['RESOLUTION_TIME_DAYS']) and row['CASE TYPE'] in medians_by_type
                    else row['RESOLUTION_TIME_DAYS'],
        axis=1
    )
    ts = ts.dropna(subset=['RESOLUTION_TIME_DAYS'])

    # Monthly aggregation
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

    case_type_monthly = (
        ts.groupby([pd.Grouper(key="CREATED DATE", freq="ME"), "CASE TYPE"])
          .size()
          .reset_index(name="count")
    )
    month_totals = case_type_monthly.groupby("CREATED DATE")["count"].sum()
    case_type_monthly["prop"] = case_type_monthly.apply(
        lambda row: row["count"] / month_totals[row["CREATED DATE"]], axis=1
    )

    dominant_prop = (
        case_type_monthly.sort_values(["CREATED DATE", "prop"], ascending=[True, False])
        .groupby("CREATED DATE")
        .first()
        .reset_index()[["CREATED DATE", "prop"]]
        .rename(columns={"CREATED DATE": "ds", "prop": "dominant_case_prop"})
    )

    # Merge regressors
    ts_grouped = ts_grouped.merge(monthly_volume, on="ds", how="left")
    ts_grouped = ts_grouped.merge(dominant_prop, on="ds", how="left")

    # Interpolate missing months
    full_range = pd.date_range(ts_grouped["ds"].min(), ts_grouped["ds"].max(), freq="ME")
    ts_grouped = ts_grouped.set_index("ds").reindex(full_range).rename_axis("ds").reset_index()
    for col in ["y", "case_volume", "dominant_case_prop"]:
        ts_grouped[col] = ts_grouped[col].interpolate().bfill().ffill()

    # Train/test split
    ts_train = ts_grouped[ts_grouped["ds"] < pd.Timestamp("2025-11-01")]
    ts_train = ts_train[ts_train["ds"] >= pd.Timestamp("2022-01-01")]

    ts_test = ts_train.iloc[-6:] if len(ts_train) > 6 else pd.DataFrame(columns=ts_train.columns)

    # Prophet model with regressors
    model = Prophet(yearly_seasonality=True, changepoint_prior_scale=0.8)
    model.add_regressor("case_volume")
    model.add_regressor("dominant_case_prop")
    model.fit(ts_train)

    # Future dataframe
    future_horizon = config.get("horizon_months", 12)
    future = model.make_future_dataframe(periods=future_horizon, freq="ME")
    future = future.merge(ts_grouped[["ds", "case_volume", "dominant_case_prop"]], on="ds", how="left")
    future["case_volume"] = future["case_volume"].ffill()
    future["dominant_case_prop"] = future["dominant_case_prop"].ffill()

    # Forecast
    forecast = model.predict(future)
    forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    # Compute MAPE on test set
    if not ts_test.empty:
        pred = forecast.merge(ts_test[["ds", "y"]], on="ds", how="inner")
        mape = mean_absolute_percentage_error(pred["y"], pred["yhat"]) * 100 if not pred.empty else None
    else:
        mape = None

    reliability = (
        "Reliable" if mape is not None and mape <= config["max_mape"] * 0.6 else
        "Possibly Unreliable" if mape is not None and mape <= config["max_mape"] else
        "Unreliable"
    )

    # Rolling trend and percent change
    trend_window = config.get("trend_window", 3)
    forecast["Rolling_Trend"] = rolling_trend(forecast["yhat"], window=trend_window)
    ts_grouped["Rolling_%_Change"] = ts_grouped["y"].pct_change().fillna(0) * 100
    forecast["Rolling_%_Change"] = forecast["yhat"].pct_change().fillna(0) * 100

    return ts_grouped, forecast, reliability, mape