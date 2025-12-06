import dash_bootstrap_components as dbc
from dash import html

def navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Home", href="/")),
            dbc.NavItem(dbc.NavLink("Forecast", href="/forecasts")),
            dbc.DropdownMenu(
                children=[
                    dbc.NavItem(dbc.NavLink("Map", href="/map")),
                    dbc.NavItem(dbc.NavLink("Complaints Over Time", href="/complaints")),
                    dbc.NavItem(dbc.NavLink("Neighborhood Metrics", href="/metrics")),
                    dbc.NavItem(dbc.NavLink("Summary", href="/summary")),
                ],
                nav=True,
                in_navbar=True,
                label="Explore",
            ),
        ],
        brand="311 Dashboard",
        brand_href="/",
        color="primary",
        dark=True,
        sticky="top",
        style={
            "width": "100%",
            "margin": "0",
            "zIndex": "1000"
        }
    )

def footer():
    return dbc.Container([
        dbc.Row([
            dbc.Col(
                html.P([
                    html.Span("Developed by "),
                    html.A("Mojoolu Roberts", href="https://www.linkedin.com/in/mojotr/", 
                        className="text-info", target="_blank"),
                    html.Span(" | Data: "),
                    html.A("houstontx.gov", 
                        href="https://www.houstontx.gov/311/servicerequestdata.html", 
                        className="text-info", target="_blank"),
                    html.Span(" | "), 
                    html.A("Source Code", href="https://github.com/Mojo-TR/311Forecasting", className="text-info", target="_blank")
                ],
                className="text-info text-center mt-4 mb-2",
                style={"fontSize": "0.9rem"})
            )
        ], justify="center")

        # # Tooltips
        # dbc.Tooltip("Visit my GitHub profile", target="tooltip-dev", placement="top"),
        # dbc.Tooltip("Go to the official Houston 311 Open Data Portal", target="tooltip-data", placement="top"),
    ])
