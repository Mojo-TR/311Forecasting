import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from app.utils.items import navbar, footer
from app.utils.forecast_loader import start_forecast_thread

import logging
logger = logging.getLogger('cmdstanpy')
logger.addHandler(logging.NullHandler())
logger.propagate = False
logger.setLevel(logging.CRITICAL)

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.VAPOR]
)

start_forecast_thread()

app.layout = dbc.Container([
    navbar(),
    dash.page_container,
    footer()
])

if __name__ == "__main__":
    app.run(debug=True)