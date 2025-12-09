from dash import html, dcc, register_page, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from app.utils.data_loader import df
from app.utils.utils import make_table, category_to_types

register_page(__name__, path="/summary", title="Summary")


# Helpers for tables
def build_slowest_table(df_in: pd.DataFrame, group_col: str, min_count: int = 20):
    """
    Build a table of the slowest groups by median RESOLUTION_TIME_DAYS.
    """
    if group_col not in df_in.columns:
        return html.P(f"{group_col} column not found.", className="text-muted")

    temp = (
        df_in
        .dropna(subset=["RESOLUTION_TIME_DAYS", group_col])
        .groupby(group_col)["RESOLUTION_TIME_DAYS"]
        .agg(["median", "count"])
        .reset_index()
    )

    temp = temp[temp["count"] >= min_count]
    if temp.empty:
        return html.P(f"Not enough data for {group_col.lower()}.", className="text-muted")

    temp = temp.sort_values("median", ascending=False)
    temp["median"] = temp["median"].round(1)

    temp = temp.rename(
        columns={
            group_col: group_col.title(),
            "median": "Median Days",
            "count": "Cases",
        }
    )

    return make_table(temp.head(10))


def build_sla_risk_table(df_in: pd.DataFrame, group_col: str, min_count: int = 20):
    """
    Build a table showing SLA risk (lowest SLA compliance first).
    """
    if group_col not in df_in.columns:
        return html.P(f"{group_col} column not found.", className="text-muted")

    temp = df_in.dropna(subset=["SLA_DAYS", "RESOLUTION_TIME_DAYS", group_col]).copy()
    if temp.empty:
        return html.P(f"No SLA data for {group_col.lower()}.", className="text-muted")

    temp["WITHIN_SLA"] = temp["RESOLUTION_TIME_DAYS"] <= temp["SLA_DAYS"]

    agg = (
        temp
        .groupby(group_col)
        .agg(
            cases=("RESOLUTION_TIME_DAYS", "size"),
            sla_rate=("WITHIN_SLA", "mean"),
        )
        .reset_index()
    )

    agg = agg[agg["cases"] >= min_count]
    if agg.empty:
        return html.P(
            f"Not enough data for SLA analysis on {group_col.lower()}.",
            className="text-muted",
        )

    agg["SLA %"] = (agg["sla_rate"] * 100).round(1)
    agg = agg.sort_values("SLA %").reset_index(drop=True)

    agg = agg.rename(
        columns={
            group_col: group_col.title(),
            "cases": "Cases",
        }
    ).drop(columns=["sla_rate"])

    return make_table(agg.head(10))

# Month dropdown options
month_options = [{"label": "All Months", "value": "all"}] + [
    {
        "label": m,
        "value": m,
    }
    for m in sorted(
        df["MonthName"].dropna().unique(),
        key=lambda x: pd.to_datetime(x, format="%B").month,
    )
]

# Categories for modal dropdown
if "CATEGORY" in df.columns:
    category_values = sorted(df["CATEGORY"].dropna().unique())
else:
    category_values = []

category_options = [{"label": c, "value": c} for c in category_values]
default_category_value = category_options[0]["value"] if category_options else None

# Data-driven SLA per CATEGORY (80th percentile)
if (
    "CATEGORY" in df.columns
    and "RESOLUTION_TIME_DAYS" in df.columns
    and "SLA_DAYS" not in df.columns
):
    sla_by_category = (
        df
        .dropna(subset=["CATEGORY", "RESOLUTION_TIME_DAYS"])
        .groupby("CATEGORY")["RESOLUTION_TIME_DAYS"]
        .quantile(0.80)
        .round(1)
        .to_dict()
    )
    df["SLA_DAYS"] = df["CATEGORY"].map(sla_by_category)
else:
    # Ensure column exists even if we couldn't compute it
    if "SLA_DAYS" not in df.columns:
        df["SLA_DAYS"] = pd.NA


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
        "field": "TYPE",
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
    {
        "field": "MonthName",
        "type": "string",
        "description": "Month name extracted from CREATED DATE for filtering.",
        "example": "January",
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
                                    className="text-muted",
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
                                            className="text-muted",
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
                            title="Data Dictionary",
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


# Callbacks – KPIs
@callback(
    Output("kpi-total-complaints", "children"),
    Output("kpi-median-resolution", "children"),
    Output("kpi-sla-rate", "children"),
    Output("kpi-avg-month", "children"),
    Input("summary-month-dropdown", "value"),
)
def update_summary_kpis(selected_month):
    filtered = df.copy()

    if selected_month and selected_month != "all":
        filtered = filtered[filtered["MonthName"] == selected_month]

    if filtered.empty or "RESOLUTION_TIME_DAYS" not in filtered.columns:
        return "0", "—", "—", "0"

    # Compute number of distinct months in filtered data
    filtered = filtered.assign(YearMonth=filtered["CREATED DATE"].dt.to_period("M"))
    num_months = filtered["YearMonth"].nunique()

    # Total complaints
    total_complaints = len(filtered)

    if num_months > 0:
        avg_per_month = total_complaints / num_months
        avg_month_text = f"{avg_per_month:,.0f}"
    else:
        avg_month_text = "—"

    # Median resolution
    median_res = filtered["RESOLUTION_TIME_DAYS"].median()
    median_res_text = f"{median_res:.0f}" if pd.notna(median_res) else "—"

    # SLA Metrics (exclude missing SLA)
    valid_sla = filtered.dropna(subset=["SLA_DAYS", "RESOLUTION_TIME_DAYS"])
    if not valid_sla.empty:
        within_sla_mask = (
            valid_sla["RESOLUTION_TIME_DAYS"] <= valid_sla["SLA_DAYS"]
        )
        sla_rate = within_sla_mask.mean() * 100
        sla_rate_text = f"{sla_rate:.1f}%"
    else:
        sla_rate_text = "—"

    return (
        f"{total_complaints:,}",
        median_res_text,
        sla_rate_text,
        avg_month_text,
    )

# Callbacks – Case Types Modal
@callback(
    Output("case-types-modal", "is_open"),
    Input("open-case-modal", "n_clicks"),
    Input("close-case-modal", "n_clicks"),
    State("case-types-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_case_types_modal(open_clicks, close_clicks, is_open):
    open_clicks = open_clicks or 0
    close_clicks = close_clicks or 0

    # Simple deterministic rule: open if opens > closes
    return open_clicks > close_clicks


@callback(
    Output("modal-case-type-list", "children"),
    Input("modal-category-select", "value"),
)
def update_case_type_list(selected_category):
    if not selected_category:
        return html.P(
            "Select a category to view its case types.",
            className="text-muted",
        )

    case_types = category_to_types.get(selected_category, [])
    if not case_types:
        return html.P(
            "No case types found for this category.",
            className="text-muted",
        )

    case_types_sorted = sorted(case_types)

    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(
                    f"Case Types under '{selected_category}':",
                    className="text-info mb-3",
                ),
                html.Ul(
                    [
                        html.Li(
                            ct,
                            style={"color": "#FFF"},
                        )
                        for ct in case_types_sorted
                    ]
                ),
                html.P(
                    f"Total case types: {len(case_types_sorted)}",
                    className="text-muted mt-3",
                ),
            ]
        ),
        className="bg-dark border-info",
    )


# Callbacks – Slowest areas & SLA risk
@callback(
    Output("slow-content", "children"),
    Input("slow-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_slowest_panel(active_tab, selected_month):
    filtered = df.copy()
    if selected_month != "all":
        filtered = filtered[filtered["MonthName"] == selected_month]

    if active_tab == "slow-cat":
        return build_slowest_table(filtered, "CATEGORY", min_count=30)
    if active_tab == "slow-nbh":
        return build_slowest_table(filtered, "NEIGHBORHOOD", min_count=20)
    if active_tab == "slow-dept":
        return build_slowest_table(filtered, "DEPARTMENT", min_count=20)

    return html.P("Invalid tab selected.", className="text-muted")


@callback(
    Output("sla-content", "children"),
    Input("sla-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_sla_panel(active_tab, selected_month):
    filtered = df.copy()
    if selected_month != "all":
        filtered = filtered[filtered["MonthName"] == selected_month]

    if active_tab == "sla-dept":
        return build_sla_risk_table(filtered, "DEPARTMENT")
    if active_tab == "sla-cat":
        return build_sla_risk_table(filtered, "CATEGORY")
    if active_tab == "sla-nbh":
        return build_sla_risk_table(filtered, "NEIGHBORHOOD")

    return html.P("Invalid tab selected.", className="text-muted")

# Callbacks – Volume treemap & trend
@callback(
    Output("volume-treemap", "figure"),
    Input("vol-tabs", "active_tab"),
    Input("summary-month-dropdown", "value"),
)
def update_volume_treemap(active_tab, selected_month):
    # Safety check
    if df.empty:
        return px.treemap(title="No data available")

    filtered = df.copy()

    if selected_month != "all":
        filtered = filtered[filtered["MonthName"] == selected_month]

    group_map = {
        "vol-cat": "CATEGORY",
        "vol-dept": "DEPARTMENT",
        "vol-nbh": "NEIGHBORHOOD",
    }

    group_col = group_map.get(active_tab, "CATEGORY")

    # Column missing → safe empty fig
    if group_col not in filtered.columns:
        return px.treemap(
            pd.DataFrame({"Label": ["No data"], "Count": [1]}),
            path=["Label"],
            values="Count",
            title="No data available",
        )

    # Build clean count df — NO rename collisions
    count_df = (
        filtered[group_col]
        .dropna()
        .value_counts()
        .rename_axis(group_col)
        .reset_index(name="Count")
    )

    if count_df.empty:
        return px.treemap(
            pd.DataFrame({"Label": ["No data"], "Count": [1]}),
            path=["Label"],
            values="Count",
            title="No data available",
        )

    fig = px.treemap(
        count_df,
        path=[group_col],
        values="Count",
        color="Count",
        color_continuous_scale="Plasma",
        title=f"Volume by {group_col.title()}",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#140327",
        font_color="white",
        margin=dict(t=40, l=0, r=0, b=0),
    )

    return fig

@callback(
    Output("volume-trend", "figure"),
    Input("summary-month-dropdown", "value"),
)
def update_volume_trend(_selected_month):
    if "CREATED DATE" not in df.columns or df["CREATED DATE"].dropna().empty:
        return px.line(title="No data available")

    filtered = df.copy()
    filtered = filtered.assign(YearMonth=filtered["CREATED DATE"].dt.to_period("M"))

    month_counts = (
        filtered.groupby("YearMonth")
        .size()
        .reset_index(name="Count")
        .sort_values("YearMonth")
    )

    if month_counts.empty:
        return px.line(title="No data available")

    last_12 = month_counts.tail(12)
    last_12["YearMonth"] = last_12["YearMonth"].astype(str)

    fig = px.line(
        last_12,
        x="YearMonth",
        y="Count",
        markers=True,
        template="plotly_dark",
        title="Complaint Volume — Last 12 Months",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis_title="Month",
        yaxis_title="Complaints",
    )

    return fig