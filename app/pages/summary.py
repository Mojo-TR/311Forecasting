from dash import html, dcc, register_page, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from app.utils.utils import make_table, empty_table, empty_figure

register_page(__name__, path="/summary", title="Summary")

# LOAD PRECOMPUTED DATA
BASE = "precomputed_data/summary/"

KPI_MONTHLY = pd.read_parquet(BASE + "kpi_monthly.parquet")
SLOW_DEPT = pd.read_parquet(BASE + "slowest_department.parquet")
SLOW_CAT = pd.read_parquet(BASE + "slowest_category.parquet")
SLOW_NBH = pd.read_parquet(BASE + "slowest_neighborhood.parquet")

SLA_DEPT = pd.read_parquet(BASE + "sla_risk_department.parquet")
SLA_CAT = pd.read_parquet(BASE + "sla_risk_category.parquet")
SLA_NBH = pd.read_parquet(BASE + "sla_risk_neighborhood.parquet")

VOLUME_COUNTS = pd.read_parquet(BASE + "volume_counts.parquet")
VOLUME_TREND = pd.read_parquet(BASE + "volume_monthly.parquet")

CATEGORY_CASETYPES = pd.read_parquet(BASE + "category_case_types.parquet")

CATEGORY_TO_TYPES = {
    row["CATEGORY"]: row["CaseTypes"] 
    for _, row in CATEGORY_CASETYPES.iterrows()
}

# MONTH DROPDOWN OPTIONS (correct!)
MONTH_LIST = sorted(KPI_MONTHLY["MonthName"].unique())
month_options = (
    [{"label": "All Months", "value": "all"}] +
    [{"label": m, "value": m} for m in MONTH_LIST if m != "all"]
)

# CATEGORY DROPDOWN FOR MODAL
category_values = sorted(CATEGORY_TO_TYPES.keys())
category_options = [{"label": c, "value": c} for c in category_values]
default_category_value = category_options[0]["value"] if category_options else None


# Data Dictionary (static metadata)
DATA_DICTIONARY = [
    {
        "field": "CASE NUMBER",
        "type": "string",
        "description": "Unique identifier for each 311 service request.",
        "example": "10123456",
    },
    {
        "field": "CREATED DATE",
        "type": "datetime",
        "description": "Date and time when the complaint was created.",
        "example": "2024-03-01 14:32",
    },
    {
        "field": "CLOSED DATE",
        "type": "datetime",
        "description": "Date and time when the complaint was closed or resolved.",
        "example": "2024-03-03 09:15",
    },
    {
        "field": "DEPARTMENT",
        "type": "string",
        "description": "City department responsible for handling the request.",
        "example": "Solid Waste Management",
    },
    {
        "field": "DIVISION",
        "type": "string",
        "description": "Sub-unit within the department handling the request.",
        "example": "Recycling Services",
    },
    {
        "field": "CATEGORY",
        "type": "string",
        "description": "Broad category describing the type of complaint.",
        "example": "Pothole",
    },
    {
        "field": "CASE TYPE",
        "type": "string",
        "description": "More specific type within the broader category.",
        "example": "Large Pothole",
    },
    {
        "field": "NEIGHBORHOOD",
        "type": "string",
        "description": "Neighborhood where the issue was reported.",
        "example": "Midtown",
    },
    {
        "field": "RESOLUTION_TIME_DAYS",
        "type": "numeric",
        "description": "Number of days between CREATED DATE and CLOSED DATE.",
        "example": "2.3",
    },
    {
        "field": "SEVERITY_SCORE",
        "type": "numeric",
        "description": "Derived severity metric based on volume and resolution time.",
        "example": "11.4",
    },
    {
        "field": "LAT / LON",
        "type": "float",
        "description": "Latitude / longitude of the complaint location.",
        "example": "29.7562, -95.3635",
    },
]


def build_data_dictionary_table():
    rows = []
    for row in DATA_DICTIONARY:
        rows.append(
            html.Tr(
                [
                    html.Td(row["field"]),
                    html.Td(row["type"]),
                    html.Td(row["description"]),
                    html.Td(row["example"]),
                ]
            )
        )

    table = dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Field"),
                        html.Th("Type"),
                        html.Th("Description"),
                        html.Th("Example"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        className="table-dark",
    )
    return table


# Layout
layout = dbc.Container(
    [
        html.H2(
            "Complaint Summary & Reference",
            className="text-center text-primary mb-4 mt-4",
        ),

        # Month filter
        dbc.Row(
            dbc.Col(
                [
                    dbc.Label(
                        "Select Month (for diagnostics):", className="text-white"
                    ),
                    dbc.Select(
                        id="summary-month-dropdown",
                        options=month_options,
                        value="all",
                        style={"maxWidth": "300px"},
                    ),
                ],
                width="auto",
                className="d-flex flex-column align-items-center",
            ),
            justify="center",
            className="mb-4",
        ),

        # KPI Row
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Total Complaints", className="text-info"),
                                html.H3(
                                    id="kpi-total-complaints",
                                    className="text-white",
                                ),
                            ]
                        ),
                        className="bg-dark border-dark",
                    ),
                    md=3,
                    sm=6,
                    className="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Avg Complaints / Month", className="text-info"),
                                html.H3(
                                    id="kpi-avg-month",
                                    className="text-white",
                                ),
                            ]
                        ),
                        className="bg-dark border-dark",
                    ),
                    md=3,
                    sm=6,
                    className="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6(
                                    "Median Resolution (Days)", className="text-info"
                                ),
                                html.H3(
                                    id="kpi-median-resolution",
                                    className="text-white",
                                ),
                            ]
                        ),
                        className="bg-dark border-dark",
                    ),
                    md=3,
                    sm=6,
                    className="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("SLA Compliance", className="text-info"),
                                html.H3(
                                    id="kpi-sla-rate",
                                    className="text-white",
                                ),
                            ]
                        ),
                        className="bg-dark border-dark",
                    ),
                    md=3,
                    sm=6,
                    className="mb-3",
                ),
            ],
            className="mb-4",
            justify="center",
        ),

        # SYSTEM SNAPSHOT + TREND/RISK WITH ONE SPINNER
        dbc.Spinner(
        children=html.Div([

            # SYSTEM SNAPSHOT ROW
            dbc.Row(
                [
                    # Left: Volume Breakdown
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H4("Complaint Volume Breakdown", className="text-white mb-3"),
                                    dbc.Tabs(
                                        [
                                            dbc.Tab(label="Category", tab_id="vol-cat", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Department", tab_id="vol-dept", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Neighborhood", tab_id="vol-nbh", labelClassName="text-info-emphasis"),
                                        ],
                                        id="vol-tabs",
                                        active_tab="vol-cat",
                                        className="mb-3 custom-tabs",
                                    ),
                                    html.Div(
                                        dcc.Graph(id="volume-treemap"),
                                        style={"height": "400px"}
                                    ),
                                ]
                            ),
                            className="bg-dark border-dark h-100",
                        ),
                        md=6,
                        className="mb-4",
                    ),

                    # Right: 12-Month Volume Trend
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H4("12-Month Volume Trend", className="text-white mb-3"),
                                    html.Div(
                                        dcc.Graph(id="volume-trend"),
                                        style={"height": "420px"}
                                    ),
                                ]
                            ),
                            className="bg-dark border-dark h-100",
                        ),
                        md=6,
                        className="mb-4",
                    ),
                ]
            ),

            # TREND / RISK CARDS
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H4("Slowest Areas (Resolution Time)", className="text-white mb-3"),
                                    dbc.Tabs(
                                        [
                                            dbc.Tab(label="Department", tab_id="slow-dept", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Category", tab_id="slow-cat", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Neighborhood", tab_id="slow-nbh", labelClassName="text-info-emphasis"),
                                        ],
                                        id="slow-tabs",
                                        active_tab="slow-dept",
                                        className="mb-3 custom-tabs",
                                    ),
                                    html.Div(id="slow-content"),
                                ]
                            ),
                            className="bg-dark border-dark h-100",
                        ),
                        md=6,
                        className="mb-4 d-flex",
                    ),

                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H4("SLA Risk Flags", className="text-white mb-3"),
                                    dbc.Tabs(
                                        [
                                            dbc.Tab(label="Department", tab_id="sla-dept", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Category", tab_id="sla-cat", labelClassName="text-info-emphasis"),
                                            dbc.Tab(label="Neighborhood", tab_id="sla-nbh", labelClassName="text-info-emphasis"),
                                        ],
                                        id="sla-tabs",
                                        active_tab="sla-dept",
                                        className="mb-3 custom-tabs",
                                    ),
                                    html.Div(id="sla-content"),
                                ]
                            ),
                            className="bg-dark border-dark h-100",
                        ),
                        md=6,
                        className="mb-4 d-flex",
                    ),
                ]
            )

        ]),
        color="primary",
        type="grow",
        size="lg",
    ),
    # Data Dictionary Accordion + Modal Trigger
    dbc.Card(
        dbc.CardBody(
            [
                html.H4(
                    "Data Dictionary & Case Types",
                    className="text-white mb-3",
                ),
                dbc.Accordion(
                    [
                        dbc.AccordionItem(
                            [
                                html.P(
                                    "Reference for the main fields used across this dashboard.",
                                    className="text-info",
                                ),
                                html.Div(
                                    build_data_dictionary_table(),
                                    className="mb-3",
                                ),
                                html.Hr(),
                                html.Div(
                                    [
                                        html.H5(
                                            "Browse Case Types by Category",
                                            className="text-info mb-2",
                                        ),
                                        html.P(
                                            "Use the browser below to see which case types belong to each category.",
                                            className="text-white",
                                        ),
                                        dbc.Button(
                                            "Open Case Type Browser",
                                            id="open-case-modal",
                                            color="info",
                                            className="mt-2",
                                        ),
                                    ]
                                ),
                            ],
                            title=html.Span("Data Dictionary", className="text-info"),
                        )
                    ],
                    start_collapsed=True,
                    flush=True,
                ),
            ]
        ),
        className="bg-dark border-dark mb-5",
    ),

        # Modal for Case Types
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Case Types by Category")),
                dbc.ModalBody(
                    [
                        html.Div(
                            [
                                dbc.Label("Select Category:", className="mb-2"),
                                dbc.Select(
                                    id="modal-category-select",
                                    options=category_options,
                                    value=default_category_value,
                                    style={"maxWidth": "400px"},
                                ),
                            ],
                            className="mb-3",
                        ),
                        html.Div(id="modal-case-type-list"),
                    ]
                ),
                dbc.ModalFooter(
                    dbc.Button(
                        "Close",
                        id="close-case-modal",
                        color="info",
                    )
                ),
            ],
            id="case-types-modal",
            is_open=False,
            size="lg",
            scrollable=True,
            backdrop="static",
        ),

        # Home button
        html.Div(
            [
                dbc.Button(
                    "🏠 Home",
                    href="/",
                    color="primary",
                    className="mt-4",
                )
            ],
            style={"textAlign": "center", "marginBottom": "40px"},
        ),
    ],
    fluid=True,
)


# KPI CALLBACK
@callback(
    Output("kpi-total-complaints", "children"),
    Output("kpi-median-resolution", "children"),
    Output("kpi-sla-rate", "children"),
    Output("kpi-avg-month", "children"),
    Input("summary-month-dropdown", "value"),
)
def update_summary_kpis(month):

    row = KPI_MONTHLY[KPI_MONTHLY["MonthName"] == month]

    if row.empty:
        return "0", "—", "—", "—"

    r = row.iloc[0]

    return (
        f"{int(r['Total']):,}",
        f"{r['MedianRes']:.0f}" if pd.notna(r['MedianRes']) else "—",
        f"{r['SLA_Rate']:.1f}%" if pd.notna(r['SLA_Rate']) else "—",
        f"{r['AvgPerMonth']:.0f}" if pd.notna(r['AvgPerMonth']) else "—",
    )


# SLOWEST AREAS
@callback(
    Output("slow-content", "children"),
    Input("slow-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_slowest(active_tab, month):

    table_map = {
        "slow-dept": SLOW_DEPT,
        "slow-cat": SLOW_CAT,
        "slow-nbh": SLOW_NBH,
    }

    df = table_map[active_tab]
    df = df[df["MonthName"] == month]

    if df.empty:
        return empty_table("No data available.")

    df = df.sort_values("MedianDays", ascending=False)

    return make_table(df.head(10), hide_cols=["MonthName"])


# SLA RISK
@callback(
    Output("sla-content", "children"),
    Input("sla-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_sla_risk(active_tab, month):

    table_map = {
        "sla-dept": SLA_DEPT,
        "sla-cat": SLA_CAT,
        "sla-nbh": SLA_NBH,
    }

    df = table_map[active_tab]
    df = df[df["MonthName"] == month]

    if df.empty:
        return empty_table("No SLA data.")

    df = df.sort_values("SLA_Percent")
    df["SLA_Percent"] = df["SLA_Percent"].round(1)

    df2 = df.rename(columns={"SLA_Percent": "SLA %", "CaseCount": "Cases"})

    return make_table(df.head(10), hide_cols=["MonthName"])


# VOLUME TREEMAP
@callback(
    Output("volume-treemap", "figure"),
    Input("vol-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_volume_treemap(tab, month):

    group_map = {
        "vol-cat": "CATEGORY",
        "vol-dept": "DEPARTMENT",
        "vol-nbh": "NEIGHBORHOOD",
    }

    col = group_map.get(tab)
    df = VOLUME_COUNTS[(VOLUME_COUNTS["GroupColumn"] == col) & (VOLUME_COUNTS["MonthName"] == month)]

    if df.empty:
        return empty_figure("No data available")

    fig = px.treemap(
        df, path=["GroupValue"], values="Count",
        color="Count", color_continuous_scale="Plasma"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
    )
    return fig


# VOLUME TREND
@callback(
    Output("volume-trend", "figure"),
    Input("summary-month-dropdown", "value"),
)
def update_volume_trend(_month):

    df = VOLUME_TREND.copy()
    df["Month"] = pd.to_datetime(df["YearMonth"])

    fig = px.line(
        df, x="Month", y="Count",
        markers=True, template="plotly_dark",
        title="Complaint Volume — Last 12 Months"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
    )

    return fig


# CASE TYPE MODAL
@callback(
    Output("modal-case-type-list", "children"),
    Input("modal-category-select", "value"),
)
def update_case_type_list(category):
    if not category:
        return html.P("Select a category.", className="text-muted")

    case_types = CATEGORY_TO_TYPES.get(category)
    if len(case_types) == 0:
        return html.P("No case types found.", className="text-danger")

    return dbc.Card(
        dbc.CardBody([
            html.H6(f"Case Types under '{category}':", className="text-info mb-3"),
            html.Ul([html.Li(ct, style={"color": "#FFF"}) for ct in case_types]),
            html.P(f"Total case types: {len(case_types)}", className="text-info mt-3"),
        ]),
        className="bg-dark border-primary",
    )


@callback(
    Output("case-types-modal", "is_open"),
    Input("open-case-modal", "n_clicks"),
    Input("close-case-modal", "n_clicks"),
    State("case-types-modal", "is_open"),
)
def toggle_case_type_modal(open_clicks, close_clicks, is_open):
    if open_clicks or close_clicks:
        return not is_open
    return is_open