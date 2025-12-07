from dash import html, dcc, register_page, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from app.utils.data_loader import df
from app.utils.utils import make_table, empty_figure
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
    
    dbc.Row(
        dbc.Col([
            dbc.Label("Forecast Horizon (Months):", className="text-white"),
            dcc.Slider(
                id="forecast-horizon",
                min=3,
                max=18,
                step=3,
                value=12,   # default
                marks={i: str(i) for i in range(3, 19, 3)}
            )
        ], width=6),
        justify="center",
        className="mb-4"
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

    level_col = {
        "category": "CATEGORY",
        "department": "DEPARTMENT",
        "division": "DIVISION"
    }.get(forecast_level.lower(), "CATEGORY")

    # Normalize neighborhoods
    if not selected_neighs:
        selected_neighs = ["CITYWIDE"]
    elif isinstance(selected_neighs, str):
        selected_neighs = [selected_neighs]

    # Collect items
    items = set()

    for neigh in selected_neighs:
        df_sub = df if neigh == "CITYWIDE" else df[df["NEIGHBORHOOD"].str.strip() == neigh.strip()]
        items.update(df_sub[level_col].dropna().astype(str).str.strip().unique())
        
    if not items:
        return [{"label": "No items available", "value": "EMPTY"}], "EMPTY"

    # ALWAYS return something valid
    options = [{"label": "All Items", "value": "ALL"}] + [
        {"label": item, "value": item} for item in sorted(items)
    ]


    return options, "ALL"

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
    Input("forecast-type", "value"),
    Input("forecast-horizon", "value")
)
def update_forecasts(selected_neighs, forecast_level, selected_item, forecast_type, horizon):

    # Subtitle
    subtitle = f"Forecasting {forecast_level.title()} {forecast_type.title()} Trends"

    # Normalize neighborhoods
    if not selected_neighs:
        selected_neighs = ["CITYWIDE"]
    elif isinstance(selected_neighs, str):
        selected_neighs = [selected_neighs]

    selected_items = [selected_item] if selected_item != "ALL" else ["ALL"]
    
    if selected_item == "EMPTY":
        return (
            empty_figure("No items available for this selection"),
            html.Div(),
            "No items available for this selection.",
            True,
            "warning",
            subtitle
        )

    fig = go.Figure()
    all_forecasts = []
    reliability_msgs = []

    config = FORECAST_CONFIG[forecast_type]
    get_func = get_severity_forecast if forecast_type == "severity" else get_forecast

    # MAIN LOOP
    for neigh in selected_neighs:
        for item in selected_items:

            try:
                ts, forecast, reliable, mape = get_func(
                    neigh, item, forecast_level, config, horizon=horizon
                )
            except Exception as e:
                reliability_msgs.append(f"{neigh}/{item}: Forecast engine failed")
                continue

            # If engine returns nothing
            if ts is None or forecast is None or forecast.empty:
                reliability_msgs.append(f"{neigh}/{item}: No forecast available")
                continue

            # MAPE label
            if mape is None or not isinstance(mape, (int, float)) or np.isnan(mape):
                msg_mape = "MAPE: N/A"
            else:
                msg_mape = f"MAPE: {mape:.2f}%"

            reliability_msgs.append(f"{neigh}/{item}: {reliable} ({msg_mape})")

            # Determine forecast_future depending on forecast type
            forecast_future = forecast.copy()

            # Safety: if nothing left, skip
            if forecast_future.empty:
                reliability_msgs.append(f"{neigh}/{item}: No future forecast rows")
                continue

            # Limit to horizon
            if horizon and horizon > 0:
                forecast_future = forecast_future.head(horizon)

            if forecast_future.empty:
                reliability_msgs.append(f"{neigh}/{item}: No future rows")
                continue

            # Styles
            line_styles = {
                "Reliable": dict(width=3, dash="solid"),
                "Possibly Unreliable": dict(width=3, dash="dash"),
                "Unreliable": dict(width=3, dash="dot", color="lightgray")
            }
            line_style = line_styles.get(reliable, dict(width=3, dash="solid"))

            # Observed
            fig.add_trace(go.Scatter(
                x=ts["ds"],
                y=ts["y"],
                mode="lines+markers",
                name=f"Observed ({neigh}/{item})"
            ))

            # Forecast line
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"],
                y=forecast_future["yhat"],
                mode="lines",
                name=f"Forecast ({neigh}/{item})",
                line=line_style
            ))

            # Confidence band
            fig.add_trace(go.Scatter(
                x=pd.concat([forecast_future["ds"], forecast_future["ds"][::-1]]),
                y=pd.concat([forecast_future["yhat_upper"], forecast_future["yhat_lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(0,123,255,0.15)",
                showlegend=False
            ))

            # Rolling Trend
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"],
                y=forecast_future["Rolling_Trend"],
                mode="lines",
                name=f"Rolling Trend ({neigh}/{item})",
                line=dict(dash="dot", width=2, color="orange")
            ))

            # Build table
            disp = forecast_future.copy()
            disp["Month"] = disp["ds"].dt.strftime("%B %Y")
            disp["Month_dt"] = disp["ds"]
            disp["Neighborhood"] = neigh
            disp["Item"] = item

            if forecast_type == "severity":
                disp["Predicted Severity"] = disp["yhat"].round(1)
                disp["Rolling Trend"] = disp["Rolling_Trend"].round(1)
                disp["Rolling % Change"] = disp["Rolling_%_Change"].round(1).astype(str) + "%"
            else:
                disp["Predicted Complaints"] = disp["yhat"].round(0).astype(int)
                disp["Rolling Trend"] = disp["Rolling_Trend"].round(0).astype(int)
                disp["Rolling % Change"] = disp["Rolling_%_Change"].round(1).astype(str) + "%"

            all_forecasts.append(disp)

    # NO FORECASTS?
    if not all_forecasts:
        return (
            empty_figure("No forecast data available for this selection"),
            dbc.Alert("No forecast rows available.", color="warning"),
            "No forecast rows available.",
            True,
            "warning",
            subtitle
        )

    # BUILD TABLE
    display_table = pd.concat(all_forecasts, ignore_index=True)
    display_table = display_table.sort_values(by=["Month_dt", "Neighborhood"])

    if forecast_type == "severity":
        columns = ["Month", "Neighborhood", "Item", "Predicted Severity", "Rolling Trend", "Rolling % Change"]
    else:
        columns = ["Month", "Neighborhood", "Item", "Predicted Complaints", "Rolling Trend", "Rolling % Change"]

    display_table = display_table[columns]
    display_table = display_table.rename(columns={"Item": forecast_level.title()})

    table_component = dbc.Card(
        dbc.CardBody(
            html.Div(
                make_table(display_table),
                style={"maxHeight": "410px", "overflowY": "auto"}
            )
        ),
        className="bg-dark border-dark mb-4"
    )

    # CHART STYLE
    fig.update_layout(
        title=f"{forecast_type.title()} Forecast (Next {horizon} Months)",
        yaxis_title="Complaints" if forecast_type == "volume" else "Severity",
        plot_bgcolor="#140327",
        paper_bgcolor="#140327",
        font_color="white"
    )

    # ALERT MESSAGE
    alert_text = "\n".join(reliability_msgs)
    show_alert = True
    alert_color = (
        "danger" if "Unreliable" in alert_text else
        "warning" if "Possibly" in alert_text else
        "info"
    )

    return fig, table_component, alert_text, show_alert, alert_color, subtitle