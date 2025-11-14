import pandas as pd
from prophet import Prophet
from threading import Thread, Lock
from .data_loader import df
import datetime as dt

forecast_df = None
forecast_ready = False
forecast_lock = Lock()

def make_forecast(df, column="CREATED DATE", periods=90):
    model_df = df.groupby(pd.to_datetime(df[column]).dt.to_period("M")).size().reset_index(name="y")
    model_df["ds"] = model_df[column].dt.to_timestamp()

    model = Prophet()
    model.fit(model_df)

    future = model.make_future_dataframe(periods=periods, freq="M")
    forecast = model.predict(future)
    return forecast[["ds", "yhat"]]

def run_forecasts():
    global forecast_df, forecast_ready
    with forecast_lock:
        forecast_ready = False
        try:
            forecast_df = make_forecast(df)
            forecast_ready = True
        except Exception as e:
            print(f"Forecasting error: {e}")
            forecast_df = None
            forecast_ready = False

def start_forecast_thread():
    thread = Thread(target=run_forecasts, daemon=True)
    thread.start()

def get_home_forecast_summary():
    """Return text summary for homepage."""
    if not forecast_ready or forecast_df is None:
        return "Forecasts loading..."

    now = dt.datetime.now()
    current_month = now.month
    current_year = now.year

    # Find forecast row matching this month
    mask = (
        (forecast_df["ds"].dt.month == current_month) &
        (forecast_df["ds"].dt.year == current_year)
    )

    current_row = forecast_df.loc[mask]

    if current_row.empty:
        return "No forecast available for current month."

    value = current_row["yhat"].values[0]
    month_name = now.strftime("%B")
    return f"Expected total for {month_name} {current_year}: {value:.0f} requests"
