from dash import html, dcc, register_page, callback, Output, Input
import pandas as pd
import plotly.express as px
from app.utils.data_loader import df
import dash_bootstrap_components as dbc
from app.data.category_mapping import category_to_types

register_page(__name__, path="/metrics", title="Neighborhood Metrics")

# Prepare data
df["MonthName"] = df["CREATED DATE"].dt.month_name()

month_options = [{"label": "All Months", "value": "all"}] + \
                [{"label": m, "value": m} for m in df["MonthName"].unique()]


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

    # Chart + Legend Row
    dbc.Row([
        # Chart
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dbc.Spinner(
                        dcc.Graph(id="stackedbar-graph", style={"minWidth": "1200px"}),
                        type="grow",
                        color="primary",
                        size="lg"
                    )
                ),
                color="dark",
                outline=True,
                className="border-dark bg-dark",
                style={
                    "overflowX": "auto",
                    "padding": "10px",
                    "borderRadius": "8px"
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
                        type="grow",
                        color="primary",
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
                    "borderRadius": "8px"
                }
            ),
            width=3
        )
    ], style={"flexWrap": "nowrap"}, className="mb-4"),

    # Resolution bar
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    dbc.Spinner(
                        dcc.Graph(id="resolution-bar", figure=None),
                        type="grow",
                        color="primary",
                        size="lg"
                    )
                ),
                color="dark",
                className="border-dark bg-dark",
                outline=True,
                style={
                    "overflowX": "auto",
                    "padding": "10px",
                    "borderRadius": "8px"
                }
            ),
            width=12
        )
    ]),

    # Home button
    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
    ], style={"textAlign": "center"})

], fluid=True)


# Callback
@callback(
    Output("stackedbar-graph", "figure"),
    Output("stackedbar-legend", "children"),
    Output("resolution-bar", "figure"),
    Input("stackedbar-metric-dropdown", "value"),
    Input("month-dropdown", "value")
)
def update_bar(selected_metric, selected_month):
    dff = df.copy()
    
    # Drop null or empty neighborhoods
    dff = dff.dropna(subset=["NEIGHBORHOOD"])
    dff = dff[dff["NEIGHBORHOOD"] != "None"]
    dff = dff[dff["NEIGHBORHOOD"].str.strip() != ""]

    if selected_month != "all" and selected_month is not None:
        dff = dff[dff["MonthName"] == selected_month]

    # Compute resolution time metrics per neighborhood
    resolution_stats = (
        dff.groupby("NEIGHBORHOOD")["RESOLUTION_TIME_DAYS"]
        .agg(["mean", "median", "max"])
        .reset_index()
        .rename(columns={"mean": "Avg_Resolution", "median": "Median_Resolution", "max": "Max_Resolution"})
    )

    if dff.empty or selected_metric not in dff.columns:
        fig = px.bar(title=f"No data available for month {selected_month}")
        fig.update_layout(
            plot_bgcolor="#20063B",
            paper_bgcolor="#20063B",
            font_color="#FFFFFF"
        )
        return fig, html.Div("No legend", style={"color": "#FFF"})

    # Aggregate counts
    stacked_data = (
        dff.groupby(["NEIGHBORHOOD", selected_metric])
        .size()
        .reset_index(name="Count")
    )

    # Order neighborhoods by total complaints
    neighborhood_order = (
        stacked_data.groupby("NEIGHBORHOOD")["Count"]
        .sum()
        .sort_values(ascending=False)
        .index
    )
    stacked_data["NEIGHBORHOOD"] = pd.Categorical(
        stacked_data["NEIGHBORHOOD"],
        categories=neighborhood_order,
        ordered=True
    )

    # Order metric categories by total count
    category_order = (
        stacked_data.groupby(selected_metric)["Count"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # Assign colors
    categories = stacked_data[selected_metric].unique()
    colors = px.colors.qualitative.Plotly
    colors = (colors * ((len(categories) // len(colors)) + 1))[:len(categories)]
    color_map = {cat: colors[i] for i, cat in enumerate(categories)}

    # Stacked bar chart
    fig = px.bar(
        stacked_data,
        x="NEIGHBORHOOD",
        y="Count",
        color=selected_metric,
        color_discrete_map=color_map,
        barmode="stack",
        category_orders={"NEIGHBORHOOD": neighborhood_order, selected_metric: category_order},
        hover_data={"Count": True, selected_metric: True},
        height=640,
        width=max(1500, len(neighborhood_order)*50)
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor="#140327",
        paper_bgcolor="#140327",
        font_color="#FFFFFF",
        margin=dict(l=40, r=40, t=80, b=80),
        bargap=0.2,
        showlegend=False
    )

    # Sort by total reports for the selected metric
    metric_col = selected_metric
    metric_counts = dff[metric_col].value_counts().to_dict()
    categories = sorted(metric_counts.keys(), key=lambda c: metric_counts[c], reverse=True)

    # Build legend
    legend_items = []
    if selected_metric == "CATEGORY":
        for cat in categories:
            subtypes = category_to_types.get(cat, [])
            legend_items.append(
                html.Div([
                    html.Div(
                        f"{cat} ({metric_counts.get(cat, 0)})",
                        style={
                            "backgroundColor": color_map.get(cat, "#555"),
                            "padding": "8px",
                            "marginBottom": "4px",
                            "borderRadius": "4px",
                            "color": "#FFFFFF",
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
                    "borderRadius": "4px",
                    "color": "#FFFFFF"
                },
            )
            for cat in categories
        ]

    res_fig = px.bar(
        resolution_stats,
        x="NEIGHBORHOOD",
        y="Avg_Resolution",
        color="Avg_Resolution",
        color_continuous_scale="Plasma",
        labels={"Avg_Resolution": "Avg Resolution (days)"},
    )
    res_fig.update_layout(
        plot_bgcolor="#140327",
        paper_bgcolor="#140327",
        font_color="#FFF",
        height=640,
        width=max(1500, len(neighborhood_order) * 50),
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig, legend_items, res_fig

@callback(
    Output("selected-metric-display", "children"),
    Input("stackedbar-metric-dropdown", "value")
)
def display_selected_metric(selected_metric):
    return f"Complaints by {selected_metric.title()}"