from __future__ import annotations

from urllib.parse import urlencode, parse_qs

import dash
from dash import dcc, html, Input, Output, State, callback
from plotly.graph_objects import Figure

from config import DEF_PARQUET
from data_loader import load_dataframe, prepare_map_data, month_options, latest_month_idx
from utils import (
    pie_counts_for_month,
    waffle_counts_for_month,
    find_country_row,
    categorize_prob_single,
    categorize_band_single,
    read_model_details,
)
from figures.map_figure import make_world_map
from figures.pie_figure import make_pie
from figures.waffle_figure import make_waffle

# Load once per process
_df = load_dataframe(DEF_PARQUET)
_map_data = prepare_map_data(_df)
_month_opts = month_options(_df)
_latest_idx = latest_month_idx(_df)

# ---------- Page layouts ----------

def _map_page_layout() -> html.Div:
    return html.Div(
        [
            html.H1(
                "FAST-cm Conflict Forecast — World Map",
                style={"textAlign": "center", "color": "#333", "marginBottom": "20px"},
            ),
            dcc.Graph(id="world-map", figure=make_world_map(_map_data), config={"displayModeBar": True}),
            html.Div(
                "Tip: Click a country to open the full detail page.",
                style={"textAlign": "center", "color": "#666"},
            ),
        ]
    )

def _country_page_layout(iso3: str, query_month: int | None) -> html.Div:
    country_name = _df.loc[_df["isoab"].str.upper() == iso3.upper(), "name"].head(1)
    display_name = country_name.iloc[0] if not country_name.empty else iso3.upper()
    default_month = query_month if query_month is not None else _latest_idx
    model_md = read_model_details()

    return html.Div(
        [
            html.Div(
                [
                    html.H2(f"{display_name} ({iso3.upper()}) — Detail View", style={"margin": 0, "color": "#333"}),
                    html.Div(dcc.Link("← Back to map", href="/"), style={"marginTop": "4px", "color": "#555"}),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "2px", "marginBottom": "12px"},
            ),
            html.Div(
                [
                    html.Div("Select month:", style={"fontWeight": 600, "marginRight": "8px"}),
                    dcc.Dropdown(
                        id="month-dropdown",
                        options=_month_opts,
                        value=default_month,
                        clearable=False,
                        searchable=False,
                        style={"width": "240px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "10px"},
            ),
            html.Div(
                [
                    html.Button(
                        "Model details and selection criteria",
                        id="details-toggle",
                        n_clicks=0,
                        **{"aria-controls": "details-panel", "aria-expanded": "false"},
                        style={
                            "padding": "8px 12px",
                            "borderRadius": "8px",
                            "border": "1px solid #dee2e6",
                            "backgroundColor": "#f8f9fa",
                            "cursor": "pointer",
                            "fontWeight": 600,
                        },
                    ),
                    html.Div(
                        id="details-panel",
                        role="region",
                        **{"aria-label": "Model details and selection criteria"},
                        style={
                            "display": "none",
                            "marginTop": "8px",
                            "padding": "12px",
                            "border": "1px solid #e9ecef",
                            "borderRadius": "8px",
                            "backgroundColor": "#fcfcfd",
                            "maxHeight": "50vh",
                            "overflowY": "auto",
                        },
                        children=[
                            html.Div(
                                "×",
                                id="details-close",
                                title="Close",
                                style={"position": "sticky", "top": 0, "float": "right", "cursor": "pointer", "fontSize": "20px", "color": "#666"},
                            ),
                            dcc.Markdown(model_md),
                        ],
                    ),
                ],
                style={"marginBottom": "10px"},
            ),
            html.Div(
                id="info-strip",
                style={
                    "backgroundColor": "#f8f9fa",
                    "border": "1px solid #e9ecef",
                    "borderRadius": "8px",
                    "padding": "10px 12px",
                    "marginBottom": "10px",
                    "color": "#333",
                    "fontSize": "14px",
                },
            ),
            html.Div(
                [
                    dcc.Graph(id="pie-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                    dcc.Graph(id="waffle-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                ],
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
            ),
        ]
    )

# ---------- Router ----------

@callback(Output("page-content", "children"), Input("url", "pathname"), State("url", "search"))
def route(pathname, search):
    if pathname is None or pathname == "/":
        return _map_page_layout()

    parts = [p for p in (pathname or "").split("/") if p]
    if len(parts) == 2 and parts[0] == "country":
        iso3 = parts[1]
        q = parse_qs((search or "")[1:], keep_blank_values=True) if search else {}
        month_idx = None
        if "month" in q:
            try:
                month_idx = int(q["month"][0])
            except Exception:
                month_idx = None
        return _country_page_layout(iso3, month_idx)

    return html.Div(
        [html.H2("Page not found"), dcc.Link("Go to map", href="/")],
        style={"textAlign": "center", "padding": "40px"},
    )

# ---------- Map click → navigate to /country/ISO3?month=<latest> ----------

@callback(Output("url", "href"), Input("world-map", "clickData"), prevent_initial_call=True)
def on_map_click(clickData):
    if not clickData:
        return dash.no_update
    iso3 = clickData["points"][0]["location"]
    query = urlencode({"month": _latest_idx})
    return f"/country/{iso3}?{query}"

# ---------- Country page computations → figures + info ----------

@callback(
    Output("pie-fig", "figure"),
    Output("waffle-fig", "figure"),
    Output("info-strip", "children"),
    Input("month-dropdown", "value"),
    Input("url", "pathname"),
)
def update_country_figures(month_idx, pathname):
    # Must be on /country/<ISO3>
    parts = [p for p in (pathname or "").split("/") if p]
    if len(parts) != 2 or parts[0] != "country":
        return Figure(), Figure(), dash.no_update

    iso3 = parts[1].upper()

    # Month guard: if missing/invalid, fall back to latest
    try:
        month_idx_int = int(month_idx) if month_idx is not None else _latest_idx
    except Exception:
        month_idx_int = _latest_idx

    # If the month doesn’t exist in the data, fallback to latest
    month_rows = _df.loc[_df["outcome_n"] == month_idx_int, ["_month"]].drop_duplicates()
    if month_rows.empty:
        month_idx_int = _latest_idx
        month_rows = _df.loc[_df["outcome_n"] == month_idx_int, ["_month"]].drop_duplicates()

    month_label = "Unknown" if month_rows.empty else month_rows["_month"].iloc[0].strftime("%Y-%m")

    # Month-global distributions
    pie_counts = pie_counts_for_month(_df, month_idx_int)
    waffle_counts = waffle_counts_for_month(_df, month_idx_int)

    # Row for highlight
    target = find_country_row(_df, month_idx_int, iso3)
    if target is None:
        pie_fig = make_pie(pie_counts, None, month_label)
        waffle_fig = make_waffle(waffle_counts, None, month_label)
        info = html.Span([
            html.B("Note: "), f"No record for {iso3} in {month_label}. ",
            "Charts show month-level distribution across all countries."
        ])
        return pie_fig, waffle_fig, info

    country_name = str(target.get("name", iso3))
    p_val = float(target.get("outcome_p", 0.0))
    pred_val = float(target.get("predicted", 0.0))
    cat = categorize_prob_single(p_val)
    band = categorize_band_single(pred_val)

    pie_fig = make_pie(pie_counts, cat, month_label)
    waffle_fig = make_waffle(waffle_counts, band, month_label)

    info = html.Span([
        html.B("Country: "), f"{country_name} ({iso3})  •  ",
        html.B("Month: "), f"{month_label}  •  ",
        html.B("Pr(>threshold): "), f"{p_val:.3f} → {cat}  •  ",
        html.B("Predicted fatalities: "), f"{pred_val:.1f} → {band}",
    ])
    return pie_fig, waffle_fig, info

# ---------- Toggle details panel ----------

@callback(
    Output("details-panel", "style"),
    Output("details-toggle", "aria-expanded"),
    Input("details-toggle", "n_clicks"),
    Input("details-close", "n_clicks"),
    State("details-panel", "style"),
    prevent_initial_call=False,
)
def toggle_details(open_clicks, close_clicks, current_style):
    current_style = dict(current_style or {})
    is_visible = current_style.get("display", "none") != "none"

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if trigger_id == "details-close":
        current_style["display"] = "none"
        return current_style, "false"

    if trigger_id == "details-toggle":
        current_style["display"] = "none" if is_visible else "block"
        return current_style, "true" if not is_visible else "false"

    current_style["display"] = "none"
    return current_style, "false"
