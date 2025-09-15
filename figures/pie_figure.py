from __future__ import annotations
import plotly.graph_objects as go
import pandas as pd
from typing import Optional
from config import PIE_COLORS

def make_pie(cat_counts: pd.Series, highlight_label: Optional[str], month_label: str) -> go.Figure:
    values = cat_counts.values.tolist()
    labels = cat_counts.index.tolist()

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
                    colors=[PIE_COLORS.get(lab, "#999999") for lab in labels],
                    line=dict(
                        color=["black" if w > 0 else "white" for w in marker_lines],
                        width=marker_lines,
                    ),
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(text=f"Risk categories for month {month_label}", x=0.5, xanchor="center"),
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )

    if highlight_label is not None and highlight_label in labels:
        fig.add_annotation(
            text=f"Highlighted: {highlight_label}",
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            showarrow=False,
            align="left",
            bgcolor="rgba(255,255,255,0.6)",
            bordercolor="black",
            borderwidth=1,
        )

    return fig
