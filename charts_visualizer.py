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
    # Remove a unidade (ex: "Temperatura (2m)") para o título
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
        template="plotly_white",
        markers=True # Adiciona marcadores para melhor visualização de pontos individuais
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
    
    # Melhora a interatividade do 'hover'
    fig.update_traces(hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Valor:</b> %{y:.2f} " + f"{unit}")

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
    df_clean = df.copy()

    # Renomeia colunas inesperadas (caso venham de GEE como 'system:time_start')
    if 'date' not in df_clean.columns:
        if 'system:time_start' in df_clean.columns:
            df_clean.rename(columns={'system:time_start': 'date'}, inplace=True)
        else:
            # Tenta usar a primeira coluna se for do tipo datetime
            if pd.api.types.is_datetime64_any_dtype(df_clean.iloc[:, 0]):
                df_clean.rename(columns={df_clean.columns[0]: 'date'}, inplace=True)
            else:
                st.warning("Coluna de datas não encontrada nos dados retornados.")
                return

    # Garante que a coluna 'value' exista
    if 'value' not in df_clean.columns:
         if len(df_clean.columns) > 1 and pd.api.types.is_numeric_dtype(df_clean.iloc[:, 1]):
             df_clean.rename(columns={df_clean.columns[1]: 'value'}, inplace=True)
         else:
            st.warning("Coluna 'value' não encontrada nos dados.")
            return

    # Conversão de tipos
    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')

    # Remove registros inválidos
    df_clean = df_clean.dropna(subset=['date', 'value'])
    if df_clean.empty:
        st.warning("Nenhum dado válido para exibir a série temporal.")
        return

    # Ordena cronologicamente
    df_clean = df_clean.sort_values('date')

    # ======================================================
    # Geração e exibição do gráfico
    # ======================================================
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao gerar o gráfico Plotly: {e}")
        return

    # =Amelhoria: Mostrar estatísticas básicas
    st.markdown("#### Estatísticas do Período")
    col1, col2, col3 = st.columns(3)
    col1.metric("Média", f"{df_clean['value'].mean():.2f} {unit}")
    col2.metric("Máxima", f"{df_clean['value'].max():.2f} {unit}")
    col3.metric("Mínima", f"{df_clean['value'].min():.2f} {unit}")


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