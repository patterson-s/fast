from __future__ import annotations
from dash import html, dcc

def serve_layout():
    return html.Div(
        [
            dcc.Location(id="url"),
            dcc.Store(id="store-country-name"),
            html.Div(id="page-content"),
        ],
        style={"maxWidth": "1200px", "margin": "0 auto"},
    )
