from dash import html, dcc, register_page, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from app.utils.data_loader import df
from app.data.category_mapping import category_to_types
from app.utils.utils import make_table


register_page(__name__, path="/summary", title="Summary")

# Preprocess
df["MonthName"] = df["CREATED DATE"].dt.month_name()

# Dropdown options
metric_options = [
    {"label": "Department", "value": "DEPARTMENT"},
    {"label": "Division", "value": "DIVISION"},
    {"label": "Category", "value": "CATEGORY"},
]

month_options = [{"label": "All Months", "value": "all"}] + [
    {"label": m, "value": m} for m in df["MonthName"].dropna().unique()
]

neighborhood_options =[{"label": "All Neighborhoods", "value": "all"}] +  [
    {"label": n.title(), "value": n}
    for n in sorted(df["NEIGHBORHOOD"].dropna().unique())
]

# Layout
layout = dbc.Container([
    html.H2("Complaint Summary", className="text-center text-primary mb-4 mt-4"),

    dbc.Row(
        [
            dbc.Col(
                dbc.RadioItems(
                    id="metric-select",
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-outline-primary",
                    labelCheckedClassName="active",
                    options=metric_options,
                    value="DEPARTMENT",
                ),
                className="d-flex justify-content-center"
            )
        ],
        className="mb-4"
    ),

    dbc.Row([
        
        dbc.Col([
            dbc.Label("Select Neighborhood:", className="text-white"),
            dbc.Select(id="neighborhood-dropdown", options=neighborhood_options, value="all", style={"width": "300px"})
        ], width="auto"),

        dbc.Col([
            dbc.Label("Select Month:", className="text-white"),
            dbc.Select(id="month-dropdown", options=month_options, value="all", style={"width": "300px"})
        ], width="auto"),
    ], justify="center", className="mb-4"),

    # Treemap
    dbc.Card(
        dbc.CardBody(
            dbc.Spinner(
                html.Div(
                    dcc.Graph(id="metric-treemap"),
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                    }
                ),
                type="grow",
                color="primary",
                size="lg"
            )
        ),
        className="bg-dark border-dark text-white rounded-3 mb-5"
    ),

    # Resolution Table
    dbc.Card(
        dbc.CardBody(
            dbc.Spinner(
                html.Div(
                    [
                        html.H5(id="table-title", className="text-white mb-3"),
                        html.Div(id="resolution-table-container")
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "height": "100%",
                        "flexDirection": "column"  # stack H5 and table vertically
                    }
                ),
                type="grow",
                color="primary",
                size="lg"
            )
        ),
        className="bg-dark border-dark my-5"
    ),

    # Div that wraps the dropdown + case types list
    html.Div(
        [
            dbc.Label("Select Category to See Case Types:", className="text-white"),
            dbc.Select(id="category-case-dropdown", className=" mb-4 ",options=[], value=None, style={"width": "300px"}),
            html.Div(id="case-type-list"),
        ],
        id="case-dropdown-container",
        style={"display": "none"}  # hidden initially
    ),

    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
    ], style={"textAlign": "center"}),
], fluid=True)

@callback(
    Output("metric-treemap", "figure"),
    Output("resolution-table-container", "children"),
    Output("table-title", "children"),
    Input("metric-select", "value"),
    Input("neighborhood-dropdown", "value"),
    Input("month-dropdown", "value"),
)
def update_metric_charts(selected_metric, selected_neighborhood, selected_month):
    filtered_df = df.copy()

    if selected_neighborhood != "all" and selected_neighborhood:
        filtered_df = filtered_df[filtered_df["NEIGHBORHOOD"] == selected_neighborhood]

    if selected_month and selected_month != "all":
        filtered_df = filtered_df[filtered_df["MonthName"] == selected_month]

    if selected_metric not in filtered_df.columns or filtered_df.empty:
        return px.treemap(title="No data"), html.P("No data available"), "No Data Available"

    count_df = (
        filtered_df[selected_metric]
        .value_counts()
        .reset_index()
    )
    count_df.columns = ["Metric", "Count"]

    # Treemap
    treemap = px.treemap(
        count_df,
        path=["Metric"],
        values="Count",
        color="Count",
        color_continuous_scale="Plasma",
        title=f"Complaints by {selected_metric.title()}",
        hover_data={"Metric": True},
        labels={"Metric": selected_metric.title(), "Count": "Complaints"},
    )
    treemap.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#140327",
        font_color="white",
    )

    # Build resolution table
    if "RESOLUTION_TIME_DAYS" in filtered_df.columns:
        stats = (
            filtered_df.groupby(selected_metric)["RESOLUTION_TIME_DAYS"]
            .agg(["count", "mean", "median"])
            .reset_index()
            .rename(columns={
                selected_metric: selected_metric.title(),
                "count": "Count",
                "mean": "Avg Resolution",
                "median": "Median Resolution"
            })
        )
        stats = stats[stats["Count"] > 0]
        stats["Avg Resolution"] = stats["Avg Resolution"].round(0)
        stats["Median Resolution"] = stats["Median Resolution"].round(0)

        # Create dbc.Table dynamically
        resolution_table = make_table(stats)
    else:
        resolution_table = html.P("No resolution time data available.")

    table_title = f"Resolution Time Summary by {selected_metric.title()}"
    return treemap, resolution_table, table_title

@callback(
    Output("case-type-list", "children"),
    Input("category-case-dropdown", "value"),
    Input("month-dropdown", "value")
)
def show_case_types(selected_category, selected_month):
    if not selected_category:
        return None

    filtered_df = df.copy()
    if selected_month and selected_month != "all":
        filtered_df = filtered_df[filtered_df["MonthName"] == selected_month]

    case_types = category_to_types.get(selected_category, [])
    if not case_types:
        return html.P("No case types found.", style={"color": "#AAA"})

    return dbc.Card(
        dbc.CardBody([
            html.H5(f"Case Types under {selected_category}:", className="text-info"),
            html.Ul([html.Li(case, style={"color": "#FFF"}) for case in sorted(case_types)])
        ]),
        className="bg-dark border-dark mb-4"
    )

@callback(
    Output("case-dropdown-container", "style"),
    Input("metric-select", "value")
)
def show_case_dropdown(selected_metric):
    return {"display": "block"} if selected_metric == "CATEGORY" else {"display": "none"}

@callback(
    Output("category-case-dropdown", "options"),
    Input("metric-select", "value")
)
def populate_category_dropdown(selected_metric):
    if selected_metric == "CATEGORY":
        categories = sorted(df["CATEGORY"].dropna().unique())
        return [{"label": c, "value": c} for c in categories]
    return []


