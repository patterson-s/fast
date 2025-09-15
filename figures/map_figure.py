from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def make_world_map(map_data: pd.DataFrame) -> go.Figure:
    if map_data.empty:
        return go.Figure().add_annotation(
            text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )

    fig = px.choropleth(
        map_data,
        locations="iso3",
        hover_name="name",
        hover_data={
            "total_predicted": ":,",
            "horizon_start": True,
            "horizon_end": True,
            "iso3": False,
            "log_predicted": False,
        },
        color="log_predicted",
        color_continuous_scale="Reds",
        labels={
            "log_predicted": "Log(Total Predicted + 1)",
            "total_predicted": "Total Predicted Fatalities",
            "horizon_start": "Horizon Start",
            "horizon_end": "Horizon End",
        },
    )
    fig.update_layout(
        title={"text": "Conflict Forecast Map - Click a country", "x": 0.5, "xanchor": "center", "font": {"size": 20}},
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig
