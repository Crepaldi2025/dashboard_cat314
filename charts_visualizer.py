# charts_visualizer.py
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
        title=f'Série Temporal de {variable_name}',
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
        )
    )
    return fig

def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    """
    Exibe um gráfico de série temporal interativo e uma explicação de seus controles.
    """
    if df.empty or 'date' not in df.columns or 'value' not in df.columns:
        st.warning("Não há dados disponíveis para gerar o gráfico para o período selecionado.")
        return

    # 1. Cria a figura do gráfico
    fig = _create_chart_figure(df, variable, unit)
    
    # 2. Exibe o gráfico no Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # 3. Exibe a caixa de informações com as instruções
    st.info(
        """
        **Dica:** Utilize os controles interativos do gráfico:
        - **Botões de Período (1m, 6m, 1a, Tudo):** Clique para aplicar um zoom rápido em períodos pré-definidos.
        - **Controle Deslizante Inferior:** Arraste as alças para selecionar um intervalo de datas personalizado.
        - **Passar o Mouse:** Posicione o cursor sobre a linha para ver a data e o valor exatos.
        """
    )