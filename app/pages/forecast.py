from dash import html, dcc, register_page, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from app.utils.data_loader import df
from app.utils.utils import make_table
from app.utils.forecast_engine import *

register_page(__name__, path="/forecasts", title="Forecasts")

# Layout
layout = dbc.Container([
    html.H2("Complaint Forecasts (Prophet Model)", className="text-center text-primary mt-4 mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.RadioItems(
                id="forecast-level",
                options=[
                    {"label": "Department", "value": "department"},
                    {"label": "Division", "value": "division"},
                    {"label": "Category", "value": "category"},
                ],
                value="department",
                inline=True,
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary",
                labelCheckedClassName="btn btn-primary"
            ),
            width="auto"
        )
    ], justify="center", className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Select Neighborhood(s):", className="text-white"),
            dcc.Dropdown(
                id="neighborhood-select",
                options=[{"label": n, "value": n} for n in sorted(df["NEIGHBORHOOD"].dropna().unique())],
                value=[],
                multi=True,
                clearable=True,
                placeholder="Select neighborhood(s)",
                style={
                    "width": "100%",
                    "backgroundColor": "#361566",
                    "color": "white",
                    "border": "none",
                    "boxShadow": "none"
                }
            ),
        ], width=4),
        dbc.Col([
            dbc.Label("Select Item:", className="text-white"),
            dbc.Select(id="item-select", options=[{"label": "All Items", "value": "ALL"}], value="ALL")
        ], width=4),
    ], justify="center", className="mb-3"),

    dbc.Row(
        [
            dbc.Col(
                dbc.RadioItems(
                    id="forecast-type",
                    options=[
                        {"label": "Complaint Volume", "value": "volume"},
                        {"label": "Severity", "value": "severity"}
                    ],
                    value="volume",
                    inline=True,
                    inputClassName="btn-check",
                    labelClassName="btn btn-outline-info",
                    labelCheckedClassName="btn btn-info"
                ),
                width="auto",
                className="text-center"
            )
        ],
        justify="center",
        className="my-4"
    ),

    html.H5(
        id="forecast-subtitle",
        className="text-center text-white mb-2"
    ),

    # Graph
    dbc.Card(
        dbc.CardBody(
            dbc.Spinner(
                dcc.Graph(
                    id="forecast-graph",
                    figure={},
                    style={"height": "500px"}
                ),
                size="lg",
                color="primary",
                type="grow", 
                fullscreen=False 
            )
        ),
        className="bg-dark border-dark mb-4"
    ),

    html.H5("Monthly Complaint Predictions & Bias", className="text-center text-white mb-4"),

    # Table
    dbc.Row(
        dbc.Col(
            dbc.Spinner(
                html.Div(id="forecast-table-container"),
                size="lg",
                color="primary",
                type="grow"
            ),
            width=10
        ),
        justify="center",
        className="mb-4"
    ),

    dbc.Alert(id="forecast-alert", is_open=False, className="mb-4",
              style={"textAlign": "center", "fontWeight": "bold", "fontSize": "18px", "borderRadius": "12px",
                     "margin": "auto", "width": "50%"}),

    dbc.Row([dbc.Col(dbc.Button("🏠 Home", href="/", color="primary"), width="auto")], justify="center"),
])


# Callbacks
@callback(
    Output("item-select", "options"),
    Output("item-select", "value"),
    Input("neighborhood-select", "value"),
    Input("forecast-level", "value")
)
def update_items_dropdown(selected_neighs, forecast_level):
    level_col = {"category": "CATEGORY", "department": "DEPARTMENT", "division": "DIVISION"}.get(forecast_level.lower(),
                                                                                                 "CATEGORY")
    if not selected_neighs:
        selected_neighs = ["CITYWIDE"]
    elif isinstance(selected_neighs, str):
        selected_neighs = [selected_neighs]

    items = set()
    for neigh in selected_neighs:
        df_sub = df if neigh == "CITYWIDE" else df[df["NEIGHBORHOOD"] == neigh]
        items.update(df_sub[level_col].dropna().unique())

    options = [{"label": "All Items", "value": "ALL"}] + [{"label": str(i), "value": str(i)} for i in sorted(items)]
    value = "ALL"  # reset to ALL whenever level changes
    return options, value

@callback(
    Output("forecast-graph", "figure"),
    Output("forecast-table-container", "children"),
    Output("forecast-alert", "children"),
    Output("forecast-alert", "is_open"),
    Output("forecast-alert", "color"),
    Output("forecast-subtitle", "children"),
    Input("neighborhood-select", "value"),
    Input("forecast-level", "value"),
    Input("item-select", "value"),
    Input("forecast-type", "value")
)
def update_forecasts(selected_neighs, forecast_level, selected_item, forecast_type):
    if not selected_neighs:
        selected_neighs = ["CITYWIDE"]
    elif isinstance(selected_neighs, str):
        selected_neighs = [selected_neighs]

    selected_items = [selected_item] if selected_item != "ALL" else ["ALL"]
    all_forecasts = []
    fig = go.Figure()
    reliability_msgs = []
    not_enough_data = False
    config = FORECAST_CONFIG[forecast_type]
    get_func = get_severity_forecast if forecast_type == "severity" else get_forecast

    for neigh in selected_neighs:
        for item in selected_items:
            ts, forecast, reliable, mape = get_func(neigh, item, forecast_level, config)

            if ts is None or forecast is None:
                not_enough_data = True
                reliability_msgs.append(f"{neigh}/{item}: Not enough data to generate forecast")
                break

            # Mark reliability but don't skip plotting — show users the result with a warning
            if mape is None or np.isnan(mape):
                msg_mape = "MAPE: N/A"
            else:
                msg_mape = f"MAPE: {mape:.2f}%"

            reliability_msgs.append(f"{neigh}/{item}: {reliable} ({msg_mape})")

            last_actual = ts["ds"].max()
            forecast_future = forecast[forecast["ds"] > last_actual].copy()
            if forecast_future.empty:
                forecast_future = forecast.tail(12).copy()

            line_styles = {
                "Reliable": dict(width=3, dash="solid"),
                "Possibly Unreliable": dict(width=3, dash="dash"),
                "Unreliable": dict(width=3, dash="dot", color="lightgray")
            }
            line_style = line_styles.get(reliable, dict(width=3, dash="solid"))

            # Graph traces
            fig.add_trace(go.Scatter(
                x=ts["ds"],
                y=ts["y"],
                mode="lines+markers",
                name=f"Observed ({neigh}/{item})")
            )
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"], y=forecast_future["yhat"],
                mode="lines",
                name=f"Forecast ({neigh}/{item})",
                line=line_style)
            )
            fig.add_trace(go.Scatter(
                x=pd.concat([forecast_future["ds"], forecast_future["ds"][::-1]]),
                y=pd.concat([forecast_future["yhat_upper"], forecast_future["yhat_lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(0,123,255,0.15)",
                line=dict(width=0),
                showlegend=False)
            )
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"],
                y=forecast_future["Rolling_Trend"],
                mode="lines",
                name=f"Rolling Trend ({neigh}/{item})",
                line=dict(dash="dot", width=2, color="orange"))
            )

            # Table display fields depend on forecast_type
            forecast_disp = forecast_future.copy()
            forecast_disp["Month"] = forecast_disp["ds"].dt.strftime("%B %Y")
            forecast_disp["Month_dt"] = forecast_disp["ds"]
            forecast_disp["Neighborhood"] = neigh
            forecast_disp["Item"] = item

            if forecast_type == "severity":
                forecast_disp["Predicted Severity"] = forecast_disp["yhat"].round(1)
                forecast_disp["Rolling Trend"] = forecast_disp["Rolling_Trend"].round(1)
                if "Rolling_%_Change" not in forecast_disp.columns:
                    forecast_disp["Rolling_%_Change"] = 0
                forecast_disp["Rolling % Change"] = forecast_disp["Rolling_%_Change"].round(1).astype(str) + "%"
            else:
                forecast_disp["Predicted Complaints"] = forecast_disp["yhat"].round(0).astype(int)
                forecast_disp["Rolling Trend"] = forecast_disp["Rolling_Trend"].round(0).astype(int)
                if "Rolling_%_Change" not in forecast_disp.columns:
                    forecast_disp["Rolling_%_Change"] = 0
                forecast_disp["Rolling % Change"] = forecast_disp["Rolling_%_Change"].round(1).astype(str) + "%"

            all_forecasts.append(forecast_disp)

    if not_enough_data:
        # Skip graph and table, show only alert
        table_component = None
        fig = go.Figure()  # empty figure
        alert_text = "Not enough data to generate forecast."
        show_alert = True
        alert_color = "danger"
    else:
        # Table component
        if all_forecasts:
            display_table = pd.concat(all_forecasts, ignore_index=True)
            display_table = display_table.sort_values(by=["Month_dt", "Neighborhood"])

            # Select columns
            if forecast_type == "severity":
                columns = ["Month", "Neighborhood", "Item", "Predicted Severity", "Rolling Trend", "Rolling % Change"]
            else:
                columns = ["Month", "Neighborhood", "Item", "Predicted Complaints", "Rolling Trend", "Rolling % Change"]
            display_table = display_table[columns]

            # Rename columns for display
            col_rename = {"Item": forecast_level.title()}
            display_table = display_table.rename(columns=col_rename)

            # Scrollable card
            table_component = dbc.Card(
                dbc.CardBody(
                    html.Div(
                        make_table(display_table),
                        style={
                            "maxHeight": "410px",
                            "overflowY": "auto",
                            "overflowX": "auto",
                        }
                    )
                ),
                className="bg-dark border-dark mb-4"
            )
        else:
            table_component = dbc.Alert("No reliable forecast data available for the selected options.", color="warning")

        fig.update_layout(
            title="Severity Forecast (Next 12 Months)" if forecast_type == "severity"
            else "Complaint Volume Forecast (Next 12 Months)",
            yaxis_title="Average Severity" if forecast_type == "severity" else "Complaints",
            plot_bgcolor="#140327",
            paper_bgcolor="#140327",
            font_color="white"
        )

        # Alert with reliability messages
        alert_text = "\n".join(reliability_msgs)
        show_alert = bool(alert_text)

        if any(msg.split(":")[1].strip().startswith("Unreliable") for msg in reliability_msgs):
            alert_color = "danger"
        elif any(msg.split(":")[1].strip().startswith("Possibly Unreliable") for msg in reliability_msgs):
            alert_color = "warning"
        else:
            alert_color = "info"

    subtitle = f"Forecasting {forecast_level.title()} {forecast_type.title()} Trends"

    return fig, table_component, alert_text, show_alert, alert_color, subtitle