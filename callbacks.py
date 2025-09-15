# callbacks.py
from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, urlencode

import dash
from dash import Input, Output, State, callback, dcc, html
from plotly.graph_objects import Figure

from config import DEF_PARQUET
from data_loader import latest_month_idx, load_dataframe, month_options, prepare_map_data
from figures.map_figure import make_world_map
from figures.pie_figure import make_pie
from figures.waffle_figure import make_waffle
from utils import (
    categorize_band_single,
    categorize_prob_single,
    find_country_row,
    pie_counts_for_month,
    read_model_details,
    waffle_counts_for_month,
)

# ========= Lazy, cached data accessors (no heavy work at import time) =========
@lru_cache(maxsize=1)
def get_df():
    return load_dataframe(DEF_PARQUET)

@lru_cache(maxsize=1)
def get_map_data():
    return prepare_map_data(get_df())

@lru_cache(maxsize=1)
def get_month_opts():
    return month_options(get_df())

@lru_cache(maxsize=1)
def get_latest_idx():
    return latest_month_idx(get_df())


# ===================== Page layout builders (pure) =====================
def _map_page_layout() -> html.Div:
    return html.Div(
        [
            html.H1(
                "FAST-cm Conflict Forecast — World Map",
                style={"textAlign": "center", "color": "#333", "marginBottom": "20px"},
            ),
            dcc.Graph(
                id="world-map",
                figure=make_world_map(get_map_data()),
                config={"displayModeBar": True},
            ),
            html.Div(
                "Tip: Click a country to open the full detail page.",
                style={"textAlign": "center", "color": "#666"},
            ),
        ]
    )

def _country_page_layout(iso3: str, query_month: int | None) -> html.Div:
    df = get_df()
    country_name = df.loc[df["isoab"].str.upper() == iso3.upper(), "name"].head(1)
    display_name = country_name.iloc[0] if not country_name.empty else iso3.upper()
    default_month = query_month if query_month is not None else get_latest_idx()
    model_md = read_model_details()

    return html.Div(
        [
            html.Div(
                [
                    html.H2(
                        f"{display_name} ({iso3.upper()}) — Detail View",
                        style={"margin": 0, "color": "#333"},
                    ),
                    html.Div(dcc.Link("← Back to map", href="/"), style={"marginTop": "4px", "color": "#555"}),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "2px", "marginBottom": "12px"},
            ),
            html.Div(
                [
                    html.Div("Select month:", style={"fontWeight": 600, "marginRight": "8px"}),
                    dcc.Dropdown(
                        id="month-dropdown",
                        options=get_month_opts(),
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
                    html.Div(
                        [
                            dcc.Graph(id="pie-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                            html.Div(id="pie-caption", style={"marginTop": "6px", "fontSize": "14px", "color": "#333"}),
                        ],
                        style={"flex": "1", "minWidth": "380px"},
                    ),
                    html.Div(
                        [
                            dcc.Graph(id="waffle-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                            html.Div(id="waffle-caption", style={"marginTop": "6px", "fontSize": "14px", "color": "#333"}),
                        ],
                        style={"flex": "1", "minWidth": "380px"},
                    ),
                ],
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
            ),
        ]
    )


# ============================== Router ==============================

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


# ========== Map click → navigate to /country/ISO3?month=<latest> ==========

@callback(Output("url", "href"), Input("world-map", "clickData"), prevent_initial_call=True)
def on_map_click(clickData):
    if not clickData:
        return dash.no_update
    iso3 = clickData["points"][0]["location"]
    query = urlencode({"month": get_latest_idx()})
    return f"/country/{iso3}?{query}"


# ======== Country page computations → figures + info ========

@callback(
    Output("pie-fig", "figure"),
    Output("waffle-fig", "figure"),
    Output("info-strip", "children"),
    Output("pie-caption", "children"),
    Output("waffle-caption", "children"),
    Input("month-dropdown", "value"),
    Input("url", "pathname"),
)
def update_country_figures(month_idx, pathname):
    # Must be on /country/<ISO3>
    parts = [p for p in (pathname or "").split("/") if p]
    if len(parts) != 2 or parts[0] != "country":
        # 5 outputs: return empty figs + no update on texts if not on country page
        return Figure(), Figure(), dash.no_update, dash.no_update, dash.no_update

    iso3 = parts[1].upper()

    # Month guard: if missing/invalid, fall back to latest
    try:
        month_idx_int = int(month_idx) if month_idx is not None else get_latest_idx()
    except Exception:
        month_idx_int = get_latest_idx()

    df = get_df()

    # If the month doesn’t exist in the data, fallback to latest
    month_rows = df.loc[df["outcome_n"] == month_idx_int, ["_month"]].drop_duplicates()
    if month_rows.empty:
        month_idx_int = get_latest_idx()
        month_rows = df.loc[df["outcome_n"] == month_idx_int, ["_month"]].drop_duplicates()

    month_label = "Unknown" if month_rows.empty else month_rows["_month"].iloc[0].strftime("%Y-%m")

    # Month-global distributions
    pie_counts = pie_counts_for_month(df, month_idx_int)
    waffle_counts = waffle_counts_for_month(df, month_idx_int)

    # Row for highlight (country-month record)
    target = find_country_row(df, month_idx_int, iso3)

    # Short titles that should appear inside the figures
    pie_title = "Figure 1: Conflict Likelihood"
    waffle_title = "Figure 2: Conflict Intensity"

    if target is None:
        # No specific country-month record → neutral figures and captions
        pie_fig = make_pie(pie_counts, None, month_label, title_text=pie_title)
        waffle_fig = make_waffle(waffle_counts, None, month_label, title_text=waffle_title)

        info = html.Span(
            [
                html.B("Note: "),
                f"No record for {iso3} in {month_label}. ",
                "Charts show month-level distribution across all countries.",
            ]
        )

        prob_notes = (
            "Figure 1 groups countries by **Pr(fatalities ≥25)** into four categories: "
            "**≤1%**, **1–50%**, **50–99%**, **≥99%**. Slice sizes show the share of countries in each category this month."
        )
        band_notes = (
            "Figure 2 bins mean predicted fatalities into bands: "
            "**0**, **1–10**, **11–100**, **101–1,000**, **1,001–10,000**, **10,001+**. "
            "Each square represents one country."
        )
        return pie_fig, waffle_fig, info, dcc.Markdown(prob_notes), dcc.Markdown(band_notes)

    # --- If we have the record, compute the narrative values (already available in your current code) ---
    country_name = str(target.get("name", iso3))
    p_val = float(target.get("outcome_p", 0.0))
    pred_val = float(target.get("predicted", 0.0))
    cat = categorize_prob_single(p_val)
    band = categorize_band_single(pred_val)

    # Figures with short titles + highlights
    pie_fig = make_pie(pie_counts, cat, month_label, title_text=pie_title)
    waffle_fig = make_waffle(waffle_counts, band, month_label, title_text=waffle_title)

    # Compact info strip (kept as-is)
    info = html.Span(
        [
            html.B("Country: "),
            f"{country_name} ({iso3})  •  ",
            html.B("Month: "),
            f"{month_label}  •  ",
            html.B("Pr(>threshold): "),
            f"{p_val:.3f} → {cat}  •  ",
            html.B("Predicted fatalities: "),
            f"{pred_val:.1f} → {band}",
        ]
    )

    # Machine-generated captions (narrative + how-it’s-built notes)
    cap_likelihood = (
        f"**Figure 1** illustrates how likely **{country_name}** is to experience severe conflict in **{month_label}**. "
        f"Our forecasts predict that **{country_name}** has a **{p_val:.0%}** chance of suffering **≥25** conflict fatalities in **{month_label}**, "
        f"which places {country_name} in the **“{cat}”** category."
    )
    prob_notes = (
        "Figure 1 groups each country’s **Pr(fatalities ≥25)** into four categories: "
        "**≤1%** = Near-certain no conflict; **1–50%** = Improbable conflict; **50–99%** = Probable conflict; "
        "**≥99%** = Near-certain conflict. Slice sizes show the share of countries in each category this month; "
        f"{country_name}’s category is highlighted in the chart."
    )
    pie_caption = dcc.Markdown(cap_likelihood + "\n\n" + prob_notes)

    cap_intensity = (
        f"**Figure 2** illustrates how severe the conflict in **{country_name}** is forecasted to be in **{month_label}**. "
        f"Our forecasts predict **{pred_val:.1f}** fatalities in **{month_label}**. "
        f"This places {country_name} in the **“{band}”** category."
    )
    band_notes = (
        "Figure 2 bins the **mean predicted fatalities** per country into bands: "
        "**0**, **1–10**, **11–100**, **101–1,000**, **1,001–10,000**, **10,001+**. "
        "Each square represents one country in this month; the country’s band is highlighted with a thicker outline."
    )
    waffle_caption = dcc.Markdown(cap_intensity + "\n\n" + band_notes)

    return pie_fig, waffle_fig, info, pie_caption, waffle_caption



# ========== Toggle details panel ==========

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
