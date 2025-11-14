from dash import html, dcc
import dash_bootstrap_components as dbc
from app.components.items import navbar, footer
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

app.layout = dbc.Container([
    navbar(),
    dash.page_container,
    footer()
])

if __name__ == "__main__":
    app.run(debug=True)