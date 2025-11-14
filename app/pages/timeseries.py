from dash import html, dcc, register_page, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import calendar
from app.data_loader import df

register_page(__name__, path="/complaints", title="Complaints Over Time")

# Ensure date fields exist
df["CREATED DATE"] = pd.to_datetime(df["CREATED DATE"], errors="coerce")
df["Year"] = df["CREATED DATE"].dt.year
df["Month"] = df["CREATED DATE"].dt.month_name()
df["Month & Year"] = df["CREATED DATE"].dt.to_period("M")


neighborhoods = sorted(df["NEIGHBORHOOD"].dropna().unique())
exclude_neighborhood = ["FB CAD #6", "311Cleaning.ipynb"]
filtered_neighborhoods = [n for n in neighborhoods if n not in exclude_neighborhood]

layout = dbc.Container([
    html.H2("Complaint Trends Over Time", className="text-center text-primary mb-4 mt-4"),

    html.Div([
        html.Label("Select Neighborhood:", className="text-white",style={"marginRight": "10px"}),
        dbc.Select(
            id="timeseries-neigh-dropdown",
            options=[{"label": n, "value": n} for n in filtered_neighborhoods],
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
            [
                dbc.CardBody([
                    dcc.Graph(
                        id="timeseries-graph",
                        config={"displayModeBar": False},
                        style={"height": "700px"}
                    )
                ])
            ],
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
    dff = df.copy()
    if selected_neigh:
        dff = dff[dff["NEIGHBORHOOD"] == selected_neigh]

    if dff.empty:
        return px.line(title="No data available for the selected filters.")

    month_order = list(calendar.month_name)[1:]

    if mode == "time":
        counts = (
            dff.groupby("Month & Year")
            .size()
            .reset_index(name="Count")
            .sort_values("Month & Year")
        )
        counts["Month & Year"] = counts["Month & Year"].dt.to_timestamp()
        counts["LineGroup"] = "All"
        x_col = "Month & Year"

        all_months = pd.date_range(counts[x_col].min(), counts[x_col].max(), freq="MS")
        counts = (
            counts.set_index(x_col)
            .reindex(all_months, fill_value=0)
            .reset_index()
            .rename(columns={"index": x_col})
        )
        counts["LineGroup"] = "All"

    else:
        counts = (
            dff.groupby(["Year", "Month"])
            .size()
            .reset_index(name="Count")
        )
        counts["Month"] = pd.Categorical(counts["Month"], categories=month_order, ordered=True)
        counts["LineGroup"] = counts["Year"].astype(str)
        counts = counts.sort_values(["Year", "Month"])
        x_col = "Month"

    fig = px.line(
        counts,
        x=x_col,
        y="Count",
        color="LineGroup",
        line_group="LineGroup",
        markers=True,
        render_mode="webgl",
        title=f"{'Seasonal' if mode=='seasonal' else 'Monthly'} Complaint Trends" +
              (f" ({selected_neigh})" if selected_neigh else ""),
        labels={"Count": "Report Count", x_col: x_col},
        height=700
    )

    if mode == "seasonal":
        fig.update_xaxes(categoryorder="array", categoryarray=month_order)

    scroll_width = 1250

    fig.update_layout(
        plot_bgcolor="#140327",
        paper_bgcolor="#140327",
        font_color="#FFFFFF",
        hovermode="x unified",
        width=scroll_width,
        xaxis_tickangle=-45 if mode == "time" else 0,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=80, b=80)
    )

    return fig