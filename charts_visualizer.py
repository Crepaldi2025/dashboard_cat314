# ==================================================================================
# charts_visualizer.py — Clima-Cast-Crepaldi (versão estável)
# ==================================================================================
import streamlit as st
import plotly.express as px
import pandas as pd

def display_time_series_chart(df, variavel, unit):
    """Exibe série temporal simples (uma linha)."""
    if df is None or df.empty:
        st.warning("Sem dados para o período selecionado.")
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    fig = px.line(
        df,
        x="date",
        y="value",
        title=f"Série Temporal de {variavel}",
        labels={"date": "Data", "value": f"{variavel} ({unit})"},
    )
    fig.update_traces(line=dict(width=2, color="#4F6BED"))
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_title="Data",
        yaxis_title=f"{variavel} ({unit})"
    )
    st.plotly_chart(fig, use_container_width=True)
