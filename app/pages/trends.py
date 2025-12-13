from dash import html, dcc, register_page, callback, Output, Input
import pandas as pd
import plotly.express as px
import calendar
import dash_bootstrap_components as dbc
from app.utils.utils import empty_figure

register_page(__name__, path="/complaint-trends", title="Complaints Over Time")

# Load unified precomputed time series files
BASE_PATH = "precomputed_data/trends/"

MONTHLY_ALL = pd.read_parquet(f"{BASE_PATH}monthly_all.parquet")
SEASONAL_ALL = pd.read_parquet(f"{BASE_PATH}seasonal_all.parquet")

NEIGH_LIST = (
    pd.read_parquet(f"{BASE_PATH}neighborhoods_cleaned.parquet")
    .iloc[:, 0]
    .tolist()
)

month_order = list(calendar.month_name)[1:]

layout = dbc.Container([
    html.H2("Complaint Trends Over Time", className="text-center text-primary mb-4 mt-4"),

    html.Div([
        html.Label("Select Neighborhood:", className="text-white",style={"marginRight": "10px"}),
        dbc.Select(
            id="timeseries-neigh-dropdown",
            options=[{"label": n, "value": n} for n in NEIGH_LIST],
            value=None,
            placeholder="All Neighborhoods",
            style={"width": "300px"}
        )

    ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),

    dbc.Row(
        [
            dbc.Col(
                dbc.RadioItems(
                    id="timeseries-mode",
                    options=[
                        {"label": "Monthly", "value": "time"},
                        {"label": "Seasonal", "value": "seasonal"},
                    ],
                    value="time",
                    inline=True,
                    className="mb-4",
                    inputClassName="btn-check",
                    labelClassName="btn btn-outline-primary",
                    labelCheckedClassName="active",
                ),
                width="auto",  # shrink to fit content
                style={"textAlign": "center"},
            )
        ],
        justify="center",
        style={"marginBottom": "20px"},
    ),


    html.Div(
        dbc.Card(
            dbc.CardBody([
                dbc.Spinner(
                    dcc.Graph(
                        id="timeseries-graph",
                        config={"displayModeBar": False},
                        style={"height": "700px"}
                    ),
                    type="grow", 
                    color="primary",
                    size="lg",
                )
            ]),
            className="bg-dark border-dark mb-3",
            style={
                "overflowX": "auto",
                "whiteSpace": "nowrap",
                "width": "100%",
                "scrollbarColor": "#444 #181818",
                "scrollbarWidth": "thin"
            }
        )
    ),
    
    # Home button at the bottom
    html.Div([
        dbc.Button("🏠 Home", href="/", color="primary", class_name="mt-5")
    ], style={"textAlign": "center"})
])

@callback(
    Output("timeseries-graph", "figure"),
    Input("timeseries-neigh-dropdown", "value"),
    Input("timeseries-mode", "value")
)
def update_timeseries(selected_neigh, mode):

    # Select correct dataset
    if mode == "time":
        dff = MONTHLY_ALL.copy()
        x_col = "Month_Year"
        title = "Monthly Complaint Trends"
    else:
        dff = SEASONAL_ALL.copy()
        x_col = "Month"
        title = "Seasonal Complaint Trends"

    # Neighborhood filter
    if selected_neigh:
        dff = dff[dff["NEIGHBORHOOD"] == selected_neigh]
    else:
        dff = dff[dff["Level"] == "city"]

    if dff.empty:
        return empty_figure("No data available.")

    # Seasonal mode: enforce month ordering + year grouping
    if mode != "time":
        dff = dff.sort_values(["Year", "MonthNum"])
        dff["Month"] = pd.Categorical(
            dff["Month"],
            categories=list(calendar.month_name)[1:],  # Jan → Dec
            ordered=True
        )
        dff["LineGroup"] = dff["Year"].astype(str)
    else:
        dff["LineGroup"] = "All"

    # Build figure
    fig = px.line(
        dff,
        x=x_col,
        y="Count",
        color="LineGroup",
        markers=True,
        render_mode="webgl",
        template="plotly_dark",
        title=title + (f" — {selected_neigh}" if selected_neigh else ""),
        labels={"Count": "Report Count"},
        height=700,
    )

    # Final styling
    fig.update_layout(
        hovermode="x unified",
        xaxis_tickangle=-45,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=80, b=80),
        width=1250,
    )

    return fig