# ==================================================================================
# charts_visualizer.py — Clima-Cast-Crepaldi (séries com extremos)
# ==================================================================================
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def _format_axis(unit: str) -> str:
    return f"{unit}" if unit else ""

def display_time_series_chart(df: pd.DataFrame, variavel: str, unit: str):
    """
    Desenha a série temporal. Se houver colunas ['mean','p95','max'],
    plota as três curvas; caso contrário, usa a coluna 'value' (modo legado).
    """
    if df is None or df.empty:
        st.warning("Sem dados para o período selecionado.")
        return

    # Garante tipo datetime
    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    # Caso 1 — Nova versão com estatísticas espaciais
    has_extremos = all(col in df.columns for col in ["mean", "p95", "max"])

    if has_extremos:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["date"], y=df["mean"],
            name="Média espacial",
            mode="lines",
            line=dict(width=2, color="#4F6BED")
        ))
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["p95"],
            name="Percentil 95",
            mode="lines",
            line=dict(width=2, color="#FFA500")
        ))
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["max"],
            name="Máximo (pixel)",
            mode="lines",
            line=dict(width=2, color="#D62728")
        ))

        fig.update_layout(
            title=f"Série Temporal de {variavel}",
            xaxis_title="Data",
            yaxis_title=f"{variavel} ({_format_axis(unit)})",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=40, r=20, t=60, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
        return

    # Caso 2 — Modo legado (apenas coluna 'value')
    if "value" in df.columns:
        fig = px.line(
            df, x="date", y="value",
            title=f"Série Temporal de {variavel}",
            labels={"date": "Data", "value": f"{variavel} ({_format_axis(unit)})"}
        )
        fig.update_traces(line=dict(width=2, color="#4F6BED"))
        st.plotly_chart(fig, use_container_width=True)
        return

    # Se não bateu nenhum caso
    st.warning("Estrutura de dados inesperada para a série temporal.")
