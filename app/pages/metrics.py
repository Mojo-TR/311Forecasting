from dash import html, dcc, register_page, callback, Output, Input
import pandas as pd
import plotly.express as px
from app.utils.data_loader import df
import dash_bootstrap_components as dbc
from app.utils.utils import make_table, category_to_types, empty_figure

register_page(__name__, path="/neighborhood-metrics", title="Neighborhood Metrics")


metrics = ["DEPARTMENT", "DIVISION", "CATEGORY"]

# LOAD PRECOMPUTED DATA
BASE_PATH = "precomputed_data/metrics/"

NEIGH_LIST = pd.read_parquet(BASE_PATH + "neighborhood_list.parquet").iloc[:, 0].tolist()
MONTH_LIST = pd.read_parquet(BASE_PATH + "month_list.parquet").iloc[:, 0].tolist()

BY_CATEGORY_NEIGH = pd.read_parquet(BASE_PATH + "by_category_neigh.parquet")
BY_DEPT_NEIGH = pd.read_parquet(BASE_PATH + "by_department_neigh.parquet")
BY_DIV_NEIGH = pd.read_parquet(BASE_PATH + "by_division_neigh.parquet")

CATEGORY_TOTAL = pd.read_parquet(BASE_PATH + "by_category.parquet")
DEPARTMENT_TOTAL = pd.read_parquet(BASE_PATH + "by_department.parquet")
DIVISION_TOTAL = pd.read_parquet(BASE_PATH + "by_division.parquet")

NEIGH_TOTAL = pd.read_parquet(BASE_PATH + "neighborhood_totals.parquet")


# Metrics map → tells callback which parquet to use
METRIC_TO_PARQUET = {
    "CATEGORY": (BY_CATEGORY_NEIGH, CATEGORY_TOTAL),
    "DEPARTMENT": (BY_DEPT_NEIGH, DEPARTMENT_TOTAL),
    "DIVISION": (BY_DIV_NEIGH, DIVISION_TOTAL),
}

ALL_MONTH_MAP = {
    "CATEGORY": pd.read_parquet(BASE_PATH + "by_category_neigh_allmonths.parquet"),
    "DEPARTMENT": pd.read_parquet(BASE_PATH + "by_department_neigh_allmonths.parquet"),
    "DIVISION": pd.read_parquet(BASE_PATH + "by_division_neigh_allmonths.parquet"),
}

month_options = [{"label": "All Months", "value": "all"}] + [
    {"label": m, "value": m} for m in MONTH_LIST
]

neighborhood_options = [{"label": "All Neighborhoods", "value": "all"}] + [
    {"label": n, "value": n} for n in NEIGH_LIST
]


layout = dbc.Container([
    html.H2("Neighborhood Metrics", className="text-center text-primary mb-4 mt-4"),

    # Metric + Month dropdowns
    dbc.Row([
        dbc.Col([
            html.Label("Group By:", className="text-white mb-2"),
            dbc.Select(
                id="stackedbar-metric-dropdown",
                options=[{"label": m, "value": m} for m in metrics],
                value="DEPARTMENT",
                style={"width": "300px"}
            )
        ], width="auto"),

        dbc.Col([
            html.Label("Select Month:", className="text-white mb-2"),
            dbc.Select(
                id="month-dropdown",
                options=month_options,
                value="all",
                style={"width": "300px"}
            )
        ], width="auto")
    ], justify="center", className="mb-4"),

    html.H5(id="selected-metric-display", className="text-white text-center mx-4"),
    
    # Neighborhood Breakdown
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4(
                        "Neighborhood Breakdown",
                        className="text-white mb-4"
                    ),
                    # Neighborhood Dropdown
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Neighborhood:", className="text-white mb-2 fw-bold"),
                            dbc.Select(
                                id="neighborhood-dropdown",
                                options=neighborhood_options,
                                value="all",
                                style={"maxWidth": "320px"}
                            )
                        ], width="auto")
                    ], className="mb-4"),

                    # Pie + Table Row (ONE spinner for both)
                    dbc.Row([
                        dbc.Spinner(
                            dbc.Row([
                                # Pie Chart
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            dcc.Graph(
                                                id="metric-pie-chart",
                                                config={"displayModeBar": False},
                                                style={"height": "450px"}
                                            )
                                        ),
                                        color="dark",
                                        outline=True,
                                        className="border-secondary shadow-sm",
                                    ),
                                    width=5,
                                    style={"paddingRight": "8px"}
                                ),

                                # Table
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            html.Div(
                                                id="stackedbar-table",
                                                style={
                                                    "maxHeight": "450px",
                                                    "overflowY": "auto",
                                                    "paddingRight": "6px"
                                                }
                                            )
                                        ),
                                        color="dark",
                                        outline=True,
                                        className="border-secondary shadow-sm",
                                    ),
                                    width=7,
                                    style={"paddingLeft": "8px"}
                                )

                            ], className="g-0"),

                            color="primary",
                            type="grow",
                            size="lg"
                        )
                    ])
                ]),
                color="dark",
                className="border-dark bg-dark my-4",
                style={"padding": "20px"}
            ),
            width=12
        )
    ]),
    
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([

                    # Optional section header
                    html.H4(
                        "Chart Breakdown (Top 30 NeighborhoodS)",
                        className="text-white mb-4"
                    ),

                    # Inner row holding Chart + Legend
                    dbc.Row([

                        # Chart
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="stackedbar-graph",
                                            style={"minWidth": "1200px"}
                                        ),
                                        color="primary",
                                        type="grow",
                                        size="lg"
                                    )
                                ),
                                color="dark",
                                outline=False,
                                className="bg-dark border-0",
                                style={
                                    "overflowX": "auto",
                                    "padding": "5px",
                                }
                            ),
                            width=9
                        ),

                        # Legend
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    dbc.Spinner(
                                        html.Div(id="stackedbar-legend"),
                                        color="primary",
                                        type="grow",
                                        size="lg"
                                    )
                                ),
                                color="dark",
                                outline=False,
                                className="bg-dark border-0",
                                style={
                                    "height": "700px",
                                    "overflowY": "auto",
                                    "padding": "5px",
                                }
                            ),
                            width=3
                        ),

                    ], style={"flexWrap": "nowrap"}),

                ]),
                color="dark",
                className="border-dark bg-dark my-4",
                style={"padding": "20px"}
            ),
            width=12
        )
    ]),

    # Home button
    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
    ], style={"textAlign": "center"})

], fluid=True)

@callback(
    Output("stackedbar-graph", "figure"),
    Output("stackedbar-legend", "children"),
    Output("stackedbar-table", "children"),
    Output("metric-pie-chart", "figure"),
    Input("stackedbar-metric-dropdown", "value"),
    Input("month-dropdown", "value"),
    Input("neighborhood-dropdown", "value")
)
def update_fig(selected_metric, selected_month, selected_neighborhood):

    # LOAD METRIC DATA

    neigh_df, metric_total_df = METRIC_TO_PARQUET[selected_metric]

    # Filter by month
    if selected_month != "all":
        dff = neigh_df[neigh_df["MonthName"] == selected_month]
    else:
        all_month_df = ALL_MONTH_MAP[selected_metric]
        dff = all_month_df.copy()

    if dff.empty:
        fig = empty_figure("No data available")
        return fig, html.Div(), html.Div(), empty_figure("No pie data")

    # GET TOP 30 NEIGHBORHOODS (FOR CHART ONLY)
    top_neigh = NEIGH_TOTAL["NEIGHBORHOOD"].head(30).tolist()

    # DO NOT inject selected neighborhood into bar chart
    dff = dff[dff["NEIGHBORHOOD"].isin(top_neigh)]

    # If user selects a neighborhood, make sure it remains in the chart
    if selected_neighborhood != "all" and selected_neighborhood not in top_neigh:
        top_neigh.append(selected_neighborhood)

    dff = dff[dff["NEIGHBORHOOD"].isin(top_neigh)]

    # TOP 10 METRIC ITEMS

    top_metric_items = (
        metric_total_df.sort_values("Count", ascending=False)
        .head(10)[selected_metric]
        .tolist()
    )

    dff = dff[dff[selected_metric].isin(top_metric_items)]

    # COLOR MAP

    colors = px.colors.qualitative.Plotly
    colors = (colors * ((len(top_metric_items) // len(colors)) + 1))[:len(top_metric_items)]
    color_map = {cat: colors[i] for i, cat in enumerate(top_metric_items)}

    # STACKED BAR CHART

    fig = px.bar(
        dff,
        x="NEIGHBORHOOD",
        y="Count",
        color=selected_metric,
        color_discrete_map=color_map,
        barmode="stack",
        category_orders={
            "NEIGHBORHOOD": top_neigh,
            selected_metric: top_metric_items
        },
        height=640,
        width=max(1500, len(top_neigh) * 50),
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        showlegend=False,
        margin=dict(l=40, r=40, t=80, b=80),
    )

    # LEGEND

    legend_items = []
    for cat in top_metric_items:
        legend_items.append(
            html.Div(
                f"{cat}",
                style={
                    "padding": "8px",
                    "backgroundColor": color_map[cat],
                    "marginBottom": "4px",
                    "color": "#FFF",
                    "fontWeight": "bold"
                }
            )
        )

    # PIE + TABLE SECTION
    raw_df = neigh_df.copy()

    # Apply month correctly
    if selected_month != "all":
        raw_df = raw_df[raw_df["MonthName"] == selected_month]

    # Apply neighborhood filter
    if selected_neighborhood != "all":
        raw_df = raw_df[raw_df["NEIGHBORHOOD"] == selected_neighborhood]

    # Aggregate by the selected metric
    table_df = (
        raw_df.groupby(selected_metric)["Count"]
        .sum()
        .reset_index()
        .sort_values("Count", ascending=False)
        .head(10)
    )

    # Build Table Component
    if table_df.empty:
        table_block = html.Div("No data", style={"color": "#FFF"})
    else:
        table_block = make_table(
            table_df.rename(columns={
                selected_metric: selected_metric.title(),
                "Count": "Requests"
            })
        )

    # PIE CHART
    if table_df.empty:
        pie_fig = empty_figure("No pie data")
    else:
        pie_fig = px.pie(
            table_df,
            names=selected_metric,
            values="Count",
            color=selected_metric,
            color_discrete_map=color_map
        )

        pie_fig.update_traces(hole=0.4, textinfo="none")
        pie_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFF",
            showlegend=False,
        )

    return fig, legend_items, table_block, pie_fig