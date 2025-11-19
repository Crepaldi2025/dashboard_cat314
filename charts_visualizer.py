# ==================================================================================
# charts_visualizer.py — Visualização Científica com Crosshairs (v60)
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io 

def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria um gráfico de linha estilo científico com:
    - Crosshairs (linhas guia horizontal e vertical).
    - Eixos emoldurados.
    - Fundo branco.
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
    # ESTILIZAÇÃO CIENTÍFICA + CROSSHAIRS
    # ==========================================================
    fig.update_layout(
        # Configuração do Eixo X (Tempo)
        xaxis=dict(
            showline=True,          
            linecolor='black',      
            linewidth=1,            
            ticks='outside',        
            ticklen=6,              
            tickcolor='black',      
            showgrid=True,          
            gridcolor='#E5E5E5',    
            mirror=True,            
            
            # --- Configuração da Linha Guia (Spike/Crosshair) ---
            showspikes=True,
            spikemode='across', # Linha atravessa o gráfico todo
            spikesnap='cursor',
            spikethickness=1,
            spikecolor='#555555',
            spikedash='solid',
            # ----------------------------------------------------

            rangeslider=dict(visible=False), # Sem slider inferior
            
            # Botões de Zoom
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
                x=0, y=1.1
            )
        ),
        
        # Configuração do Eixo Y (Valor)
        yaxis=dict(
            showline=True,
            linecolor='black',
            linewidth=1,
            ticks='outside',
            ticklen=6,
            tickcolor='black',
            showgrid=True,
            gridcolor='#E5E5E5',
            mirror=True,  
            zeroline=False,
            
            # --- Configuração da Linha Horizontal (Crosshair) ---
            showspikes=True,
            spikemode='across', # Linha horizontal cruzando o gráfico
            spikethickness=1,
            spikecolor='#555555',
            spikedash='solid'
            # ----------------------------------------------------
        ),
        
        plot_bgcolor='white',   
        paper_bgcolor='white',  
        font=dict(family="Arial, sans-serif", size=14, color="black"),
        margin=dict(l=60, r=30, t=50, b=60),
        height=450,
        hovermode="x" # Mostra o tooltip do ponto mais próximo no eixo X
    )
    
    fig.update_traces(
        line=dict(width=2.5, color='#1f77b4'), 
        marker=dict(size=7, symbol='circle', line=dict(width=1, color='white')),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Valor:</b> %{y:.2f} " + f"{unit}"
    )

    return fig

def _convert_df_to_excel(df: pd.DataFrame) -> bytes:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return excel_buffer.getvalue()

def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str):
    # CSS para ajustar métricas
    st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.warning("Nenhum dado válido encontrado.")
        return

    df_clean = df.copy()

    # Padronização de colunas
    if 'date' not in df_clean.columns:
        if 'system:time_start' in df_clean.columns: df_clean.rename(columns={'system:time_start': 'date'}, inplace=True)
        elif pd.api.types.is_datetime64_any_dtype(df_clean.iloc[:, 0]): df_clean.rename(columns={df_clean.columns[0]: 'date'}, inplace=True)
        else: return

    if 'value' not in df_clean.columns:
         if len(df_clean.columns) > 1 and pd.api.types.is_numeric_dtype(df_clean.iloc[:, 1]):
             df_clean.rename(columns={df_clean.columns[1]: 'value'}, inplace=True)
         else: return

    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')
    df_clean = df_clean.dropna(subset=['date', 'value']).sort_values('date')

    # 1. Exibe o Gráfico
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao plotar gráfico: {e}")
        return

    # 2. Exibe a Legenda Explicativa (Logo abaixo do gráfico)
    st.markdown(
        """
        <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; border: 1px solid #ddd; font-size: 0.9em; color: #555; margin-bottom: 20px;">
            <b>🖱️ Interação:</b> Passe o mouse sobre o gráfico para ver o valor exato e as linhas de referência (horizontal e vertical).<br>
            <b>🔎 Zoom Rápido (Botões Superiores):</b> 
            <code>1m</code> = Último Mês | 
            <code>6m</code> = Últimos 6 Meses | 
            <code>1a</code> = Último Ano | 
            <code>Tudo</code> = Período Completo.
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 3. Estatísticas
    st.markdown("#### Estatísticas do Período")
    
    media = df_clean['value'].mean()
    maximo = df_clean['value'].max()
    minimo = df_clean['value'].min()
    amplitude = maximo - minimo
    desvio_padrao = df_clean['value'].std()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Média", f"{media:.1f} {unit}")
    c2.metric("Máxima", f"{maximo:.1f} {unit}")
    c3.metric("Mínima", f"{minimo:.1f} {unit}")
    c4.metric("Amplitude", f"{amplitude:.1f} {unit}", help="Diferença entre Máximo e Mínimo.")
    c5.metric("Desvio Padrão", f"{desvio_padrao:.1f}", help="Dispersão dos dados em relação à média.")
    
    # 4. Tabela e Exportação
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
    
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1: st.download_button("Exportar CSV", data=csv_data, file_name=f"serie_{file_name_safe}.csv", mime="text/csv", use_container_width=True)
    with col_ex2: 
        if excel_data: st.download_button("Exportar XLSX", data=excel_data, file_name=f"serie_{file_name_safe}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
