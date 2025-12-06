from threading import Lock, Thread
import pandas as pd

forecast_lock = Lock()
forecast_ready = False
forecast_df = None

def build_master_volume_forecast():
    from app.utils.forecast_engine import get_forecast, FORECAST_CONFIG  # existing forecast function and config for volume forecasts
    # Compute CITYWIDE / ALL volume forecast once and store it.
    global forecast_df, forecast_ready
    with forecast_lock:
        forecast_ready = False
        try:
            # Run get_forecast for CITYWIDE volume
            _, fc, _, _ = get_forecast("CITYWIDE", "ALL", "category", FORECAST_CONFIG["volume"])
            forecast_df = fc[["ds", "yhat"]].copy()
            forecast_ready = True
        except Exception as e:
            print("Error building master volume forecast:", e)
            forecast_df = None
            forecast_ready = False

def start_forecast_thread():
    # Run forecast in background.
    thread = Thread(target=build_master_volume_forecast, daemon=True)
    thread.start()

def get_home_forecast_summary():
    # Return text summary for homepage.
    global forecast_df, forecast_ready
    if not forecast_ready or forecast_df is None:
        return "Forecasts loading..."

    now = pd.Timestamp.now()
    current_row = forecast_df[(forecast_df["ds"].dt.month == now.month) &
                              (forecast_df["ds"].dt.year == now.year)]

    if current_row.empty:
        return "No forecast available for current month."

    value = current_row["yhat"].values[0]
    return f"{value:,.0f}"
