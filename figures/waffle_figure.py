from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from typing import Optional
from config import BAND_LABELS, BAND_COLORS, WAFFLE_COLS, WAFFLE_CELL, WAFFLE_GAP

def make_waffle(
    band_counts: pd.Series,
    highlight_band: Optional[str],
    month_label: str,
    cols: int = WAFFLE_COLS,
    cell: float = WAFFLE_CELL,
    gap: float = WAFFLE_GAP,
) -> go.Figure:
    order = BAND_LABELS[::-1]  # top band first
    rows_per_band = {lab: int(np.ceil(int(band_counts[lab]) / cols)) for lab in order}

    traces = []
    y_offset = 0.0
    for lab in order:
        n = int(band_counts[lab])
        if n <= 0:
            y_offset += gap
            continue

        xs, ys, line_widths = [], [], []
        for i in range(n):
            r = i // cols
            c = i % cols
            x = c * (cell + gap)
            y = y_offset + r * (cell + gap)

            xs.append(x)
            ys.append(-y)  # invert so top band is at top
            if highlight_band is not None and lab == highlight_band and i == 0:
                line_widths.append(2.0)
            else:
                line_widths.append(0.6)

        if xs:
            traces.append(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    name=lab,
                    hovertemplate=f"Band: {lab}<br>Tile %{{pointNumber}}<extra></extra>",
                    marker=dict(symbol="square", size=16, color=BAND_COLORS[lab], line=dict(color="black", width=line_widths)),
                    showlegend=True,
                )
            )

        y_offset += max(rows_per_band[lab], 1) * (cell + gap) + gap

    fig = go.Figure(data=traces)
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
