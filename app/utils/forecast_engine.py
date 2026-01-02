import pandas as pd
from prophet import Prophet
from app.utils.data_loader import df

# CONFIG
FORECAST_CONFIG = {
    "volume": {
        "min_months": 12,
        "max_mape": 50,
        "horizon_months": 12,
        "trend_window": 3,
    },
    "severity": {
        "min_months": 6,
        "max_mape": 70,
        "horizon_months": 6,
        "trend_window": 2,
    },
}

BASE = "precomputed_data/forecast/"

# Helper: ensure ds is datetime
def _ensure_month_end(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ds" in df.columns:
        df["ds"] = pd.to_datetime(df["ds"])
    return df

def _norm_str(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.replace("\u00a0", " ", regex=False)
         .str.replace(r"\s+", " ", regex=True)
         .str.strip()
    )


# VOLUME INPUTS
VOLUME_FULL = pd.read_parquet(BASE + "monthly_volume_full.parquet")

# Add normalized helper columns (only once, cheap)
for col in ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY"]:
    if col in VOLUME_FULL.columns:
        VOLUME_FULL[col + "_CLEAN"] = _norm_str(VOLUME_FULL[col]).str.title()

# SEVERITY INPUTS (preloaded once)
SEV_CITY = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_citywide.parquet")
)

SEV_NEIGH = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_neighborhood.parquet")
)

SEV_DEPT = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_department.parquet")
)

SEV_DIV = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_division.parquet")
)

SEV_CAT = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_category.parquet")
)

SEV_NEIGH_DEPT = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_neighborhood_department.parquet")
)
SEV_NEIGH_DIV = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_neighborhood_division.parquet")
)
SEV_NEIGH_CAT = _ensure_month_end(
    pd.read_parquet(BASE + "monthly_severity_neighborhood_category.parquet")
)

def _add_clean_cols(sev: pd.DataFrame) -> pd.DataFrame:
    sev = sev.copy()
    for col in ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY"]:
        if col in sev.columns:
            sev[col + "_CLEAN"] = _norm_str(sev[col]).str.title()
    return sev

SEV_CITY = _add_clean_cols(SEV_CITY)
SEV_NEIGH = _add_clean_cols(SEV_NEIGH)
SEV_DEPT = _add_clean_cols(SEV_DEPT)
SEV_DIV  = _add_clean_cols(SEV_DIV)
SEV_CAT  = _add_clean_cols(SEV_CAT)

SEV_NEIGH_DEPT = _add_clean_cols(SEV_NEIGH_DEPT)
SEV_NEIGH_DIV  = _add_clean_cols(SEV_NEIGH_DIV)
SEV_NEIGH_CAT  = _add_clean_cols(SEV_NEIGH_CAT)

SEVERITY_MAP = {
    "citywide": SEV_CITY,
    "neighborhood": SEV_NEIGH,
    "department": SEV_DEPT,
    "division": SEV_DIV,
    "category": SEV_CAT,
    "neighborhood_department": SEV_NEIGH_DEPT,
    "neighborhood_division": SEV_NEIGH_DIV,
    "neighborhood_category": SEV_NEIGH_CAT,
}

# HELPERS
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

def month_closure_rate(df, month_end):
    """
    month_end: a Timestamp like 2025-09-30 (end-of-month date)
    Returns float in [0,1] or None if no cases exist.
    """
    start = month_end.replace(day=1)
    end = month_end

    subset = df[(df["CREATED DATE"] >= start) & (df["CREATED DATE"] <= end)]

    if subset.empty:
        return None

    closed = subset["CLOSED DATE"].notna().sum()
    total = len(subset)

    return closed / total

def compute_recent_mape(merged, years=3):
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


def compute_forecast(ts, config, horizon=None):
    horizon = horizon or config["horizon_months"]
    min_months = config.get("min_months", 12)
    max_mape = config.get("max_mape", 50)
    trend_window = config.get("trend_window", 3)

    ts = ts.sort_values("ds")

    # Not enough data
    if len(ts) < min_months or ts["y"].nunique() < 2:
        ts = ts.copy()
        ts["yhat"] = ts["y"]
        ts["yhat_lower"] = ts["y"]
        ts["yhat_upper"] = ts["y"]
        ts["Rolling_Trend"] = rolling_trend(ts["y"], window=trend_window)
        ts["Rolling_%_Change"] = ts["y"].pct_change().fillna(0) * 100
        fc = ts.copy()
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

    # Rolling trend + % change on combined series
    merged["Rolling_Trend"] = rolling_trend(
        merged["y"].fillna(merged["yhat"]),
        window=trend_window,
    )
    merged["Rolling_%_Change"] = (
        merged["y"].fillna(merged["yhat"]).pct_change().fillna(0) * 100
    )

    # Recent MAPE
    valid = merged.dropna(subset=["y", "yhat"])
    valid = valid[valid["y"] > 0]
    if len(valid) > 0:
        mape = compute_recent_mape(merged, years=3)
    else:
        mape = None

    reliable = classify_reliability(mape, max_mape)

    # Split into hist vs future
    last_actual = ts["ds"].max()
    hist = merged[merged["ds"] <= last_actual].copy()
    fc_only = merged[merged["ds"] > last_actual].copy()

    return hist, fc_only, reliable, mape


# PUBLIC API: VOLUME FORECAST
def get_forecast(neigh, item, level, config, horizon=None):
    """
    Volume forecasts based only on monthly_volume_full parquet.
    Returns (hist, forecast_only, reliability_text, mape)
    """
    
    empty_cols = [
        "ds", "y", "yhat", "yhat_lower",
        "yhat_upper", "Rolling_Trend", "Rolling_%_Change"
    ]
    empty = pd.DataFrame(columns=empty_cols)

    level_col = {
        "category": "CATEGORY",
        "department": "DEPARTMENT",
        "division": "DIVISION",
    }.get(level.lower(), "CATEGORY")

    dff = VOLUME_FULL.copy()
    
    # Determine correct LEVEL (matches monthly_volume_full.parquet LEVEL values)
    if neigh == "CITYWIDE" and item == "ALL":
        level_key = "citywide"

    elif neigh == "CITYWIDE" and item != "ALL":
        # CITYWIDE item-level (requires precompute LEVEL = "department"/"division"/"category")
        level_key = level.lower()   # "department" / "division" / "category"

    elif neigh != "CITYWIDE" and item == "ALL":
        level_key = "neighborhood"

    elif neigh != "CITYWIDE" and item != "ALL":
        # Neighborhood item-level
        level_key = f"neighborhood_{level.lower()}"  # "neighborhood_department"/...

    else:
        return empty, empty, "Unreliable", None

    dff = VOLUME_FULL[VOLUME_FULL["LEVEL"] == level_key].copy()

    # Neighborhood filter
    if neigh != "CITYWIDE":
        neigh_clean = _norm_str(pd.Series([neigh])).iloc[0].title()
        dff = dff[dff["NEIGHBORHOOD_CLEAN"] == neigh_clean]

    if item != "ALL":
        item_clean = _norm_str(pd.Series([item])).iloc[0].title()
        dff = dff[dff[level_col + "_CLEAN"] == item_clean]
        
    print("DEBUG level_key:", level_key)
    print("DEBUG neigh:", neigh, "item:", item, "level_col:", level_col)
    print("DEBUG rows after filters:", len(dff))
    if len(dff) == 0:
        print("DEBUG unique departments (sample):", VOLUME_FULL["DEPARTMENT"].dropna().head(10).tolist())


    if dff.empty:
        # Return empty structures with same columns expected downstream
        empty_cols = ["ds", "y", "yhat", "yhat_lower", "yhat_upper", "Rolling_Trend", "Rolling_%_Change"]
        empty_hist = pd.DataFrame(columns=empty_cols)
        empty_fc = pd.DataFrame(columns=empty_cols)
        return empty_hist, empty_fc, "Unreliable", None

    # Aggregate to a single y series per month
    ts = (
        dff
        .groupby("ds")["Count"]
        .sum()
        .reset_index()
        .rename(columns={"Count": "y"})
        .sort_values("ds")
    )

    # Ensure continuous months (missing months → 0 complaints)
    full_range = pd.date_range(ts["ds"].min(), ts["ds"].max(), freq="ME")
    ts = (
        ts.set_index("ds")
        .reindex(full_range, fill_value=0)
        .rename_axis("ds")
        .reset_index()
    )

    hist, fc_only, reliable, mape = compute_forecast(ts, config, horizon=horizon)

    return hist, fc_only, reliable, mape


def get_severity_forecast(neigh, item, level, config, horizon=None):
    """
    Simple, stable severity forecast.

    - Uses precomputed monthly severity tables (no parquet reads per call)
    - No regressors
    - Horizon starts at the current calendar month
    - "ALL" items forecast is ALWAYS based on citywide severity,
      regardless of level or neighborhood selection
    - Incomplete months trimmed using closure completeness
    """

    # Helpers
    def _norm(series: pd.Series) -> pd.Series:
        return (
            series.astype(str)
            .str.replace("\u00a0", " ")
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.title()
        )

    level_base = level.lower()

    if neigh != "CITYWIDE" and item != "ALL":
        level_key = f"neighborhood_{level_base}"
    else:
        level_key = level_base

    filter_col = level_base.upper()


    if level_key not in SEVERITY_MAP:
        # Failsafe
        cols = ["ds", "y", "yhat", "yhat_lower", "yhat_upper",
                "Rolling_Trend", "Rolling_%_Change"]
        empty = pd.DataFrame(columns=cols)
        return empty, empty.copy(), "Unreliable", None

    # Base severity table for this level
    severity = SEVERITY_MAP[level_key].copy()

    # Normalize user choices
    neigh_clean = _norm_str(pd.Series([neigh])).iloc[0].title()
    item_clean = None if item == "ALL" else _norm_str(pd.Series([item])).iloc[0].title()

    # ALL items: always use CITYWIDE series (fully consistent)
    if item == "ALL":
        severity = SEV_CITY[["ds", "Severity"]].copy()
        # We also ignore neighborhood for ALL-items forecast.
    else:
        # Neighborhood filter
        if neigh != "CITYWIDE" and "NEIGHBORHOOD_CLEAN" in severity.columns:
            severity = severity[severity["NEIGHBORHOOD_CLEAN"] == neigh_clean]

        # Item filter (department / division / category)
        if item != "ALL":
            item_col = filter_col + "_CLEAN"   # e.g. DEPARTMENT_CLEAN
            if item_col in severity.columns:
                severity = severity[severity[item_col] == item_clean]
                
    print("SEV DEBUG rows:", len(severity))
    print("SEV DEBUG cols:", severity.columns.tolist())

    # Empty? → bail out cleanly
    if severity.empty:
        cols = ["ds", "y", "yhat", "yhat_lower", "yhat_upper",
                "Rolling_Trend", "Rolling_%_Change"]
        empty = pd.DataFrame(columns=cols)
        return empty, empty.copy(), "Unreliable", None

    # Build continuous monthly time series
    ts = severity[["ds", "Severity"]].rename(columns={"Severity": "y"}).sort_values("ds")

    full_range = pd.date_range(ts["ds"].min(), ts["ds"].max(), freq="ME")
    ts = (
        ts.set_index("ds")
          .reindex(full_range)
          .rename_axis("ds")
          .reset_index()
    )
    ts["y"] = ts["y"].interpolate().bfill().ffill()

    # Remove incomplete last months via closure completeness
    if len(severity) >= 2:
        original_months = severity["ds"].sort_values().unique()
        last_month = original_months[-1]
        second_last_month = original_months[-2]

        df_subset = df.copy()

        # Only filter df_subset when we're forecasting a specific thing (not ALL)
        if item != "ALL":
            # Neighborhood filter
            if neigh != "CITYWIDE" and "NEIGHBORHOOD" in df_subset.columns:
                df_subset = df_subset[_norm_str(df_subset["NEIGHBORHOOD"]).str.title() == neigh_clean]

            # Item filter (DEPARTMENT / DIVISION / CATEGORY)
            if filter_col in df_subset.columns and item_clean is not None:
                df_subset = df_subset[_norm_str(df_subset[filter_col]).str.title() == item_clean]

        rate = month_closure_rate(df_subset, second_last_month)

        if rate is not None and rate >= 0.90:
            ts = ts[ts["ds"] < last_month]
        else:
            ts = ts[ts["ds"] < second_last_month]
            
    print("SEV DEBUG level_key:", level_key)
    print("SEV DEBUG neigh_clean:", neigh_clean, "item_clean:", item_clean)
    print("SEV DEBUG rows:", len(severity))

    if len(severity) == 0:
        print("SEV DEBUG sample neighborhoods:", severity.columns.tolist())
        base_df = SEVERITY_MAP[level_key]
        if "NEIGHBORHOOD_CLEAN" in base_df.columns:
            print("SEV DEBUG neigh unique sample:", base_df["NEIGHBORHOOD_CLEAN"].dropna().unique()[:10])
        item_col = filter_col + "_CLEAN"
        if item_col in base_df.columns:
            print("SEV DEBUG item unique sample:", base_df[item_col].dropna().unique()[:10])


    # Fallback if not enough history
    if len(ts) < config["min_months"]:
        ts["yhat"] = ts["y"]
        ts["yhat_lower"] = ts["y"]
        ts["yhat_upper"] = ts["y"]
        ts["Rolling_Trend"] = rolling_trend(ts["y"], window=config["trend_window"])
        ts["Rolling_%_Change"] = ts["y"].pct_change().fillna(0) * 100
        return ts, ts.copy(), "Unreliable", None

    # Fit Prophet (no regressors)
    model = Prophet(yearly_seasonality=True)
    model.fit(ts)

    # Forecast starting at CURRENT MONTH
    horizon = horizon or config["horizon_months"]
    today_month = pd.Timestamp.today().to_period("M").to_timestamp()

    future = model.make_future_dataframe(periods=horizon, freq="ME")
    fc = model.predict(future)

    merged = pd.merge(
        fc[["ds", "yhat", "yhat_lower", "yhat_upper"]],
        ts[["ds", "y"]],
        on="ds",
        how="left",
    )

    base = merged["y"].fillna(merged["yhat"])
    merged["Rolling_Trend"] = rolling_trend(base, window=config["trend_window"])
    merged["Rolling_%_Change"] = base.pct_change().fillna(0) * 100

    # Historical part = everything up to last observed month
    hist_cutoff = ts["ds"].max()
    hist = merged[merged["ds"] <= hist_cutoff]

    # Future part = from current calendar month onward
    future_df = merged[merged["ds"] >= today_month].copy()
    future_df = future_df.head(horizon)

    # If Prophet didn't give enough rows, extend flat
    if len(future_df) < horizon:
        missing = horizon - len(future_df)
        last_row = future_df.iloc[-1] if not future_df.empty else None

        extra_months = pd.date_range(
            start=future_df["ds"].max() + pd.offsets.MonthEnd(1)
            if not future_df.empty else today_month,
            periods=missing,
            freq="ME",
        )

        for m in extra_months:
            future_df.loc[len(future_df)] = {
                "ds": m,
                "yhat": last_row["yhat"] if last_row is not None else ts["y"].iloc[-1],
                "yhat_lower": last_row["yhat_lower"] if last_row is not None else ts["y"].iloc[-1],
                "yhat_upper": last_row["yhat_upper"] if last_row is not None else ts["y"].iloc[-1],
                "Rolling_Trend": last_row["Rolling_Trend"] if last_row is not None else ts["y"].iloc[-1],
                "Rolling_%_Change": 0,
            }

    # Reliability via recent MAPE
    mape = compute_recent_mape(merged)
    reliability = classify_reliability(mape, config["max_mape"])

    return hist, future_df, reliability, mape