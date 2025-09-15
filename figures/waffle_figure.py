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
    title_text: str | None = None,
) -> go.Figure:
    order = BAND_LABELS[::-1]
    
    # Safety checks and logging
    total_countries = band_counts.sum()
    if total_countries > 500:
        print(f"WARNING: {total_countries} total countries in waffle chart for {month_label}")
        return go.Figure().add_annotation(
            text=f"Too many countries to display ({total_countries})", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Cap individual band counts to prevent runaway
    safe_band_counts = band_counts.copy()
    for lab in order:
        count = int(band_counts[lab])
        if count > 100:
            print(f"WARNING: Capping {lab} from {count} to 100 countries")
            safe_band_counts[lab] = 100
        elif count < 0:
            print(f"WARNING: Negative count for {lab}: {count}, setting to 0")
            safe_band_counts[lab] = 0

    rows_per_band = {lab: int(np.ceil(max(0, int(safe_band_counts[lab])) / cols)) for lab in order}

    traces = []
    y_offset = 0.0
    max_total_rows = 0
    
    for lab in order:
        n = int(safe_band_counts[lab])
        if n <= 0:
            y_offset += gap
            continue

        # Additional safety check per band
        if n > 200:
            print(f"ERROR: Band {lab} has {n} countries, skipping")
            continue

        xs, ys, line_widths = [], [], []
        current_band_rows = 0
        
        for i in range(n):
            r = i // cols
            c = i % cols
            x = c * (cell + gap)
            y = y_offset + r * (cell + gap)

            xs.append(x)
            ys.append(-y)
            current_band_rows = max(current_band_rows, r + 1)
            
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

        band_height = max(rows_per_band[lab], 1) * (cell + gap) + gap
        y_offset += band_height
        max_total_rows += current_band_rows

    # Safety check on total figure dimensions
    if max_total_rows > 50 or y_offset > 50:
        print(f"ERROR: Waffle chart too large - rows: {max_total_rows}, y_offset: {y_offset}")
        return go.Figure().add_annotation(
            text="Chart too large to display safely", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )

    fig = go.Figure(data=traces)
    max_cols = cols * (cell + gap)
    safe_max_rows = min(y_offset, 20)
    
    fig.update_xaxes(visible=False, range=[-cell, max_cols + cell])
    fig.update_yaxes(visible=False, range=[-(safe_max_rows + cell), cell])

    fig.update_layout(
        title=dict(text=title_text or "Waffle Chart", x=0.5, xanchor="center"),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0.0),
        margin=dict(l=10, r=10, t=50, b=70),
        height=520,
        autosize=False,
    )

    return fig