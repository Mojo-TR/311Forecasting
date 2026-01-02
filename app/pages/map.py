from dash import html, dcc, register_page, Output, Input, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from app.utils.data_loader import df
from app.utils.utils import empty_map

register_page(__name__, path="/map", title="Map")

# Load data=
df["MonthName"] = df["CREATED DATE"].dt.month_name()

# Create dropdown options
year_options = [
    {"label": str(y), "value": str(y)}
    for y in sorted(df["Year"].dropna().unique())
]

month_options = [{"label": "All Months", "value": "all"}] + \
                [{"label": m, "value": m} for m in df["MonthName"].unique()]

color_options = [
    {"label": "Department", "value": "DEPARTMENT"},
    {"label": "Division", "value": "DIVISION"},
    {"label": "Category", "value": "CATEGORY"},
    {"label": "Resolution Time (days)", "value": "RESOLUTION_TIME_DAYS"}
]

# Default value = most recent year
default_year = str(df["Year"].dropna().max())
default_month = "all"

# Base map
initial_df = df[df["Year"] == int(default_year)]
fig = px.scatter_map(
    initial_df.sample(min(1000, len(initial_df))),
    lat="LATITUDE",
    lon="LONGITUDE",
    color="DEPARTMENT",
    map_style="carto-darkmatter",
    zoom=9,
    title=f"311 Complaint Hotspots ({default_year})",
)
fig.update_layout(height=700, paper_bgcolor="#181818", font_color="#FFFFFF")

# Layout
def layout():
    return html.Div([
        html.H2("Complaint Locations in Houston", className="text-center text-primary mb-4 mt-4"),
        
        dbc.Row([
            dbc.Col(
                [
                    html.Label("Select Year:", className="text-white me-2"),
                    dbc.Select(
                        id="map-year-dropdown",
                        options=year_options,
                        value=default_year,
                        style={"width": "300px"}
                    ),
                ],
                width="auto"
            ),
            dbc.Col(
                [
                    html.Label("Select Month:", className="text-white me-2"),
                    dbc.Select(
                        id="month-dropdown",
                        options=month_options,
                        value=default_month,
                        style={"width": "300px"}
                    ),
                ],
                width="auto"
            ),
            dbc.Col(
                [
                    html.Label("Color By:", className="text-white me-2"),
                    dbc.Select(
                        id="color-dropdown",
                        options=color_options,
                        value="DEPARTMENT",  # default
                        style={"width": "250px"}
                    ),
                ],
                width="auto"
            )
        ],
        justify="center",
        className="mb-4"
    ),

        html.Div(
            dbc.Spinner(
                dcc.Graph(id="map-graph", figure=fig),
                color="primary",
                type="grow",
                size="lg"
            ),
            className="card bg-dark border-dark mb-3"
        ),
        
        # Home button at the bottom
        html.Div([
            dbc.Button("🏠 Home", href="/", color="primary", className="mt-4")
        ], style={"textAlign": "center"})
    ])

@callback(
    Output("map-graph", "figure"),
    Input("map-year-dropdown", "value"),
    Input("month-dropdown", "value"),
    Input("color-dropdown", "value")
)
def update_map(selected_year, selected_month, selected_color):

    # SAFETY: missing input
    if not selected_year:
        return empty_map("No year selected")

    # Filter by year
    try:
        dff = df[df["Year"] == int(selected_year)]
    except Exception:
        return empty_map("Invalid year format")

    # Filter by month
    if selected_month and selected_month != "all":
        dff = dff[dff["MonthName"] == selected_month]

    # No rows at all
    if dff.empty:
        return empty_map("No complaint data for these filters")

    # Drop null coordinates
    dff = dff.dropna(subset=["LATITUDE", "LONGITUDE"])
    if dff.empty:
        return empty_map("No valid coordinates available for these filters")

    # Limit dataset for performance
    if len(dff) > 2000:
        dff = dff.sample(2000, random_state=42)

    # Determine coloring
    if selected_color == "RESOLUTION_TIME_DAYS":
        color_arg = "RESOLUTION_TIME_DAYS"
        color_scale = "Plasma"
    else:
        color_arg = selected_color
        color_scale = None

    # Ensure required columns exist
    required_columns = ["LATITUDE", "LONGITUDE", color_arg]
    for col in required_columns:
        if col not in dff.columns:
            return empty_map(f"Missing column: {col}")

    # Try to build the map
    try:
        fig = px.scatter_map(
            dff,
            lat="LATITUDE",
            lon="LONGITUDE",
            color=color_arg,
            color_continuous_scale=color_scale,
            hover_name="CATEGORY",
            hover_data={
                "NEIGHBORHOOD": True,
                "DEPARTMENT": True,
                "DIVISION": True,
                "CATEGORY": True,
                "RESOLUTION_TIME_DAYS": ":.0f",
                "LATITUDE": False,
                "LONGITUDE": False
            },
            map_style="carto-darkmatter",
            zoom=9,
            title=f"311 Complaint Hotspots ({selected_year})"
        )
    except Exception:
        return empty_map("Unable to render map with the selected fields")

    # Final styling
    fig.update_layout(
        height=700,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FFFFFF",
    )

    return fig