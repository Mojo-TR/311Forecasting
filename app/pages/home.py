from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
from dash import Input, Output, callback
import pandas as pd
from app.data_loader import df
import plotly.express as px
from datetime import datetime
from app.components.utils import make_table
from app.forecast_loader import start_forecast_thread, get_home_forecast_summary, forecast_ready

register_page(__name__, path="/")

# Start background forecast thread
start_forecast_thread()

# Get current month as string, e.g. "November 2025"
current_month = datetime.now().strftime("%B %Y")

# total months
total_months = df["CREATED DATE"].dt.to_period("M").nunique()

#total neighborhoods
total_neighborhoods = df["NEIGHBORHOOD"].nunique() if "NEIGHBORHOOD" in df.columns else 0

# Total complaints
total_complaints = len(df)

# Average complaints per month
avg_per_month = df.groupby(df["CREATED DATE"].dt.to_period("M")).size().mean() if "CREATED DATE" in df.columns else None

# Average complaints per neighborhood
avg_per_neighborhood = df.groupby("NEIGHBORHOOD").size().mean() if "NEIGHBORHOOD" in df.columns else None

# Average complaints per department
avg_per_department = df.groupby("DEPARTMENT").size().mean() if "DEPARTMENT" in df.columns else None

# Average complaints per division
avg_per_division = df.groupby("DIVISION").size().mean() if "DIVISION" in df.columns else None

# Average complaints per category
avg_per_category = df.groupby("CATEGORY").size().mean() if "CATEGORY" in df.columns else None

# Resolution Times
avg_resolution_days = df["RESOLUTION_TIME_DAYS"].mean()
median_resolution_days = df["RESOLUTION_TIME_DAYS"].median()

# Create time series figure
monthly_trend = (
    df.groupby(df["CREATED DATE"].dt.to_period("M"))
    .size()
    .reset_index(name="Count")
)
monthly_trend["CREATED DATE"] = monthly_trend["CREATED DATE"].astype(str)

trend_fig = px.line(
    monthly_trend,
    x="CREATED DATE",
    y="Count",
    markers=True,
    template="plotly_dark"
)
trend_fig.update_layout(
    paper_bgcolor="#140327",
    plot_bgcolor="#140327",
    font_color="#FFF",
    xaxis_title="Date",
    margin=dict(l=0, r=0, t=40, b=0),
)

top_5_cache = {}
for col in ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY"]:
    if col in df.columns:
        top_5_cache[col] = df[col].value_counts().head(5).reset_index()
        top_5_cache[col].columns = [col, "Complaints"]

card_style = {"height": "100px"} 

layout = dbc.Container([

    html.H1("Houston 311 Complaints Dashboard", className="text-center text-primary mb-4 mt-3"),

    dbc.Card([
                dbc.CardBody(
                [
                    html.H4("This Month’s Forecast", className="card-title text-primary no-glow fw-bold"),
                    html.Div(
                        id="forecast-summary",
                        className="fs-5 text-white fw-semibold mb-3",
                    ),
                    dbc.Button("View Full Forecast →", href="/forecasts", color="primary", className="w-100"),
                ]
            ),
        ],
        className="bg-dark text-light border-dark mb-4",
        style={"maxWidth": "100%", "width": "22rem", "margin": "auto"},
    ),

    html.H5("Select what you want to explore:", className="text-center text-white mb-3"),

    dbc.Row([
        dbc.Col(dbc.Button("Map", color="primary", href="/map", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Complaints Over Time", color="primary", href="/complaints", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Neighborhood Metrics", color="primary", href="/metrics", size="lg", className="w-100"), width=3),
        dbc.Col(dbc.Button("Summary", color="primary", href="/summary", size="lg", className="w-100"), width=3),
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

                # "See More" link directly under the card
                html.Nav(
                    html.Ol([
                        html.Li(
                            html.A(
                                "See More",
                                href="/summary",
                                className="text-decoration-none text-primary"
                            ),
                            className="breadcrumb-item active"
                        )
                    ], className="breadcrumb mb-0"),
                    style={"marginTop": "5px", "textAlign": "center"}
                )
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
                            href="/complaints-over-time", 
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
                        html.Div(id="top-table-container"),
                    ),
                    className="card bg-dark border-dark mb-2"
                ),
                html.Nav(
                    html.Ol([
                            html.Li(
                                html.A(
                                    "See More",
                                    href="/metrics",
                                    className="text-decoration-none text-primary"
                                ),
                                className="breadcrumb-item active"
                            )],className="breadcrumb mb-0"
                    ),
                )],width=6
        )],justify="center",
    className="mb-5"
),

])
# --- Callback for Top 5 Summary ---
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
        return make_table(df_top)
    else:
        return dbc.Alert("No data available for this selection.", color="warning")

@callback(
    Output("forecast-summary", "children"),
    Input("interval-refresh", "n_intervals")
)
def update_forecast_summary(_):
    return get_home_forecast_summary()
