from dash import html, dcc, register_page, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.utils.data_loader import df
from app.utils.utils import make_table, empty_figure, empty_table


register_page(__name__, path="/resolution", title="Resolution Insights")

# Precompute Month Names
df["MonthName"] = df["CREATED DATE"].dt.month_name()

month_options = [{"label": "All Months", "value": "all"}] + \
                [{"label": m, "value": m} for m in df["MonthName"].unique()]

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
                ])
                , className="bg-dark border-dark"),
        )
    ], className="mb-4"),

    # SLA Heatmap
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("SLA Performance Heatmap", className="text-white"),
                    dbc.Spinner(
                        html.Div(
                            dcc.Graph(id="resolution-sla-heatmap"),
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto"
                            }
                        ),
                        type="grow",
                        color="primary",
                        size="lg"
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
                    dbc.Spinner(
                        dcc.Graph(id="resolution-trend"),
                        type="grow",
                        color="primary",
                        size="lg"
                    )
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
                    dbc.Spinner(
                        dcc.Graph(id="resolution-scatter"),
                        type="grow",
                        color="primary",
                        size="lg"
                    )
                ]),
                className="bg-dark border-dark"
            )
        )
    ], className="mb-4"),

    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
    ], style={"textAlign": "center"})

], fluid=True)

# CALLBACK
@callback(
    Output("resolution-kpi-row", "children"),
    Output("resolution-table", "children"),
    Output("resolution-sla-heatmap", "figure"),
    Output("resolution-trend", "figure"),
    Output("resolution-scatter", "figure"),
    Input("resolution-month", "value")
)
def update_resolution_page(selected_month):

    dff = df.copy()

    # Filter by month
    if selected_month != "all":
        dff = dff[dff["MonthName"] == selected_month]

    # Clean neighborhoods
    dff = dff.dropna(subset=["NEIGHBORHOOD"])
    dff = dff[dff["NEIGHBORHOOD"].str.strip() != ""]
    dff = dff[dff["NEIGHBORHOOD"] != "None"]

    # EARLY EXIT: no data left after filtering
    if dff.empty:
        return (
            [],
            empty_table("No data available for this month."),
            empty_figure("No SLA data."),
            empty_figure("No trend data."),
            empty_figure("No resolution data.")
        )

    # Compute resolution stats per neighborhood
    resolution_stats = (
        dff.groupby("NEIGHBORHOOD")["RESOLUTION_TIME_DAYS"]
        .agg(["mean", "median", "max", "count"])
        .reset_index()
        .rename(columns={
            "mean": "Avg_Resolution",
            "median": "Median_Resolution",
            "max": "Max_Resolution",
            "count": "Volume"
        })
    )

    if resolution_stats.empty:
        return (
            [],
            empty_table("No resolution data."),
            empty_figure("No SLA data."),
            empty_figure("No trend data."),
            empty_figure("No resolution data.")
        )

    # KPI SUMMARY CARDS
    city_avg = resolution_stats["Avg_Resolution"].mean()
    city_median = resolution_stats["Median_Resolution"].median()

    if len(resolution_stats) == 1:
        fastest = slowest = resolution_stats.iloc[0]
    else:
        fastest = resolution_stats.sort_values("Avg_Resolution").iloc[0]
        slowest = resolution_stats.sort_values("Avg_Resolution").iloc[-1]

    kpi_cards = [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Avg Resolution (Citywide)", className="text-white"),
            html.H3(f"{city_avg:.0f} days", className="text-primary")
        ]), className="bg-dark border-dark"), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Median Resolution (Citywide)", className="text-white"),
            html.H3(f"{city_median:.0f} days", className="text-primary")
        ]), className="bg-dark border-dark"), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Fastest Neighborhood", className="text-white"),
            html.H4(f"{fastest['NEIGHBORHOOD']}", className="text-success"),
            html.H5(f"{fastest['Avg_Resolution']:.0f} days", className="text-success")
        ]), className="bg-dark border-dark"), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Slowest Neighborhood", className="text-white"),
            html.H4(f"{slowest['NEIGHBORHOOD']}", className="text-danger"),
            html.H5(f"{slowest['Avg_Resolution']:.0f} days", className="text-danger")
        ]), className="bg-dark border-dark"), width=3),
    ]

    # RANKING TABLE
    table_df = resolution_stats.sort_values("Avg_Resolution")
    table_df["Avg_Resolution"] = table_df["Avg_Resolution"].fillna(0).round().astype(int)

    col_rename = {
        "NEIGHBORHOOD": "Neighborhood",
        "Avg_Resolution": "Avg Days",
        "Median_Resolution": "Median",
        "Max_Resolution": "Max",
        "Volume": "Requests"
    }
    table_html = make_table(table_df, col_rename=col_rename)

    # SLA HEATMAP
    sla_df = dff.copy()
    sla_df["SLA_1"] = sla_df["RESOLUTION_TIME_DAYS"] <= 1
    sla_df["SLA_3"] = sla_df["RESOLUTION_TIME_DAYS"] <= 3
    sla_df["SLA_7"] = sla_df["RESOLUTION_TIME_DAYS"] <= 7
    sla_df["SLA_30"] = sla_df["RESOLUTION_TIME_DAYS"] <= 30
    sla_df["SLA_60"] = sla_df["RESOLUTION_TIME_DAYS"] <= 60
    sla_df["SLA_90"] = sla_df["RESOLUTION_TIME_DAYS"] <= 90

    sla_stats = sla_df.groupby("NEIGHBORHOOD")[["SLA_1", "SLA_3", "SLA_7", "SLA_30", "SLA_60", "SLA_90"]].mean() * 100
    
    sla_stats = sla_stats.rename(columns={
        "SLA_1": "1 Day",
        "SLA_3": "3 Days",
        "SLA_7": "7 Days",
        "SLA_30": "30 Days",
        "SLA_60": "60 Days",
        "SLA_90": "90 Days"
    })
    
    if sla_stats.empty:
        heatmap_fig = empty_figure("No SLA data.")
    else:
        heatmap_fig = px.imshow(
            sla_stats,
            aspect="auto",
            color_continuous_scale="Plasma",
            labels=dict(color="Percent Within SLA"),
        )
        heatmap_fig.update_layout(
            height=2000,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFF"
        )
        heatmap_fig.update_xaxes(
            showticklabels=True,
            ticklabelposition="inside bottom",
            mirror=True
        )

    # TREND OVER TIME
    trend = (
        dff.groupby(dff["CREATED DATE"].dt.to_period("M"))["RESOLUTION_TIME_DAYS"]
        .mean()
        .reset_index()
    )

    if trend.empty:
        trend_fig = empty_figure("No trend data.")
    else:
        trend["Month"] = trend["CREATED DATE"].dt.to_timestamp()
        trend_fig = px.line(
            trend,
            x="Month",
            y="RESOLUTION_TIME_DAYS",
            markers=True,
            labels={"RESOLUTION_TIME_DAYS": "Avg Resolution (Days)"}
        )
        trend_fig.update_layout(
            height=700,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFF"
        )

    # VOLUME VS RESOLUTION SCATTER
    if resolution_stats.empty:
        scatter_fig = empty_figure("No resolution data.")
    else:
        scatter_fig = px.scatter(
            resolution_stats,
            x="Volume",
            y="Avg_Resolution",
            text="NEIGHBORHOOD",
            color="Avg_Resolution",
            color_continuous_scale="Plasma",
        )
        scatter_fig.update_layout(
            height=700,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFF"
        )
        scatter_fig.update_traces(textposition="top center")

    return kpi_cards, table_html, heatmap_fig, trend_fig, scatter_fig
