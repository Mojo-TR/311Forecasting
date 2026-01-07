from dash import html, dcc, register_page, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.utils.utils import make_table, empty_figure, empty_table

register_page(__name__, path="/resolution-insights", title="Resolution Insights")
                
# LOAD PRECOMPUTED DATA
BASE = "precomputed_data/resolution/"

RES_STATS = {
    "neighborhood": {
        "monthly": pd.read_parquet(BASE + "resolution_stats_neighborhood.parquet"),
        "all": pd.read_parquet(BASE + "resolution_stats_all_months_neighborhood.parquet"),
        "heatmap": pd.read_parquet(BASE + "sla_heatmap_neighborhood.parquet"),
    },
    "department": {
        "monthly": pd.read_parquet(BASE + "resolution_stats_department.parquet"),
        "all": pd.read_parquet(BASE + "resolution_stats_all_months_department.parquet"),
        "heatmap": pd.read_parquet(BASE + "sla_heatmap_department.parquet"),
    },
    "category": {
        "monthly": pd.read_parquet(BASE + "resolution_stats_category.parquet"),
        "all": pd.read_parquet(BASE + "resolution_stats_all_months_category.parquet"),
        "heatmap": pd.read_parquet(BASE + "sla_heatmap_category.parquet"),
    },
}


CITY = pd.read_parquet(BASE + "resolution_citywide.parquet")
FAST_SLOW = pd.read_parquet(BASE + "fastest_slowest.parquet")
TREND = pd.read_parquet(BASE + "trend.parquet")

MONTHS = pd.read_parquet(BASE + "months.parquet").iloc[:, 0].tolist()
NEIGH_LIST = pd.read_parquet(BASE + "neighborhoods.parquet").iloc[:, 0].tolist()

TAB_TO_LEVEL = {
    "rank-nbh": "neighborhood",
    "rank-dept": "department",
    "rank-cat": "category",
    "scatter-nbh": "neighborhood",
    "scatter-dept": "department",
    "scatter-cat": "category",
    "heat-nbh": "neighborhood",
    "heat-dept": "department",
    "heat-cat": "category",
}

LEVEL_TO_LABEL = {
    "neighborhood": "Neighborhood",
    "department": "Department",
    "category": "Category",
}

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
            
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H4("Resolution Ranking", className="text-white"),
                                dbc.Tabs(
                                    [
                                        dbc.Tab(label="Department", tab_id="rank-dept", labelClassName="text-info-emphasis"),
                                        dbc.Tab(label="Category", tab_id="rank-cat", labelClassName="text-info-emphasis"),
                                        dbc.Tab(label="Neighborhood", tab_id="rank-nbh", labelClassName="text-info-emphasis"),
                                    ],
                                    id="rank-tabs",
                                    active_tab="rank-nbh",
                                    className="mb-3 custom-tabs",
                                ),
                                html.Div(
                                    id="resolution-table",
                                    style={
                                        "maxHeight": "500px",
                                        "overflowY": "auto",
                                    }
                                )
                            ]),
                            className="bg-dark border-dark h-100"
                        ),
                        md=6
                    ),

                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H4("Volume vs Resolution Time", className="text-white"),
                                dbc.Tabs(
                                    [
                                        dbc.Tab(label="Department", tab_id="scatter-dept", labelClassName="text-info-emphasis"),
                                        dbc.Tab(label="Category", tab_id="scatter-cat", labelClassName="text-info-emphasis"),
                                        dbc.Tab(label="Neighborhood", tab_id="scatter-nbh", labelClassName="text-info-emphasis"),
                                    ],
                                    id="scatter-tabs",
                                    active_tab="scatter-nbh",
                                    className="mb-3 custom-tabs",
                                ),
                                dcc.Graph(
                                    id="resolution-scatter",
                                    style={"height": "500px"}
                                )
                            ]),
                            className="bg-dark border-dark h-100"
                        ),
                        md=6
                    ),
                ],
                className="mb-4"
            ),
                        
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

            # SLA Heatmap
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H4("SLA Performance Heatmap", className="text-white"),
                            dbc.Tabs(
                                [
                                    dbc.Tab(label="Department", tab_id="heat-dept", labelClassName="text-info-emphasis"),
                                    dbc.Tab(label="Category", tab_id="heat-cat", labelClassName="text-info-emphasis"),
                                    dbc.Tab(label="Neighborhood", tab_id="heat-nbh", labelClassName="text-info-emphasis"),
                                ],
                                id="heat-tabs",
                                active_tab="heat-nbh",
                                className="mb-3 custom-tabs",
                            ),
                            dcc.Graph(id="resolution-sla-heatmap", style={"height": "800px", "overflowY": "auto",})
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
    Input("resolution-month", "value"),
)
def update_resolution_kpis(month):

    if month == "all":
        r = CITY.query("MonthName == 'all'").iloc[0]
        fs = FAST_SLOW.query("MonthName == 'all'").iloc[0]
    else:
        r = CITY.query("MonthName == @month").iloc[0]
        fs = FAST_SLOW.query("MonthName == @month").iloc[0]

    return [
        make_kpi("Avg Resolution (Citywide)", f"{r['Avg_Resolution']:.0f} days"),
        make_kpi("Median Resolution (Citywide)", f"{r['Median_Resolution']:.0f} days"),
        make_kpi("Fastest", f"{fs['Fastest']} — {fs['FastestValue']:.0f}", "success"),
        make_kpi("Slowest", f"{fs['Slowest']} — {fs['SlowestValue']:.0f}", "danger"),
    ]


@callback(
    Output("resolution-table", "children"),
    Input("rank-tabs", "active_tab"),
    Input("resolution-month", "value"),
)
def update_resolution_table(tab, month):

    level = TAB_TO_LEVEL[tab]
    data = RES_STATS[level]
    label = LEVEL_TO_LABEL[level]

    if month == "all":
        df = data["all"]
    else:
        df = data["monthly"].query("MonthName == @month")

    if df.empty:
        return empty_table("No data available.")

    DISPLAY_COLS = ["Group", "Volume", "Avg_Resolution"]

    table_df = (
        df[DISPLAY_COLS]
        .sort_values("Avg_Resolution", ascending=True)
        .assign(Avg_Resolution=lambda x: x["Avg_Resolution"].round(1))
        .head(15)
    )
    
    table_df.insert(0, "Rank", range(1, len(table_df) + 1))

    return make_table(
        table_df,
            col_rename={
            "Group": label,
            "Avg_Resolution": "Avg Resolution"
        }
    )


@callback(
    Output("resolution-scatter", "figure"),
    Input("scatter-tabs", "active_tab"),
    Input("resolution-month", "value"),
)
def update_resolution_scatter(tab, month):

    level = TAB_TO_LEVEL[tab]
    data = RES_STATS[level]

    if month == "all":
        df = data["all"]
    else:
        df = data["monthly"].query("MonthName == @month")

    if df.empty:
        return empty_figure("No data available for this selection.")

    fig = px.scatter(
        df,
        x="Volume",
        y="Avg_Resolution",
        hover_name="Group",
        color="Avg_Resolution",
        color_continuous_scale="Plasma"
    )

    fig.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Total Complaints",
        yaxis_title="Avg Resolution (days)",
        font=dict(color="white"),
        coloraxis_colorbar=dict(title=""),
        autosize=False
    )
    
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "<b>Total Complaints:</b> %{x:,}<br>"
            "<b>Avg Resolution:</b> %{y:.1f} days"
            "<extra></extra>"
        )
    )

    return fig

@callback(
    Output("resolution-sla-heatmap", "figure"),
    Input("heat-tabs", "active_tab"),
)
def update_heatmap(tab):

    level = TAB_TO_LEVEL[tab]
    heatmap = RES_STATS[level]["heatmap"]

    fig = px.imshow(
        heatmap,
        aspect="auto",
        color_continuous_scale="Plasma"
    )

    fig.update_layout(
        height=1000,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        coloraxis_colorbar=dict(title=""),
        xaxis=dict(
            tickangle=-45,
            title="Month",
            categoryorder="array",
            categoryarray=[
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
        ),
        hoverlabel=dict(
            bgcolor="#170229",
            font_color="#EAEAEA",
            bordercolor="#555",
            font_size=13,
            font_family="Inter, Arial, sans-serif",
        ),
        yaxis=dict(title=LEVEL_TO_LABEL[level].title()),
        margin=dict(b=140)
    )
    
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "<b>Month:</b> %{x}<br>"
            "<b>SLA Performance:</b> %{z:.1f}%"
            "<extra></extra>"
        )
    )

    return fig

@callback(
    Output("resolution-trend", "figure"),
    Input("resolution-month", "value"),
)
def update_trend(_):

    fig = px.line(
        TREND,
        x="Month",
        y="RESOLUTION_TIME_DAYS",
        markers=True,
        template="plotly_dark"
    )

    fig.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Avg Resolution Time (days)",
    )
    
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "<b>Avg Resolution Time:</b> %{y:.1f} days"
            "<extra></extra>"
        )
    )

    return fig