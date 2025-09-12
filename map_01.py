#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache
import time
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthEnd
from urllib.parse import urlencode, urlparse, parse_qs

# =========================
# Config (bins, labels, colors)
# =========================
# Outcome-probability (pie)
PIE_BINS   = [-float("inf"), 0.01, 0.5, 0.99, float("inf")]
PIE_LABELS = [
    "Near-certain no conflict",
    "Improbable conflict",
    "Probable conflict",
    "Near-certain conflict",
]
PIE_COLORS = {
    "Near-certain no conflict": "green",
    "Improbable conflict": "blue",
    "Probable conflict": "orange",
    "Near-certain conflict": "red",
}

# Predicted-count bands (waffle)
BAND_BINS   = [-0.1, 0, 10, 100, 1000, 10000, float("inf")]
BAND_LABELS = ["0", "1–10", "11–100", "101–1,000", "1,001–10,000", "10,001+"]
BAND_COLORS = {
    "0":            "#6baed6",
    "1–10":         "#74c476",
    "11–100":       "#fd8d3c",
    "101–1,000":    "#9e9ac8",
    "1,001–10,000": "#e34a33",
    "10,001+":      "#636363",
}

WAFFLE_COLS = 12     # tiles per row
WAFFLE_GAP  = 0.0    # inter-tile gap; keep tight
WAFFLE_CELL = 1.0    # tile size

DEF_PARQUET = Path(__file__).resolve().parent / "data" / "FAST-Forecast.parquet"


# =========================
# Data loading & prep
# =========================
def load_dataframe(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    required = {"name", "isoab", "dates", "predicted", "cumulative_outcome_n", "outcome_p", "outcome_n"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Parquet missing expected columns: {missing}")

    parsed = pd.to_datetime(df["dates"].astype(str), errors="coerce")
    bad_mask = parsed.isna() & df["dates"].astype(str).str.match(r"^\d{6}$").fillna(False)
    parsed.loc[bad_mask] = pd.to_datetime(df.loc[bad_mask, "dates"].astype(str), format="%Y%m", errors="coerce")
    df["_month"] = parsed.dt.to_period("M").dt.to_timestamp() + MonthEnd(0)

    df = df.sort_values(["name", "_month"]).reset_index(drop=True)
    return df


def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
    map_data = df.groupby(["name", "isoab"]).agg({
        "predicted": "sum",
        "_month": ["min", "max"]
    }).reset_index()
    map_data.columns = ["name", "iso3", "total_predicted", "horizon_start", "horizon_end"]
    map_data["log_predicted"] = np.log1p(map_data["total_predicted"])
    return map_data


def month_options(df: pd.DataFrame) -> List[Dict[str, Any]]:
    # Build dropdown options [{label: 'YYYY-MM', value: outcome_n}, ...]
    small = df[["_month", "outcome_n"]].drop_duplicates().sort_values("_month")
    return [{"label": m.strftime("%Y-%m"), "value": int(n)} for m, n in zip(small["_month"], small["outcome_n"])]


def latest_month_idx(df: pd.DataFrame) -> int:
    small = df[["_month", "outcome_n"]].drop_duplicates().sort_values("_month")
    return int(small["outcome_n"].iloc[-1])


# =========================
# Categorization helpers
# =========================
def categorize_prob_single(p: float) -> str:
    if p <= 0.01:
        return "Near-certain no conflict"
    elif p < 0.5:
        return "Improbable conflict"
    elif p < 0.99:
        return "Probable conflict"
    else:
        return "Near-certain conflict"


def categorize_band_single(pred: float) -> str:
    edges = BAND_BINS
    labs = BAND_LABELS
    for i in range(len(labs)):
        # include lowest edge
        if edges[i] < pred <= edges[i+1] or (i == 0 and pred == edges[0]):
            return labs[i]
    return labs[-1]


def pie_counts_for_month(df: pd.DataFrame, month_idx: int) -> pd.Series:
    dfm = df.loc[df["outcome_n"] == month_idx]
    if dfm.empty:
        return pd.Series(0, index=PIE_LABELS, dtype=int)
    cats = pd.cut(dfm["outcome_p"].fillna(0.0),
                  bins=PIE_BINS, labels=PIE_LABELS,
                  right=True, include_lowest=True)
    return cats.value_counts().reindex(PIE_LABELS, fill_value=0)


def waffle_counts_for_month(df: pd.DataFrame, month_idx: int) -> pd.Series:
    dfm = df.loc[df["outcome_n"] == month_idx]
    if dfm.empty:
        return pd.Series(0, index=BAND_LABELS, dtype=int)
    bands = pd.cut(dfm["predicted"].fillna(0.0),
                   bins=BAND_BINS, labels=BAND_LABELS,
                   include_lowest=True)
    return bands.value_counts().reindex(BAND_LABELS, fill_value=0)


def find_country_row(df: pd.DataFrame, month_idx: int, iso3: str) -> Optional[pd.Series]:
    dfm = df.loc[(df["outcome_n"] == month_idx) & (df["isoab"].str.upper() == iso3.upper())]
    if dfm.empty:
        return None
    return dfm.iloc[0]

# =========================
# Markdown loader (mtime-aware)
# =========================
MODEL_DETAILS_PATH = Path(__file__).resolve().parent / "docs" / "model_details.md"

@lru_cache(maxsize=1)
def _read_model_details_cached(_cache_buster: float) -> str:
    """Internal: cached read so we don't hit disk every render."""
    if not MODEL_DETAILS_PATH.exists():
        return "*(model_details.md not found — create docs/model_details.md)*"
    return MODEL_DETAILS_PATH.read_text(encoding="utf-8")

def read_model_details() -> str:
    """
    Read markdown, but let edits during development show up automatically.
    We pass the file's mtime into the cache key so the cache invalidates on changes.
    """
    try:
        mtime = MODEL_DETAILS_PATH.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    return _read_model_details_cached(mtime)


# =========================
# Figures
# =========================
def create_world_map(map_data: pd.DataFrame) -> go.Figure:
    if map_data.empty:
        return go.Figure().add_annotation(text="No data available",
                                          xref="paper", yref="paper",
                                          x=0.5, y=0.5, showarrow=False)

    fig = px.choropleth(
        map_data,
        locations="iso3",
        hover_name="name",
        hover_data={
            "total_predicted": ":,",
            "horizon_start": True,
            "horizon_end": True,
            "iso3": False,
            "log_predicted": False
        },
        color="log_predicted",
        color_continuous_scale="Reds",
        labels={
            'log_predicted': 'Log(Total Predicted + 1)',
            'total_predicted': 'Total Predicted Fatalities',
            'horizon_start': 'Horizon Start',
            'horizon_end': 'Horizon End'
        }
    )
    fig.update_layout(
        title={'text': "Conflict Forecast Map - Click a country",
               'x': 0.5, 'xanchor': 'center', 'font': {'size': 20}},
        geo=dict(showframe=False, showcoastlines=True, projection_type='natural earth'),
        height=600, margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig


def build_pie_figure(cat_counts: pd.Series,
                     highlight_label: Optional[str],
                     month_label: str) -> go.Figure:
    values = cat_counts.values.tolist()
    labels = cat_counts.index.tolist()

    # Pull out the highlighted slice slightly
    pulls = [0.08 if (highlight_label is not None and lab == highlight_label) else 0 for lab in labels]
    marker_lines = [2 if (highlight_label is not None and lab == highlight_label) else 0 for lab in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                sort=False,
                direction="clockwise",
                hole=0.0,
                pull=pulls,
                textinfo="percent",
                textfont=dict(color="white", size=12),
                marker=dict(
                    colors=[PIE_COLORS[lab] for lab in labels],
                    line=dict(color=["black" if w > 0 else "white" for w in marker_lines],
                              width=marker_lines),
                ),
            )
        ]
    )
    title = f"Risk categories for month {month_label}"
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )

    # Optional annotation for highlight
    if highlight_label is not None and highlight_label in labels:
        fig.add_annotation(
            text=f"Highlighted: {highlight_label}",
            xref="paper", yref="paper",
            x=0.02, y=0.98, showarrow=False, align="left",
            bgcolor="rgba(255,255,255,0.6)", bordercolor="black", borderwidth=1
        )

    return fig


def build_waffle_figure(band_counts: pd.Series,
                        highlight_band: Optional[str],
                        month_label: str,
                        cols: int = WAFFLE_COLS,
                        cell: float = WAFFLE_CELL,
                        gap: float = WAFFLE_GAP) -> go.Figure:
    """
    Create a vertical waffle made of square markers; top band at top.
    One Scatter trace per band keeps legend clean.
    """
    # Order top->bottom (reverse so highest band appears at the top)
    order = BAND_LABELS[::-1]

    # Compute stacking rows per band
    rows_per_band = {lab: int(np.ceil(int(band_counts[lab]) / cols)) for lab in order}

    # Build coordinates
    traces = []
    y_offset = 0.0
    for lab in order:
        n = int(band_counts[lab])
        if n <= 0:
            # still reserve a faint separator line
            y_offset += gap  # small spacer
            continue

        xs, ys, line_widths = [], [], []
        for i in range(n):
            r = i // cols  # row index within band
            c = i % cols   # column index
            x = c * (cell + gap)
            y = y_offset + r * (cell + gap)

            xs.append(x)
            ys.append(-y)  # invert y so top band plots at top
            # Thicker outline for the first tile of the highlight band
            if highlight_band is not None and lab == highlight_band and i == 0:
                line_widths.append(2.0)
            else:
                line_widths.append(0.6)

        # Push a trace for this band (if there are points)
        if xs:
            traces.append(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    name=lab,
                    hovertemplate=f"Band: {lab}<br>Tile %{{pointNumber}}<extra></extra>",
                    marker=dict(
                        symbol="square",
                        size=16,  # adjust to taste; visual tile size
                        color=BAND_COLORS[lab],
                        line=dict(color="black", width=line_widths),
                    ),
                    showlegend=True
                )
            )

        # Advance y_offset by the band height
        y_offset += max(rows_per_band[lab], 1) * (cell + gap) + gap  # band gap

    # Figure frame
    fig = go.Figure(data=traces)
    # Set axis ranges to fit snugly
    max_cols = cols * (cell + gap)
    max_rows = y_offset
    fig.update_xaxes(visible=False, range=[-cell, max_cols + cell])
    fig.update_yaxes(visible=False, range=[-(max_rows + cell), cell])

    fig.update_layout(
        title=dict(text=f"Vertical waffle — bands by color — {month_label}", x=0.5, xanchor="center"),
        legend=dict(orientation="v", x=1.02, y=1.0),
        margin=dict(l=10, r=150, t=50, b=10),
        height=520,
    )
    return fig


# =========================
# App & Pages
# =========================
def create_app(df: pd.DataFrame) -> dash.Dash:
    # Allow IDs that only appear on certain routes
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.title = "FAST-cm Interactive Visualizer (Pie + Waffle)"

    # Precompute shared bits
    map_data = prepare_map_data(df)
    month_opts = month_options(df)
    latest_idx = latest_month_idx(df)

    # Validation layout so Dash knows about ALL IDs used across pages
    sample_iso = (map_data["iso3"].iloc[0] if not map_data.empty else "USA")
    app.validation_layout = html.Div([
        # Map page bits
        dcc.Location(id="url"),
        html.Div(id="page-content"),
        dcc.Graph(id="world-map"),
        # Country page bits
        dcc.Dropdown(id="month-dropdown", options=month_opts, value=latest_idx),
        html.Div(id="info-strip"),
        dcc.Graph(id="pie-fig"),
        dcc.Graph(id="waffle-fig"),
        # Details panel bits
        html.Button("Model details and selection criteria", id="details-toggle"),
        html.Div(id="details-panel"),
        html.Div(id="details-close"),
    ])

    # Simple shell
    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            dcc.Store(id="store-country-name"),
            html.Div(id="page-content"),
        ],
        style={"maxWidth": "1200px", "margin": "0 auto"}
    )

    # ----- Page layouts
    def map_page_layout() -> html.Div:
        return html.Div(
            [
                html.H1(
                    "FAST-cm Conflict Forecast — World Map",
                    style={'textAlign': 'center', 'color': '#333', 'marginBottom': '20px'}
                ),
                dcc.Graph(
                    id='world-map',
                    figure=create_world_map(map_data),
                    config={'displayModeBar': True}
                ),
                html.Div(
                    "Tip: Click a country to open the full detail page.",
                    style={"textAlign": "center", "color": "#666"}
                ),
            ]
        )

    def country_page_layout(iso3: str, query_month: Optional[int]) -> html.Div:
        # Resolve display name
        country_name = df.loc[df["isoab"].str.upper() == iso3.upper(), "name"].head(1)
        display_name = country_name.iloc[0] if not country_name.empty else iso3.upper()

        # Month default
        default_month = query_month if query_month is not None else latest_idx

        # Load the static markdown content
        model_md = read_model_details()

        return html.Div(
            [
                html.Div(
                    [
                        html.H2(
                            f"{display_name} ({iso3.upper()}) — Detail View",
                            style={'margin': 0, 'color': '#333'}
                        ),
                        html.Div(
                            dcc.Link("← Back to map", href="/"),
                            style={'marginTop': '4px', 'color': '#555'}
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "2px",
                        "marginBottom": "12px",
                    },
                ),

                # Controls
                html.Div(
                    [
                        html.Div("Select month:", style={"fontWeight": 600, "marginRight": "8px"}),
                        dcc.Dropdown(
                            id="month-dropdown",
                            options=month_opts,
                            value=default_month,
                            clearable=False,
                            searchable=False,
                            style={"width": "240px"}
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "10px"}
                ),

                # Model details toggle + collapsible panel
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
                                "display": "none",           # hidden by default; toggled via callback
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
                                    style={
                                        "position": "sticky",
                                        "top": 0,
                                        "float": "right",
                                        "cursor": "pointer",
                                        "fontSize": "20px",
                                        "color": "#666",
                                    },
                                ),
                                dcc.Markdown(model_md),
                            ],
                        ),
                    ],
                    style={"marginBottom": "10px"}
                ),

                # Info strip
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

                # Two charts
                html.Div(
                    [
                        dcc.Graph(id="pie-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                        dcc.Graph(id="waffle-fig", config={"displayModeBar": False}, style={"flex": "1"}),
                    ],
                    style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}
                ),
            ]
        )

    # ----- Router
    @app.callback(Output("page-content", "children"), Input("url", "pathname"), State("url", "search"))
    def route(pathname, search):
        if pathname is None or pathname == "/":
            return map_page_layout()

        # /country/<ISO3>
        parts = [p for p in pathname.split("/") if p]
        if len(parts) == 2 and parts[0] == "country":
            iso3 = parts[1]
            # parse ?month=
            q = parse_qs(search[1:], keep_blank_values=True) if search else {}
            month_idx = None
            if "month" in q:
                try:
                    month_idx = int(q["month"][0])
                except Exception:
                    month_idx = None
            return country_page_layout(iso3, month_idx)

        # fallback
        return html.Div(
            [html.H2("Page not found"), dcc.Link("Go to map", href="/")],
            style={"textAlign": "center", "padding": "40px"}
        )

    # ----- Map click → navigate to /country/ISO3?month=<latest>
    @app.callback(
        Output("url", "href"),
        Input("world-map", "clickData"),
        prevent_initial_call=True
    )
    def on_map_click(clickData):
        if not clickData:
            return dash.no_update
        iso3 = clickData["points"][0]["location"]
        query = urlencode({"month": latest_idx})
        return f"/country/{iso3}?{query}"

    # ----- Country page computations → figures + info
    @app.callback(
        Output("pie-fig", "figure"),
        Output("waffle-fig", "figure"),
        Output("info-strip", "children"),
        Input("month-dropdown", "value"),
        Input("url", "pathname"),
    )
    def update_country_figures(month_idx, pathname):
        # Guard: only run on country page
        parts = [p for p in (pathname or "").split("/") if p]
        if len(parts) != 2 or parts[0] != "country":
            return go.Figure(), go.Figure(), dash.no_update
        iso3 = parts[1].upper()

        # Month label (YYYY-MM) for titles
        month_row = df.loc[df["outcome_n"] == int(month_idx), ["_month"]].drop_duplicates()
        if month_row.empty:
            month_label = "Unknown"
        else:
            month_label = month_row["_month"].iloc[0].strftime("%Y-%m")

        # Month-global counts
        pie_counts = pie_counts_for_month(df, int(month_idx))
        waffle_counts = waffle_counts_for_month(df, int(month_idx))

        # Target row & highlights
        target = find_country_row(df, int(month_idx), iso3)
        if target is None:
            pie_fig = build_pie_figure(pie_counts, None, month_label)
            waffle_fig = build_waffle_figure(waffle_counts, None, month_label)
            info = html.Span([
                html.B("Note: "), f"No record for {iso3} in {month_label}. ",
                "Charts show month-level distribution across all countries."
            ])
            return pie_fig, waffle_fig, info

        country_name = str(target["name"])
        p_val = float(target.get("outcome_p", 0.0))
        pred_val = float(target.get("predicted", 0.0))
        cat = categorize_prob_single(p_val)
        band = categorize_band_single(pred_val)

        pie_fig = build_pie_figure(pie_counts, cat, month_label)
        waffle_fig = build_waffle_figure(waffle_counts, band, month_label)

        info = html.Span([
            html.B("Country: "), f"{country_name} ({iso3})  •  ",
            html.B("Month: "), f"{month_label}  •  ",
            html.B("Pr(>threshold): "), f"{p_val:.3f} → {cat}  •  ",
            html.B("Predicted fatalities: "), f"{pred_val:.1f} → {band}"
        ])
        return pie_fig, waffle_fig, info

    # ----- NEW: Toggle the details panel (button & close "×")
    @app.callback(
        Output("details-panel", "style"),
        Output("details-toggle", "aria-expanded"),
        Input("details-toggle", "n_clicks"),
        Input("details-close", "n_clicks"),
        State("details-panel", "style"),
        prevent_initial_call=False,
    )
    def toggle_details(open_clicks, close_clicks, current_style):
        # Ensure style dict exists
        current_style = dict(current_style or {})
        is_visible = current_style.get("display", "none") != "none"

        # Which control fired?
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Close explicitly
        if trigger_id == "details-close":
            current_style["display"] = "none"
            return current_style, "false"

        # Toggle via button
        if trigger_id == "details-toggle":
            current_style["display"] = "none" if is_visible else "block"
            return current_style, "true" if not is_visible else "false"

        # Initial render: keep hidden
        current_style["display"] = "none"
        return current_style, "false"

    return app



    # ----- Router
    @app.callback(Output("page-content", "children"), Input("url", "pathname"), State("url", "search"))
    def route(pathname, search):
        if pathname is None or pathname == "/":
            return map_page_layout()

        # /country/<ISO3>
        parts = [p for p in pathname.split("/") if p]
        if len(parts) == 2 and parts[0] == "country":
            iso3 = parts[1]
            # parse ?month=
            q = parse_qs(search[1:], keep_blank_values=True) if search else {}
            month_idx = None
            if "month" in q:
                try:
                    month_idx = int(q["month"][0])
                except Exception:
                    month_idx = None
            return country_page_layout(iso3, month_idx)

        # fallback
        return html.Div(
            [html.H2("Page not found"), dcc.Link("Go to map", href="/")],
            style={"textAlign": "center", "padding": "40px"}
        )

    # ----- Map click → navigate to /country/ISO3?month=<latest>
    @app.callback(
        Output("url", "href"),
        Input("world-map", "clickData"),
        prevent_initial_call=True
    )
    def on_map_click(clickData):
        if not clickData:
            return dash.no_update
        iso3 = clickData["points"][0]["location"]
        query = urlencode({"month": latest_idx})
        return f"/country/{iso3}?{query}"

    # ----- Country page computations → figures + info
    @app.callback(
        Output("pie-fig", "figure"),
        Output("waffle-fig", "figure"),
        Output("info-strip", "children"),
        Input("month-dropdown", "value"),
        Input("url", "pathname"),
    )
    def update_country_figures(month_idx, pathname):
        # Guard: only run on country page
        parts = [p for p in (pathname or "").split("/") if p]
        if len(parts) != 2 or parts[0] != "country":
            return go.Figure(), go.Figure(), dash.no_update
        iso3 = parts[1].upper()

        # Month label (YYYY-MM) for titles
        month_row = df.loc[df["outcome_n"] == int(month_idx), ["_month"]].drop_duplicates()
        if month_row.empty:
            month_label = "Unknown"
        else:
            month_label = month_row["_month"].iloc[0].strftime("%Y-%m")

        # Month-global counts
        pie_counts = pie_counts_for_month(df, int(month_idx))
        waffle_counts = waffle_counts_for_month(df, int(month_idx))

        # Target row & highlights
        target = find_country_row(df, int(month_idx), iso3)
        if target is None:
            # Build figures without highlight; info message about missing row
            pie_fig = build_pie_figure(pie_counts, None, month_label)
            waffle_fig = build_waffle_figure(waffle_counts, None, month_label)
            info = html.Span([
                html.B("Note: "), f"No record for {iso3} in {month_label}. ",
                "Charts show month-level distribution across all countries."
            ])
            return pie_fig, waffle_fig, info

        country_name = str(target["name"])
        p_val = float(target.get("outcome_p", 0.0))
        pred_val = float(target.get("predicted", 0.0))
        cat = categorize_prob_single(p_val)
        band = categorize_band_single(pred_val)

        pie_fig = build_pie_figure(pie_counts, cat, month_label)
        waffle_fig = build_waffle_figure(waffle_counts, band, month_label)

        info = html.Span([
            html.B("Country: "), f"{country_name} ({iso3})  •  ",
            html.B("Month: "), f"{month_label}  •  ",
            html.B("Pr(>threshold): "), f"{p_val:.3f} → {cat}  •  ",
            html.B("Predicted fatalities: "), f"{pred_val:.1f} → {band}"
        ])
        return pie_fig, waffle_fig, info

    return app


# =========================
# Entrypoint
# =========================
def main():
    parser = argparse.ArgumentParser(description="FAST-cm interactive visualizer (map + full country view)")
    parser.add_argument(
        "--parquet",
        type=str,
        default=os.environ.get("FAST_CM_PARQUET", str(DEF_PARQUET)),
        help="Path to FAST-Forecast.parquet"
    )
    args = parser.parse_args()

    parquet_path = Path(args.parquet)
    if not parquet_path.exists():
        print(f"Parquet not found: {parquet_path}")
        sys.exit(1)

    try:
        df = load_dataframe(parquet_path)
    except Exception as e:
        print(f"Error loading parquet: {e}")
        sys.exit(1)

    app = create_app(df)

    # Production vs development settings
    is_production = os.environ.get('RENDER')
    if is_production:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=False)
    else:
        app.run(debug=True)


if __name__ == "__main__":
    main()
