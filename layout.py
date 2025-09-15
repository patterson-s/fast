from __future__ import annotations
from dash import html
# During Commit 1 we don’t rebuild layout; we render what map_01 defines.
# This keeps the app running while we move pieces in later commits.
def serve_layout():
    return html.Div(id="app-root")  # placeholder; callbacks will populate later
