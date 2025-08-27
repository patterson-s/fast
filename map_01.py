#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthEnd

DEF_PARQUET = Path(__file__).resolve().parent / "FAST-cm" / "FAST-Forecast.parquet"

def load_dataframe(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    required = {"name", "isoab", "dates", "predicted", "cumulative_outcome_n", "outcome_p"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Parquet missing expected columns: {missing}")

    parsed = pd.to_datetime(df["dates"].astype(str), errors="coerce", infer_datetime_format=True)
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

def create_country_report_data(df_country: pd.DataFrame) -> Dict[str, Any]:
    if df_country.empty:
        return {}
        
    name = df_country["name"].iloc[0]
    iso = df_country["isoab"].iloc[0]
    horizon_start = df_country["_month"].min()
    horizon_end = df_country["_month"].max()
    
    total_pred = df_country["predicted"].sum()
    max_month_row = df_country.loc[df_country["predicted"].idxmax()]
    max_month = max_month_row["_month"]
    max_value = max_month_row["predicted"]
    
    p = df_country["outcome_p"].fillna(0.0)
    n = len(p)
    hi = (p >= 0.90).sum()
    mid = ((p >= 0.50) & (p < 0.90)).sum()
    low = ((p > 0.0) & (p < 0.50)).sum()
    zero = (p == 0.0).sum()
    
    monthly_data = df_country[["_month", "predicted", "cumulative_outcome_n", "outcome_p"]].copy()
    monthly_data["month_str"] = monthly_data["_month"].dt.strftime("%Y-%m")
    monthly_data["predicted_fmt"] = monthly_data["predicted"].apply(lambda x: f"{int(round(float(x))):,}")
    monthly_data["cumulative_fmt"] = monthly_data["cumulative_outcome_n"].apply(lambda x: f"{int(round(float(x))):,}")
    monthly_data["outcome_p_fmt"] = monthly_data["outcome_p"].apply(lambda x: f"{100.0*float(x):.1f}%" if pd.notna(x) else "0.0%")
    
    return {
        "name": name,
        "iso": iso,
        "horizon_start": horizon_start.strftime("%b %Y"),
        "horizon_end": horizon_end.strftime("%b %Y"),
        "total_predicted": f"{int(round(total_pred)):,}",
        "max_month": max_month.strftime("%b %Y"),
        "max_value": f"{int(round(max_value)):,}",
        "risk_high": f"{hi}/{n}",
        "risk_medium": f"{mid}/{n}",
        "risk_low": f"{low}/{n}",
        "risk_zero": f"{zero}/{n}",
        "monthly_data": monthly_data.to_dict('records')
    }

def resolve_country_from_iso(df: pd.DataFrame, iso3: str) -> Optional[pd.DataFrame]:
    if not iso3:
        return None
    iso_match = df[df["isoab"].str.upper() == iso3.upper()]
    return iso_match.copy() if len(iso_match) > 0 else None

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
        title={
            'text': "Conflict Forecast Map - Click Country for Details",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth'
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def create_app(df: pd.DataFrame) -> dash.Dash:
    app = dash.Dash(__name__)
    app.title = "FAST-cm Interactive Map"
    
    map_data = prepare_map_data(df)
    
    app.layout = html.Div([
        html.H1("FAST-cm Conflict Forecast Interactive Map", 
               style={'textAlign': 'center', 'color': '#333', 'marginBottom': '30px'}),
        
        dcc.Graph(
            id='world-map',
            figure=create_world_map(map_data),
            config={'displayModeBar': True}
        ),
        
        dcc.Store(id='country-data-store'),
        
        html.Div(id='country-modal', style={'display': 'none'}, children=[
            html.Div(
                style={
                    'position': 'fixed',
                    'top': '0',
                    'left': '0',
                    'width': '100%',
                    'height': '100%',
                    'backgroundColor': 'rgba(0,0,0,0.5)',
                    'zIndex': '1000',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center'
                },
                children=[
                    html.Div(
                        style={
                            'backgroundColor': 'white',
                            'padding': '20px',
                            'borderRadius': '10px',
                            'maxWidth': '800px',
                            'maxHeight': '80vh',
                            'overflow': 'auto',
                            'position': 'relative'
                        },
                        children=[
                            html.Button('×', 
                                      id='close-modal',
                                      style={
                                          'position': 'absolute',
                                          'top': '10px',
                                          'right': '15px',
                                          'background': 'none',
                                          'border': 'none',
                                          'fontSize': '24px',
                                          'cursor': 'pointer',
                                          'color': '#666'
                                      }),
                            html.Div(id='modal-content')
                        ]
                    )
                ]
            )
        ])
    ])
    
    @app.callback(
        [Output('country-modal', 'style'),
         Output('modal-content', 'children'),
         Output('country-data-store', 'data')],
        [Input('world-map', 'clickData'),
         Input('close-modal', 'n_clicks')]
    )
    def handle_map_interaction(clickData, close_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return {'display': 'none'}, [], {}
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'close-modal':
            return {'display': 'none'}, [], {}
        
        if trigger_id == 'world-map' and clickData:
            iso3 = clickData['points'][0]['location']
            df_country = resolve_country_from_iso(df, iso3)
            
            if df_country is None or df_country.empty:
                return {'display': 'none'}, [], {}
            
            report_data = create_country_report_data(df_country)
            
            modal_content = [
                html.H2(f"{report_data['name']} ({report_data['iso']})", 
                       style={'color': '#333', 'marginBottom': '20px'}),
                
                html.Div([
                    html.P([html.Strong("Forecast Horizon: "), f"{report_data['horizon_start']} → {report_data['horizon_end']}"]),
                    html.P([html.Strong("Total Predicted Fatalities: "), report_data['total_predicted']]),
                    html.P([html.Strong("Peak Monthly Forecast: "), f"{report_data['max_value']} ({report_data['max_month']})"]),
                ], style={'marginBottom': '20px'}),
                
                html.H4("Risk Profile (Pr[fatalities > threshold] by month)", 
                       style={'color': '#555', 'marginBottom': '10px'}),
                html.Ul([
                    html.Li([html.Strong("High (≥90%): "), report_data['risk_high']]),
                    html.Li([html.Strong("Medium (50-<90%): "), report_data['risk_medium']]),
                    html.Li([html.Strong("Low (>0-<50%): "), report_data['risk_low']]),
                    html.Li([html.Strong("Near-zero (=0%): "), report_data['risk_zero']]),
                ], style={'marginBottom': '20px'}),
                
                html.H4("Monthly Forecasts", style={'color': '#555', 'marginBottom': '10px'}),
                dash_table.DataTable(
                    data=report_data['monthly_data'],
                    columns=[
                        {"name": "Month", "id": "month_str"},
                        {"name": "Predicted", "id": "predicted_fmt"},
                        {"name": "Cumulative", "id": "cumulative_fmt"},
                        {"name": "Pr(>threshold)", "id": "outcome_p_fmt"}
                    ],
                    style_cell={'textAlign': 'center', 'padding': '10px'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data={'backgroundColor': '#ffffff'},
                    style_table={'overflowX': 'auto'}
                )
            ]
            
            return {'display': 'block'}, modal_content, report_data
        
        return {'display': 'none'}, [], {}
    
    return app

def main():
    parser = argparse.ArgumentParser(description="FAST-cm interactive map")
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
    app.run(debug=True)

if __name__ == "__main__":
    main()