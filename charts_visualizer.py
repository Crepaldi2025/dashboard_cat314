# ==================================================================================
# charts_visualizer.py — Clima-Cast-Crepaldi (versão estável restaurada)
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------------------------------
# Função interna para criar o gráfico
# --------------------------------------------------------------------------
def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria a figura do gráfico de linha interativo de série temporal usando Plotly.
    """
    variable_name = variable.split(" (")[0]

    fig = px.line(
        df,
        x="date",
        y="value",
        title=f"Série Temporal de {variable_name}",
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        template="plotly_white"
    )

    fig.update_layout(
        title_x=0.5,
        title_font=dict(size=18, color="#2c3e50"),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            title="Data",
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1a", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ])
            )
        ),
        yaxis=dict(title=f"{variable_name} ({unit})")
    )

    return fig

# --------------------------------------------------------------------------
# Função principal para exibir o gráfico
# --------------------------------------------------------------------------
def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    """
    Exibe um gráfico de série temporal interativo e instruções de uso.
    """
    if df.empty or "date" not in df.columns or "value" not in df.columns:
        st.warning("Não há dados disponíveis para gerar o gráfico para o período selecionado.")
        return

    fig = _create_chart_figure(df, variable, unit)
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        """
        **Dica:**  
        - Use os botões acima do gráfico para aplicar zoom rápido em períodos predefinidos.  
        - Arraste o controle deslizante inferior para selecionar intervalos personalizados.  
        - Passe o mouse sobre a linha para visualizar valores exatos.  
        """
    )
