from __future__ import annotations
from dash import Dash
from layout import serve_layout  # stub for now
import callbacks  # noqa: F401  # registers callbacks via decorators

def create_app() -> Dash:
    app = Dash(__name__, suppress_callback_exceptions=True, assets_folder="assets")
    app.title = "FAST-cm Interactive Visualizer"
    app.layout = serve_layout  # temporary stub that mounts old content
    return app

if __name__ == "__main__":
    create_app().run_server(debug=True)
