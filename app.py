# app.py
import os
import dash
from dash import dcc, html

# Create the Dash app first so dash.callback can register callbacks
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "FAST-cm"
server = app.server  # <- Render/Gunicorn entry point

# Minimal shell layout; callbacks.py will fill page-content
app.layout = html.Div(
    [dcc.Location(id="url"), html.Div(id="page-content")],
    style={"maxWidth": "1200px", "margin": "0 auto"},
)

# IMPORTANT: import after app is created so @callback uses this app
import callbacks  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
