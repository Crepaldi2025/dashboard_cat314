# ==================================================================================
# charts_visualizer.py — Visualização Científica com Exportação de Imagem (v61)
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
            spikemode='across', 
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
            spikemode='across', 
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
        hovermode="x" 
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

    # 1. Gera a Figura
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
    except Exception as e:
        st.error(f"Erro ao criar figura: {e}")
        return

    # 2. Exibe o Gráfico
    st.plotly_chart(fig, use_container_width=True)

    # 3. Botões de Exportação do Gráfico (PNG/JPG)
    # Nota: Requer 'kaleido' instalado (pip install kaleido)
    variable_clean = variable.split(" (")[0].lower().replace(" ", "_")
    
    col_img1, col_img2, col_void = st.columns([1, 1, 2])
    
    try:
        # Gera imagem em memória para evitar salvar em disco
        img_png = fig.to_image(format="png", width=1200, height=800, scale=2)
        img_jpg = fig.to_image(format="jpeg", width=1200, height=800, scale=2)
        
        with col_img1:
            st.download_button(
                label="📷 Baixar Gráfico (PNG)",
                data=img_png,
                file_name=f"grafico_{variable_clean}.png",
                mime="image/png",
                use_container_width=True
            )
        with col_img2:
            st.download_button(
                label="📷 Baixar Gráfico (JPG)",
                data=img_jpg,
                file_name=f"grafico_{variable_clean}.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
            
    except ValueError:
        # Fallback caso o engine kaleido não esteja instalado
        with col_img1:
            st.warning("Instale a biblioteca `kaleido` para habilitar downloads de imagem.")

    # 4. Legenda Explicativa
    st.markdown(
        """
        <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; border: 1px solid #ddd; font-size: 0.9em; color: #555; margin-top: 10px; margin-bottom: 20px;">
            <b>🖱️ Interação:</b> Passe o mouse sobre o gráfico para ver o valor exato e as linhas de referência.<br>
            <b>🔎 Zoom Rápido:</b> <code>1m</code> = Mês | <code>6m</code> = Semestre | <code>1a</code> = Ano | <code>Tudo</code> = Total.
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 5. Estatísticas
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
    
    # 6. Tabela e Exportação de Dados
    st.markdown("---")
    df_export = df_clean.rename(columns={'value': f'{variable.split(" (")[0]} ({unit})'})
    
    if pd.api.types.is_datetime64tz_dtype(df_export['date']):
        df_export['date'] = df_export['date'].dt.tz_localize(None)
    
    st.subheader("Tabela de Dados") 
    df_display = df_export.copy()
    df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display, use_container_width=True, height=300)

    st.subheader("Exportar Tabela")
    
    file_name_safe = variable_clean
    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig', date_format='%d/%m/%Y')
    try: excel_data = _convert_df_to_excel(df_export)
    except: excel_data = None
    
    cex1, cex2 = st.columns(2)
    with cex1: st.download_button("Exportar CSV (Dados)", data=csv_data, file_name=f"serie_{file_name_safe}.csv", mime="text/csv", use_container_width=True)
    with cex2: 
        if excel_data: st.download_button("Exportar XLSX (Dados)", data=excel_data, file_name=f"serie_{file_name_safe}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
