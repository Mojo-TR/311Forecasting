from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
from dash import Input, Output, callback
import pandas as pd
from app.utils.data_loader import df
import plotly.express as px
from datetime import datetime
from app.utils.utils import make_table, empty_figure
from app.utils.forecast_loader import get_home_forecast_summary

register_page(__name__, path="/")

def safe_stat(func, default=None):
    """Run a stat function safely. 
    If anything fails, return the default value.
    """
    try:
        return func()
    except Exception:
        return default

# DATE HELPERS
now = datetime.now()
current_month_period = now.strftime("%Y-%m")
yesterday = (now - pd.Timedelta(days=1)).date()

# Start background forecast thread
summary_text = get_home_forecast_summary()

# Get current month as string
current_month = datetime.now().strftime("%B %Y")

# Cases in the current month
current_month_period = datetime.now().strftime("%Y-%m")
try:
    cases_this_month = df[df["CREATED DATE"].dt.to_period("M") == current_month_period].shape[0]
except Exception:
    cases_this_month = None

cases_yesterday = safe_stat(
    lambda: df[df["CREATED DATE"].dt.date == yesterday].shape[0],
    default=None
)

total_months = safe_stat(
    lambda: df["CREATED DATE"].dt.to_period("M").nunique(),
    default=None
)

total_neighborhoods = safe_stat(
    lambda: df["NEIGHBORHOOD"].nunique(),
    default=None
)

total_complaints = safe_stat(
    lambda: len(df),
    default=None
)

avg_per_month = safe_stat(
    lambda: df.groupby(df["CREATED DATE"].dt.to_period("M")).size().mean(),
    default=None
)

avg_per_neighborhood = safe_stat(
    lambda: df.groupby("NEIGHBORHOOD").size().mean(),
    default=None
)

avg_per_department = safe_stat(
    lambda: df.groupby("DEPARTMENT").size().mean(),
    default=None
)

avg_per_division = safe_stat(
    lambda: df.groupby("DIVISION").size().mean(),
    default=None
)

avg_per_category = safe_stat(
    lambda: df.groupby("CATEGORY").size().mean(),
    default=None
)

avg_resolution_days = safe_stat(
    lambda: df["RESOLUTION_TIME_DAYS"].mean(),
    default=None
)

median_resolution_days = safe_stat(
    lambda: df["RESOLUTION_TIME_DAYS"].median(),
    default=None
)

# Create time series figure
monthly_trend = (
    df.groupby(df["CREATED DATE"].dt.to_period("M"))
    .size()
    .reset_index(name="Count")
)
monthly_trend["CREATED DATE"] = monthly_trend["CREATED DATE"].astype(str)

if monthly_trend.empty:
    trend_fig = empty_figure("No time-series data available")
else:
    trend_fig = px.line(
        monthly_trend,
        x="CREATED DATE",
        y="Count",
        markers=True,
        template="plotly_dark"
    )
    
    trend_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        xaxis_title="Month",
        yaxis_title="Complaints",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    trend_fig.update_traces(
        hovertemplate=
            "<b>Month:</b> %{x}<br>" +
            "<b>Requests:</b> %{y:,}<extra></extra>"
    )


top_5_cache = {}
for col in ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY"]:
    if col in df.columns:
        top_5_cache[col] = df[col].value_counts().head(5).reset_index()
        top_5_cache[col].columns = [col, "Complaints"]

card_style = {"height": "100px"} 

layout = dbc.Container([

    html.H1("Houston 311 Complaints Dashboard", className="text-center text-primary mb-4 mt-3"),

    dbc.Row([
        # Cases Yesterday
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Yesterday's Reports", className="card-title text-primary no-glow fw-bold"),
                    html.H2(
                        f"{cases_yesterday:,}" if cases_yesterday is not None else "N/A",
                        className="text-white fw-bold"
                    ),
                    dbc.Button("View Complaints →", href="/complaint-trends", color="primary", className="mt-2 w-100")
                ])
            ], className="bg-dark text-light border-dark mb-4"),
            width=3
        ),
        
        # Cases This Month
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Cases This Month", className="card-title text-primary no-glow fw-bold"),
                    html.H2(f"{cases_this_month:,}", className="text-white fw-bold"),
                    dbc.Button("View Complaints →", href="/complaint-trends", color="primary", className="mt-2 w-100")
                ])
            ], className="bg-dark text-light border-dark mb-4"),
            width=3
        ),

        # Forecast Card
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("This Month's Forecast", className="card-title text-primary no-glow fw-bold"),
                        dbc.Spinner(
                            html.H2(id="forecast-summary", className="text-white fw-semibold mb-3"),
                            color="primary", type="grow", size="sm"
                        ),
                    dbc.Button("View Full Forecast →", href="/forecasts", color="primary", className="w-100"),
                ])
            ], className="bg-dark text-light border-dark mb-4"),
            width=3
        ),
    ],
    justify="center",
    className="mb-4"),


    html.H5("Select what you want to explore:", className="text-center text-white mb-3"),

    dbc.Row([
        dbc.Col(dbc.Button("Map", color="primary", href="/map", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Complaint Trends", color="primary", href="/complaint-trends", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Neighborhood Metrics", color="primary", href="/neighborhood-metrics", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Resolution Insights", color="primary", href="/resolution-insights", size="lg", className="w-100"), width=3),
    ], justify="center", className="mb-4"),

    dcc.Interval(id="interval-refresh", interval=5000, n_intervals=0),

    html.H5("Summary Statistics", className="text-center text-white"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Complaints", className="card-title"),
                    html.H2(f"{total_complaints:,}", className="card-text text-info")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Months", className="card-title"),
                    html.H2(f"{total_months:,}", className="card-text text-info")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Neighborhoods", className="card-title"),
                    html.H2(f"{total_neighborhoods:,}", className="card-text text-info")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
    ], justify="center", className="mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg Complaints / Month", className="card-title"),
                    html.H2(f"{avg_per_month:,.0f}", className="card-text text-warning")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg / Neighborhood", className="card-title"),
                    html.H2(f"{avg_per_neighborhood:,.0f}", className="card-text text-warning")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
    ], justify="center", className="mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg / Department", className="card-title"),
                    html.H2(f"{avg_per_department:,.0f}", className="card-text text-danger")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg / Division", className="card-title"),
                    html.H2(f"{avg_per_division:,.0f}", className="card-text text-danger")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg / Category", className="card-title"),
                    html.H2(f"{avg_per_category:,.0f}", className="card-text text-danger")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
    ], justify="center", className="mb-4"),

    dbc.Row([
        dbc.Col(
            [
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Avg Resolution Time", className="card-title"),
                        html.H2(f"{avg_resolution_days:,.0f} Days", className="card-text text-success")
                    ])
                ], color="dark", outline=True, style=card_style),
            ],
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Median Resolution Time", className="card-title"),
                    html.H2(f"{median_resolution_days:,.0f} Days", className="card-text text-success")
                ])
            ], color="dark", outline=True, style=card_style),
            width=3
        ),
    ], justify="center", className="mb-5"),

    html.H5("Complaints Over Time", className="text-center text-white"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(figure=trend_fig, config={"displayModeBar": False})
                ])
            ], className="card bg-dark border-dark mb-3"),
            
            html.Nav(
                html.Ol([
                    html.Li(
                        html.A(
                            "See More", 
                            href="/complaint-trends", 
                            className="text-decoration-none text-primary"
                        ), 
                        className="breadcrumb-item active"
                    )
                ], className="breadcrumb mb-0"),
                style={"marginTop": "5px"}
            ),
        ])
    ], justify="center", className="mb-5"),
    
    html.H5("Top 5 Summary", className="text-center text-white mb-2"),
    
    dbc.Row([
        dbc.Col(
            dbc.RadioItems(
                id="summary-scope",
                options=[
                    {"label": "Neighborhood", "value": "neighborhood"},
                    {"label": "Department", "value": "department"},
                    {"label": "Division", "value": "division"},
                    {"label": "Category", "value": "category"},
                ],
                value="neighborhood",
                inline=True,
                className="btn-group mb-4 d-flex justify-content-center",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary",
                labelCheckedClassName="active",
            ),
            width="auto"
        )
    ], justify="center"),
    
    dbc.Row(
    [
        dbc.Col([
                dbc.Card(
                    dbc.CardBody(
                        dbc.Spinner(
                            html.Div(id="top-table-container"),
                            color="primary",
                            type="grow",
                            size="sm"
                        ),
                    ),
                    className="card bg-dark border-dark mb-2"
                ),
                html.Nav(
                    html.Ol([
                            html.Li(
                                html.A(
                                    "See More",
                                    href="/neighborhood-metrics",
                                    className="text-decoration-none text-primary"
                                ),
                                className="breadcrumb-item active"
                            )],className="breadcrumb mb-0"
                    ),
                )],width=6
        )],justify="center",
    className="mb-5"
    ),
    
    # Summary Page Quick Link
    html.H5("Explore Detailed Summary", className="text-center text-white mt-4"),

    dbc.Row([
        dbc.Col(
            dbc.Button(
                "Go to Summary →",
                href="/summary",
                color="info",
                size="lg",
                className="w-150 d-block mx-auto"
            ),
            width="auto"
        )
    ], className="mb-5", justify="center"),

])
# Callback for Top 5 Summary
@callback(
    Output("top-table-container", "children"),
    Input("summary-scope", "value")
)
def update_top_5(scope):
    # Map radio value to actual column name
    scope_map = {
        "neighborhood": "NEIGHBORHOOD",
        "department": "DEPARTMENT",
        "division": "DIVISION",
        "category": "CATEGORY",
    }
    col = scope_map.get(scope)

    # Get cached top 5 table
    if col in top_5_cache:
        df_top = top_5_cache[col]

        if df_top.empty:
            return dbc.Alert("No records found.", color="warning")

        try:
            return make_table(df_top, col_rename={col: col.title()})
        except Exception:
            return dbc.Alert("Failed to load table.", color="danger")

@callback(
    Output("forecast-summary", "children"),
    Input("interval-refresh", "n_intervals")
)
def update_forecast_summary(_):
    return get_home_forecast_summary()