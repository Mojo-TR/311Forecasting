from dash import html, dcc, register_page, callback, Output, Input
import pandas as pd
import plotly.express as px
from app.utils.data_loader import df
import dash_bootstrap_components as dbc
from app.utils.utils import make_table, category_to_types, empty_figure

register_page(__name__, path="/neighborhood-metrics", title="Neighborhood Metrics")

# Prepare data
df["MonthName"] = df["CREATED DATE"].dt.month_name()

month_options = [{"label": "All Months", "value": "all"}] + \
                [{"label": m, "value": m} for m in df["MonthName"].unique()]

neighborhood_options = [{"label": "All Neighborhoods", "value": "all"}] + \
                       [{"label": n, "value": n} for n in sorted(
                           df["NEIGHBORHOOD"]
                           .dropna()
                           .loc[lambda s: (s.str.strip() != "") & (s != "None")]
                           .unique()
                       )]


metrics = ["DEPARTMENT", "DIVISION", "CATEGORY"]

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
                style={"width": "300px"}
            )
        ], width="auto")
    ], justify="center", className="mb-4"),

    html.H5(id="selected-metric-display", className="text-white text-center mt-4 mb-4"),

    # Chart + Legend Row (each with its own spinner)
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
                outline=True,
                className="border-dark bg-dark",
                style={
                    "overflowX": "auto",
                    "padding": "10px",
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
                outline=True,
                className="border-dark bg-dark",
                style={
                    "height": "700px",
                    "overflowY": "auto",
                    "padding": "10px",
                }
            ),
            width=3
        )
    ], style={"flexWrap": "nowrap"}, className="mb-4"),

    # Neighborhood Breakdown
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
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
                className="border-dark bg-dark",
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
def update_bar(selected_metric, selected_month, selected_neighborhood):
    dff = df.copy()
    
    # Clean neighborhoods
    dff = dff.dropna(subset=["NEIGHBORHOOD"])
    dff = dff[dff["NEIGHBORHOOD"].str.strip() != ""]
    dff = dff[dff["NEIGHBORHOOD"] != "None"]

    # Filter month
    if selected_month not in [None, "all"]:
        dff = dff[dff["MonthName"] == selected_month]

    # GLOBAL EARLY EXIT — no data after filters
    if dff.empty or selected_metric not in dff.columns:
        fig = empty_figure("No data available")
        empty_legend = html.Div("No legend", style={"color": "#FFF"})
        empty_table_block = html.Div("No data available for the selected filters.", style={"color": "#FFF"})
        empty_pie = empty_figure("No pie chart data")
        return fig, empty_legend, empty_table_block, empty_pie

    # Aggregate complaints
    stacked_data = (
        dff.groupby(["NEIGHBORHOOD", selected_metric])
        .size()
        .reset_index(name="Count")
    )

    # LIMIT TO TOP 30 NEIGHBORHOODS
    neighborhood_order = (
        stacked_data.groupby("NEIGHBORHOOD")["Count"]
        .sum()
        .sort_values(ascending=False)
        .index[:30]
        .tolist()
    )

    stacked_data = stacked_data[stacked_data["NEIGHBORHOOD"].isin(neighborhood_order)]

    stacked_data["NEIGHBORHOOD"] = pd.Categorical(
        stacked_data["NEIGHBORHOOD"],
        categories=neighborhood_order,
        ordered=True
    )
    
    # LIMIT TO TOP 10 CATEGORIES
    category_order = (
        stacked_data.groupby(selected_metric)["Count"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    top_categories = category_order[:10]

    stacked_data = stacked_data[stacked_data[selected_metric].isin(top_categories)]

    stacked_data[selected_metric] = pd.Categorical(
        stacked_data[selected_metric],
        categories=top_categories,
        ordered=True
    )

    # Colors
    colors = px.colors.qualitative.Plotly
    colors = (colors * ((len(top_categories) // len(colors)) + 1))[:len(top_categories)]
    color_map = {cat: colors[i] for i, cat in enumerate(top_categories)}

    # Build metric counts AFTER filtering
    metric_counts = (
        dff[dff["NEIGHBORHOOD"].isin(neighborhood_order)][selected_metric]
        .value_counts()
        .to_dict()
    )
    
    # Filter down to only the top 10 categories
    metric_counts = {cat: metric_counts.get(cat, 0) for cat in top_categories}

    # STACKED BAR CHART
    fig = px.bar(
        stacked_data,
        x="NEIGHBORHOOD",
        y="Count",
        color=selected_metric,
        color_discrete_map=color_map,
        barmode="stack",
        category_orders={
            "NEIGHBORHOOD": neighborhood_order,
            selected_metric: top_categories,
        },
        height=640,
        width=max(1500, len(neighborhood_order) * 50),
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        showlegend=False,
        margin=dict(l=40, r=40, t=80, b=80)
    )

    # LEGEND 
    legend_items = []
    if selected_metric == "CATEGORY":
        for cat in top_categories:
            subtypes = category_to_types.get(cat, [])
            legend_items.append(
                html.Div([
                    html.Div(
                        f"{cat} ({metric_counts.get(cat, 0)})",
                        style={
                            "backgroundColor": color_map.get(cat, "#555"),
                            "padding": "8px",
                            "marginBottom": "4px",
                            "color": "#FFF",
                            "fontWeight": "bold"
                        },
                    ),
                    html.Ul(
                        [html.Li(sub, style={"color": "#DDD", "fontSize": "13px"}) for sub in sorted(subtypes)],
                        style={
                            "marginLeft": "16px",
                            "marginTop": "2px",
                            "marginBottom": "10px",
                            "paddingLeft": "10px",
                            "maxHeight": "150px",
                            "overflowY": "auto",
                            "borderLeft": "2px solid #333"
                        }
                    ) if subtypes else html.I("No subtypes", style={"color": "#AAA", "fontSize": "12px"})
                ])
            )
    else:
        legend_items = [
            html.Div(
                f"{cat} ({metric_counts.get(cat, 0)})",
                style={
                    "backgroundColor": color_map.get(cat, "#555"),
                    "padding": "8px",
                    "margin": "2px",
                    "color": "#FFF"
                }
            )
            for cat in top_categories
        ]

    # TOP 10 TABLE
    neighborhood_filter = dff.copy()
    if selected_neighborhood and selected_neighborhood != "all":
        neighborhood_filter = neighborhood_filter[neighborhood_filter["NEIGHBORHOOD"] == selected_neighborhood]

    table_data = (
        neighborhood_filter[selected_metric]
        .value_counts()
        .reset_index()
        .rename(columns={"index": selected_metric, selected_metric: "Count"})
        .head(10)
    )
    if table_data.empty:
        table_block = html.Div(
            f"No data available for {selected_neighborhood or 'selection'}.",
            style={"color": "#FFF"}
        )
        pie_fig = empty_figure("No pie data")
    else:
        if selected_metric == "CATEGORY":
            metric_label = "Categories"
        else:
            metric_label = selected_metric.title() + "s"
        table_block = html.Div([
            html.H5(
                f"Top 10 {metric_label} for "
                f"{'All Neighborhoods' if selected_neighborhood == 'all' else selected_neighborhood}",
                className="text-white mb-3"
            ),
            make_table(table_data, col_rename={selected_metric: selected_metric.title(), "Count": "Requests"})
        ])
        
        # PIE CHART DATA
        pie_df = dff.copy()

        # Apply neighborhood filter
        if selected_neighborhood != "all":
            pie_df = pie_df[pie_df["NEIGHBORHOOD"] == selected_neighborhood]

        # Count values
        pie_counts = (
            pie_df[selected_metric]
            .value_counts(dropna=True)
            .reset_index()
        )

        # VERY IMPORTANT: rename columns explicitly and safely
        pie_counts.columns = [selected_metric, "Count"]

        # Build pie chart
        pie_fig = px.pie(
            pie_counts,
            names=pie_counts.columns[0],   # same as selected_metric
            values="Count",
        )
        
        pie_fig.update_traces(
            hole=0.4,
            textinfo="none"
        )

        # Style
        pie_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FFF",
            title_font_size=20,
            showlegend=False 
        )

    return fig, legend_items, table_block, pie_fig