# ==================================================================================
# charts_visualizer.py — Visualização Científica (Atualizado v59)
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io 

def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria um gráfico de linha com estética de publicação científica:
    - Fundo branco limpo.
    - Eixos emoldurados (box style).
    - Ticks externos visíveis.
    - Sem slider inferior.
    """
    variable_name = variable.split(" (")[0]
    
    fig = px.line(
        df,
        x='date',
        y='value',
        title=None,
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        markers=True
    )

    # ==========================================================
    # ESTILIZAÇÃO CIENTÍFICA
    # ==========================================================
    fig.update_layout(
        # Configuração do Eixo X
        xaxis=dict(
            showline=True,          # Mostra linha do eixo
            linecolor='black',      # Cor da linha do eixo
            linewidth=1,            # Espessura da linha
            ticks='outside',        # Ticks para fora
            ticklen=6,              # Comprimento do tick
            tickcolor='black',      # Cor do tick
            showgrid=True,          # Mostra a grade
            gridcolor='#E5E5E5',    # Grade cinza claro suave
            mirror=True,            # Espelha o eixo (cria a borda superior)
            
            # Remove o slider inferior (solicitado)
            rangeslider=dict(visible=False),
            
            # Mantém os botões de zoom temporal (opcional, útil para navegação)
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1a", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ]),
                bgcolor="white",
                bordercolor="#cccccc",
                borderwidth=1,
                x=0, y=1.1 # Posiciona botões levemente acima para não poluir
            )
        ),
        
        # Configuração do Eixo Y
        yaxis=dict(
            showline=True,
            linecolor='black',
            linewidth=1,
            ticks='outside',
            ticklen=6,
            tickcolor='black',
            showgrid=True,
            gridcolor='#E5E5E5',
            mirror=True,  # Espelha o eixo (cria a borda direita)
            zeroline=False # Remove linha zero destacada
        ),
        
        # Aparência Geral
        plot_bgcolor='white',   # Fundo da área do gráfico
        paper_bgcolor='white',  # Fundo externo
        font=dict(
            family="Arial, sans-serif",
            size=14,
            color="black"
        ),
        margin=dict(l=60, r=30, t=50, b=60), # Margens ajustadas
        height=450,
        hovermode="x unified" # Tooltip moderno unificado
    )
    
    # Ajuste fino da linha de dados
    fig.update_traces(
        line=dict(width=2.5, color='#1f77b4'), # Azul clássico, linha sólida
        marker=dict(size=7, symbol='circle', line=dict(width=1, color='white')), # Pontos com borda branca para destaque
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Valor:</b> %{y:.2f} " + f"{unit}"
    )

    return fig

def _convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """Converte DataFrame para Excel em memória."""
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return excel_buffer.getvalue()

def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    """
    Exibe o gráfico e as estatísticas.
    """
    
    # CSS para ajustar métricas
    st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 1.1rem; 
    }
    </style>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.warning("Não há dados disponíveis para gerar o gráfico.")
        return

    df_clean = df.copy()

    # Padronização de colunas (Robustez)
    if 'date' not in df_clean.columns:
        if 'system:time_start' in df_clean.columns:
            df_clean.rename(columns={'system:time_start': 'date'}, inplace=True)
        elif pd.api.types.is_datetime64_any_dtype(df_clean.iloc[:, 0]):
            df_clean.rename(columns={df_clean.columns[0]: 'date'}, inplace=True)
        else:
            st.warning("Erro nos dados: coluna de data não encontrada.")
            return

    if 'value' not in df_clean.columns:
         if len(df_clean.columns) > 1 and pd.api.types.is_numeric_dtype(df_clean.iloc[:, 1]):
             df_clean.rename(columns={df_clean.columns[1]: 'value'}, inplace=True)
         else:
            st.warning("Erro nos dados: coluna de valor não encontrada.")
            return

    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')
    df_clean = df_clean.dropna(subset=['date', 'value'])
    
    if df_clean.empty:
        st.warning("Nenhum dado válido encontrado.")
        return
        
    df_clean = df_clean.sort_values('date')

    # Gera e exibe o gráfico
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao plotar gráfico: {e}")
        return

    # Estatísticas
    st.markdown("#### Estatísticas do Período")
    
    media = df_clean['value'].mean()
    maximo = df_clean['value'].max()
    minimo = df_clean['value'].min()
    amplitude = maximo - minimo
    desvio_padrao = df_clean['value'].std()

    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Média", f"{media:.1f} {unit}")
    col2.metric("Máxima", f"{maximo:.1f} {unit}")
    col3.metric("Mínima", f"{minimo:.1f} {unit}")
    
    col4.metric(
        "Amplitude", 
        f"{amplitude:.1f} {unit}",
        help="Diferença entre o valor máximo e mínimo."
    )
    
    col5.metric(
        "Desvio Padrão", 
        f"{desvio_padrao:.1f}",
        help="Medida de dispersão dos dados em relação à média."
    )
    
    # Tabela e Exportação
    st.markdown("---")
    variable_name = variable.split(" (")[0]
    df_export = df_clean.rename(columns={'value': f'{variable_name} ({unit})'})
    
    if pd.api.types.is_datetime64tz_dtype(df_export['date']):
        df_export['date'] = df_export['date'].dt.tz_localize(None)
    
    st.subheader("Tabela de Dados") 
    df_display = df_export.copy()
    df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display, use_container_width=True, height=300)

    st.subheader("Exportar Tabela")
    
    file_name_safe = variable_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    
    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig', date_format='%d/%m/%Y')
    try: excel_data = _convert_df_to_excel(df_export)
    except: excel_data = None
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Exportar CSV", data=csv_data, file_name=f"serie_{file_name_safe}.csv", mime="text/csv", use_container_width=True)
    with c2:
        if excel_data:
            st.download_button("Exportar XLSX", data=excel_data, file_name=f"serie_{file_name_safe}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
