# ==================================================================================
# charts_visualizer.py — Séries temporais do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px


def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria a figura do gráfico de linha interativo de série temporal usando Plotly.
    (Função interna, indicada pelo underscore no início do nome)
    """
    variable_name = variable.split(" (")[0]

    fig = px.line(
        df,
        x='date',
        y='value',
        title=f"Série Temporal de {variable_name}",
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        template="plotly_white"
    )

    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1a", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        ),
        margin=dict(l=10, r=10, t=45, b=10),
        height=420
    )

    return fig


def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    """
    Exibe um gráfico de série temporal interativo e uma explicação de seus controles.
    """
    # ======================================================
    # Pré-processamento seguro do DataFrame
    # ======================================================
    if df is None or df.empty:
        st.warning("Não há dados disponíveis para gerar o gráfico para o período selecionado.")
        return

    # Corrige possíveis problemas de colunas ou formatos
    df = df.copy()

    # Renomeia colunas inesperadas (caso venham de GEE como 'system:time_start')
    if 'date' not in df.columns:
        if 'system:time_start' in df.columns:
            df.rename(columns={'system:time_start': 'date'}, inplace=True)
        else:
            st.warning("Coluna de datas não encontrada nos dados retornados.")
            return

    # Conversão de tipos
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Remove registros inválidos
    df = df.dropna(subset=['date', 'value'])
    if df.empty:
        st.warning("Nenhum dado válido para exibir a série temporal.")
        return

    # Ordena cronologicamente
    df = df.sort_values('date')

    # ======================================================
    # Geração e exibição do gráfico
    # ======================================================
    fig = _create_chart_figure(df, variable, unit)
    st.plotly_chart(fig, use_container_width=True)

    # ======================================================
    # Caixa de instruções
    # ======================================================
    st.info(
        """
        **Dica:** Utilize os controles interativos do gráfico:
        - **Botões de Período (1m, 6m, 1a, Tudo):** Aplique zoom rápido em períodos pré-definidos.  
        - **Controle Deslizante Inferior:** Ajuste manualmente o intervalo de datas.  
        - **Passe o Mouse:** Veja a data e o valor exatos para cada ponto da série.
        """
    )
