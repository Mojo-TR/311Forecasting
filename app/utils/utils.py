from dash import html
import dash_bootstrap_components as dbc


def make_table(df, col_rename=None):
    """Create a consistent Bootstrap dark table dynamically from any DataFrame."""
    if df.empty:
        return dbc.Alert("No data available.", color="warning")

    # Rename columns if dictionary provided
    if col_rename:
        df = df.rename(columns=col_rename)

    return dbc.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th(col, style={
                        "backgroundColor": "var(--bs-primary)",
                        "color": "white",
                        "whiteSpace": "nowrap"
                    }) for col in df.columns
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(df.iloc[i, j]) for j in range(len(df.columns))
                ]) for i in range(len(df))
            ])
        ],
        bordered=False,
        striped=True,
        hover=True,
        size="sm",
        className="table-dark text-white",
        style={"tableLayout": "fixed"}
    )



