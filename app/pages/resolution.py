from dash import html, dcc, register_page, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.utils.utils import make_table, empty_figure, empty_table

register_page(__name__, path="/resolution-insights", title="Resolution Insights")
                
# LOAD PRECOMPUTED DATA
BASE = "precomputed_data/resolution/"

RES_ALL = pd.read_parquet(BASE + "resolution_stats_all_months.parquet")
RES_MONTHLY = pd.read_parquet(BASE + "resolution_stats.parquet")
CITY = pd.read_parquet(BASE + "resolution_citywide.parquet")
FAST_SLOW = pd.read_parquet(BASE + "fastest_slowest.parquet")
HEATMAP = pd.read_parquet(BASE + "sla_heatmap_matrix.parquet")
TREND = pd.read_parquet(BASE + "trend.parquet")

MONTHS = pd.read_parquet(BASE + "months.parquet").iloc[:, 0].tolist()
NEIGH_LIST = pd.read_parquet(BASE + "neighborhoods.parquet").iloc[:, 0].tolist()

month_options = [{"label": "All Months", "value": "all"}] + [
    {"label": m, "value": m} for m in MONTHS
]

def make_kpi(title, value, color="primary"):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.H5(title, className="text-white"),
                html.H3(value, className=f"text-{color}")
            ]),
            className="bg-dark border-dark"
        ),
        width=3
    )


# PAGE LAYOUT
layout = dbc.Container([

    html.H2("Resolution Time Insights", className="text-center text-primary mt-4 mb-4"),

    # Month filter
    dbc.Row([
        dbc.Col([
            html.Label("Select Month:", className="text-white mb-2"),
            dbc.Select(id="resolution-month", options=month_options, value="all")
        ], width="auto")
    ], justify="center", className="mb-4"),

    # KPI Row
    dbc.Row(id="resolution-kpi-row", className="mb-4"),
    
    dbc.Spinner(
        children=html.Div([

            # Ranking Table
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Neighborhood Resolution Ranking", className="text-white"),
                            html.Div(
                                id="resolution-table",
                                style={
                                    "maxHeight": "500px",
                                    "overflowY": "auto",
                                    "paddingRight": "10px"
                                }
                            )
                        ]),
                        className="bg-dark border-dark"
                    )
                )
            ], className="mb-4"),

            # SLA Heatmap
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("SLA Performance Heatmap", className="text-white"),
                            html.Div(
                                dcc.Graph(id="resolution-sla-heatmap", style={"height": "600px"}),
                                style={
                                    "maxHeight": "500px",
                                    "overflowY": "auto",
                                    "paddingRight": "10px"
                                }
                            )
                        ]),
                        className="bg-dark border-dark"
                    )
                )
            ], className="mb-4"),

            # Trend Over Time
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Resolution Trend Over Time", className="text-white"),
                            dcc.Graph(id="resolution-trend")
                        ]),
                        className="bg-dark border-dark"
                    )
                )
            ], className="mb-4"),

            # Volume vs Resolution Scatter
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("Volume vs Average Resolution Time", className="text-white"),
                            dcc.Graph(id="resolution-scatter")
                        ]),
                        className="bg-dark border-dark"
                    )
                )
            ], className="mb-4"),

        ]),

        color="primary",
        type="grow",
        fullscreen=True,
        fullscreen_style={"backgroundColor": "rgba(0, 0, 0, 0)"}
    ),
    
    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
    ], style={"textAlign": "center"})

], fluid=True)

@callback(
    Output("resolution-kpi-row", "children"),
    Output("resolution-table", "children"),
    Output("resolution-sla-heatmap", "figure"),
    Output("resolution-trend", "figure"),
    Output("resolution-scatter", "figure"),
    Input("resolution-month", "value")
)
def update_resolution_page(selected_month):

    if selected_month == "all":
        dff = RES_ALL
        city_vals = CITY[CITY["MonthName"] == "all"].iloc[0]
        fs = FAST_SLOW[FAST_SLOW["MonthName"] == "all"].iloc[0]
    else:
        dff = RES_MONTHLY[RES_MONTHLY["MonthName"] == selected_month]
        city_vals = CITY[CITY["MonthName"] == selected_month].iloc[0]
        fs = FAST_SLOW[FAST_SLOW["MonthName"] == selected_month].iloc[0]

    kpis = [
        make_kpi("Avg Resolution (Citywide)", f"{city_vals['Avg_Resolution']:.0f} days"),
        make_kpi("Median Resolution (Citywide)", f"{city_vals['Median_Resolution']:.0f} days"),
        make_kpi("Fastest Neighborhood",
                 f"{fs['Fastest']} — {fs['FastestValue']:.0f} days",
                 color="success"),
        make_kpi("Slowest Neighborhood",
                 f"{fs['Slowest']} — {fs['SlowestValue']:.0f} days",
                 color="danger"),
    ]

    # Ranking table
    table_html = make_table(dff.sort_values("Avg_Resolution"))

    # SLA Heatmap (month-order enforced)
    sla_fig = px.imshow(
        HEATMAP[MONTHS],
        aspect="auto",
        color_continuous_scale="Plasma",
    )
    sla_fig.update_layout(
        height=2000,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF"
    )

    # Trend graph
    trend_fig = px.line(
        TREND,
        x="Month",
        y="RESOLUTION_TIME_DAYS",
        markers=True,
        template="plotly_dark"
    )
    trend_fig.update_layout(
        height=700,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # Scatter
    scatter_fig = px.scatter(
        dff,
        x="Volume",
        y="Avg_Resolution",
        text="NEIGHBORHOOD",
        color="Avg_Resolution",
        color_continuous_scale="Plasma"
    )
    scatter_fig.update_traces(textposition="top center")

    return kpis, table_html, sla_fig, trend_fig, scatter_fig