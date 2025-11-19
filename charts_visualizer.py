# ==================================================================================
# charts_visualizer.py — Séries temporais do Clima-Cast-Crepaldi (Corrigido v33)
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io 

def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    """
    Cria a figura do gráfico de linha interativo com estilo detalhado.
    (v32) - Fontes maiores, eixos marcados e visual profissional.
    """
    variable_name = variable.split(" (")[0]
    
    # Criação básica do gráfico
    fig = px.line(
        df,
        x='date',
        y='value',
        title=None, 
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        template="plotly_white",
        markers=True
    )

    # =========================================================
    # CUSTOMIZAÇÃO DETALHADA DO VISUAL
    # =========================================================
    fig.update_layout(
        # Aumenta a margem para não cortar textos grandes
        margin=dict(l=20, r=20, t=30, b=20),
        
        # Fundo do gráfico
        plot_bgcolor="rgba(255, 255, 255, 0.9)",
        paper_bgcolor="rgba(255, 255, 255, 0.9)",

        # Títulos e rótulos
        font=dict(family="Inter, sans-serif", size=14, color="#333"),
        xaxis_title=dict(font=dict(size=16)),
        yaxis_title=dict(font=dict(size=16)),
        
        # Legenda (se houver)
        showlegend=False
    )
    
    # Customização do eixo X
    fig.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#e0e0e0',
        linecolor='#ccc',
        linewidth=2,
        zeroline=False,
        tickfont=dict(size=12),
        rangeslider_visible=True, # Adiciona slider de zoom
        rangeselector=dict( # Adiciona botões de seleção de período
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1a", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    # Customização do eixo Y
    fig.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#e0e0e0',
        linecolor='#ccc',
        linewidth=2,
        zeroline=False,
        tickfont=dict(size=12),
    )

    # Customização da linha principal
    fig.update_traces(
        line=dict(width=3, color='#4CAF50'), # Linha mais espessa e verde
        marker=dict(size=5, symbol='circle', line=dict(width=1, color='#4CAF50')),
        mode='lines+markers'
    )

    return fig

def _convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """Converte um DataFrame para um objeto BytesIO do Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()


def _render_data_and_chart(df: pd.DataFrame, variable: str, unit: str, tipo_periodo: str):
    """
    Recebe os dados brutos e renderiza o gráfico, a tabela e os botões de exportação.
    (v33) - Adicionada checagem df_export.empty para evitar StreamlitAPIException no download_button.
    """
    if df.empty:
        st.warning("Não foi possível gerar a série temporal. Verifique o período e a localização selecionados.")
        return

    variable_name = variable.split(" (")[0]
    
    # ----------------------------------------------------
    # 1. PRÉ-PROCESSAMENTO E PREPARAÇÃO DO DATAFRAME
    # ----------------------------------------------------
    df_clean = df.copy()
    
    # Verifica se a banda é Vento (vetorial) e calcula a magnitude
    is_wind_vector = variable_name == "Vento (10m)"

    if is_wind_vector:
        # Renomeia as colunas u e v para facilitar o cálculo
        df_clean = df_clean.rename(columns={'u_component_of_wind_10m': 'u', 'v_component_of_wind_10m': 'v'})
        # Calcula a magnitude do vento
        df_clean['value'] = (df_clean['u']**2 + df_clean['v']**2)**0.5
        # Mantém a data e a nova coluna 'value'
        df_clean = df_clean[['date', 'value']]
    else:
        # Para variáveis escalares, apenas renomeia 'value' para consistência
        df_clean = df_clean.rename(columns={variable: 'value'})
        df_clean = df_clean[['date', 'value']] # Garante que apenas date e value fiquem
    
    # Cria o DataFrame para exportação, renomeando a coluna 'value' com a unidade
    df_export = df_clean.rename(columns={'value': f'{variable_name} ({unit})'})
    
    # Remove fuso horário se existir (para exportar limpo)
    if df_export['date'].dt.tz is not None:
        df_export['date'] = df_export['date'].dt.tz_localize(None) 
    
    # --- CORREÇÃO V33: CHECAGEM DE DADOS PARA EVITAR StreamlitAPIException NO st.download_button ---
    if df_export.empty:
        st.warning("Não há dados disponíveis para o período e localização selecionados. Por favor, ajuste os parâmetros.")
        return
    # ----------------------------------------------------------------------------------------------

    # ----------------------------------------------------
    # 2. TABELA DE DADOS
    # ----------------------------------------------------
    st.subheader("Tabela de Dados") 
    df_display = df_export.copy()
    
    # --- A CORREÇÃO ESTÁ NESTA LINHA ABAIXO (adicionado .dt) ---
    df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_display, use_container_width=True, height=300)

    st.subheader("Exportar Tabela")
    
    # ----------------------------------------------------
    # 3. BOTÕES DE DOWNLOAD
    # ----------------------------------------------------
    file_name_safe = variable_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    
    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig', date_format='%d/%m/%Y')
    excel_data = _convert_df_to_excel(df_export)
    
    col_btn_1, col_btn_2 = st.columns(2)
    
    with col_btn_1:
        st.download_button(
            label="Exportar para CSV",
            data=csv_data,
            file_name=f"serie_temporal_{file_name_safe}_{tipo_periodo}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with col_btn_2:
        st.download_button(
            label="Exportar para XLSX (Excel)",
            data=excel_data,
            file_name=f"serie_temporal_{file_name_safe}_{tipo_periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    # ----------------------------------------------------
    # 4. GRÁFICO DE SÉRIE TEMPORAL
    # ----------------------------------------------------
    st.markdown("---")
    st.subheader(f"Série Temporal: {variable_name} ({unit})")
    
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao gerar o gráfico: {e}")

# ==================================================================================
# FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO (Chamada do main.py)
# ==================================================================================

def _render_results_page(results):
    """
    (v33) - Renderiza a página de resultados, que foi populada no session_state.
    """
    if results is None:
        return
    
    # 1. Exibe a localização analisada
    if results.get('local_name'):
        st.success(f"Análise Concluída para: **{results['local_name']}**")
    
    # 2. Cria as abas de visualização
    tab_mapa, tab_serie = st.tabs(["Mapa Interativo", "Série Temporal"])
    
    with tab_mapa:
        # O mapa é renderizado em map_visualizer, se existir no results
        map_html = results.get('map_html')
        map_title = results.get('map_title')

        if map_html:
            st.markdown(f"**{map_title}**")
            # Renderiza o mapa Folium/geemap
            st.components.v1.html(map_html, height=550, scrolling=False)
            
            # Botões de download do mapa
            if 'map_download_data' in results:
                
                download_data = results['map_download_data']
                
                col_img_1, col_img_2, col_img_3 = st.columns(3)
                
                with col_img_1:
                    st.download_button(
                        label="Download do Mapa (PNG)",
                        data=download_data['png']['data'],
                        file_name=download_data['png']['filename'],
                        mime=download_data['png']['mime'],
                        use_container_width=True
                    )
                with col_img_2:
                    st.download_button(
                        label="Download do Mapa (JPEG)",
                        data=download_data['jpeg']['data'],
                        file_name=download_data['jpeg']['filename'],
                        mime=download_data['jpeg']['mime'],
                        use_container_width=True
                    )
                with col_img_3:
                     st.download_button(
                        label="Download do Mapa (TIFF)",
                        data=download_data['tiff']['data'],
                        file_name=download_data['tiff']['filename'],
                        mime=download_data['tiff']['mime'],
                        use_container_width=True
                    )
        else:
             st.info("O Mapa Temático não foi gerado ou não está disponível.")
        
    with tab_serie:
        # A série temporal é renderizada por _render_data_and_chart
        if 'time_series_data' in results and not results['time_series_data'].empty:
            _render_data_and_chart(
                df=results['time_series_data'],
                variable=results['variable_label'],
                unit=results['unit_label'],
                tipo_periodo=st.session_state.tipo_periodo
            )
        else:
            st.info("A Série Temporal não foi gerada ou não há dados para o período e localização.")

def render_results_if_available(session_state):
    """
    Função de conveniência chamada por main.py.
    """
    if session_state.get("analysis_results") is not None:
        _render_results_page(session_state.analysis_results)
    else:
        # Se os resultados foram limpos ou não existem, apenas retorna.
        return
