# ==================================================================================
# charts_visualizer.py — Séries temporais do Clima-Cast-Crepaldi (Corrigido v29)
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io 

# --- INÍCIO DA CORREÇÃO v29 ---
def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria a figura do gráfico de linha interativo de série temporal usando Plotly.
    (v29) - Título removido, pois agora é gerenciado pelo main.py.
    """
    variable_name = variable.split(" (")[0]
    
    fig = px.line(
        df,
        x='date',
        y='value',
        title=None, # <-- Título removido daqui
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        template="plotly_white",
        markers=True
    )
# --- FIM DA CORREÇÃO v29 ---

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
        margin=dict(l=10, r=10, t=20, b=10), # <-- Margem do topo diminuída
        height=420
    )
    
    fig.update_traces(hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Valor:</b> %{y:.2f} " + f"{unit}")

    return fig

# --- INÍCIO DA CORREÇÃO v29 (Adicionando helper) ---
def _convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """
    Converte um DataFrame para um arquivo Excel (XLSX) em memória.
    """
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return excel_buffer.getvalue()
# --- FIM DA CORREÇÃO v29 ---


def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    """
    Exibe um gráfico de série temporal interativo e uma explicação de seus controles.
    """
    
    # CSS para diminuir a fonte da métrica (v18)
    st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem; 
    }
    </style>
    """, unsafe_allow_html=True)
    
    
    # ======================================================
    # Pré-processamento seguro do DataFrame (Idêntico)
    # ======================================================
    if df is None or df.empty:
        st.warning("Não há dados disponíveis para gerar o gráfico para o período selecionado.")
        return

    df_clean = df.copy()

    if 'date' not in df_clean.columns:
        if 'system:time_start' in df_clean.columns:
            df_clean.rename(columns={'system:time_start': 'date'}, inplace=True)
        elif pd.api.types.is_datetime64_any_dtype(df_clean.iloc[:, 0]):
            df_clean.rename(columns={df_clean.columns[0]: 'date'}, inplace=True)
        else:
            st.warning("Coluna de datas não encontrada nos dados retornados.")
            return

    if 'value' not in df_clean.columns:
         if len(df_clean.columns) > 1 and pd.api.types.is_numeric_dtype(df_clean.iloc[:, 1]):
             df_clean.rename(columns={df_clean.columns[1]: 'value'}, inplace=True)
         else:
            st.warning("Coluna 'value' não encontrada nos dados.")
            return

    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')
    df_clean = df_clean.dropna(subset=['date', 'value'])
    if df_clean.empty:
        st.warning("Nenhum dado válido para exibir a série temporal.")
        return
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

    # ======================================================
    # Estatísticas (Idêntico)
    # ======================================================
    st.markdown("#### Estatísticas do Período")
    col1, col2, col3 = st.columns(3)
    col1.metric("Média", f"{df_clean['value'].mean():.1f} {unit}")
    col2.metric("Máxima", f"{df_clean['value'].max():.1f} {unit}")
    col3.metric("Mínima", f"{df_clean['value'].min():.1f} {unit}")

    # ======================================================
    # Caixa de instruções (Idêntico)
    # ======================================================
    st.info(
        """
        **Dica:** Utilize os controles interativos do gráfico:
        - **Botões de Período (1m, 6m, 1a, Tudo):** Aplique zoom rápido em períodos pré-definidos.  
        - **Controle Deslizante Inferior:** Ajuste manualmente o intervalo de datas.  
        - **Passe o Mouse:** Veja a data e o valor exatos para cada ponto da série.
        """
    )
    
    # ======================================================
    # Tabela de Dados e Exportação (Adicionado v29)
    # ======================================================
    st.markdown("---")
    
    variable_name = variable.split(" (")[0]
    df_export = df_clean.rename(columns={'value': f'{variable_name} ({unit})'})
    df_export['date'] = df_export['date'].dt.tz_localize(None) 
    
    st.subheader("Tabela de Dados") 
    df_display = df_export.copy()
    df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display, use_container_width=True, height=300)

    st.subheader("Exportar Tabela")
    
    file_name_safe = variable_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    
    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig', date_format='%d/%m/%Y')
    excel_data = _convert_df_to_excel(df_export)
    
    col_btn_1, col_btn_2 = st.columns(2)
    
    with col_btn_1:
        st.download_button(
            label="Exportar para CSV",
            data=csv_data,
            file_name=f"serie_temporal_{file_name_safe}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with col_btn_2:
        st.download_button(
            label="Exportar para XLSX (Excel)",
            data=excel_data,
            file_name=f"serie_temporal_{file_name_safe}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

