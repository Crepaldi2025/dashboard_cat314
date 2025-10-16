# main.py
import streamlit as st
import ui_antigo
import gee_handler
import map_visualizer
import charts_visualizer
import ee
import utils
import requests
import io
import pandas as pd
import copy
import locale

# Define o locale para Português do Brasil para todo o script.
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        # Fallback para sistemas Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Nomes de meses podem aparecer em inglês.")

def initialize_gee():
    """Tenta inicializar a conexão com o Google Earth Engine."""
    try:
        PROJECT_ID = 'gee-crepaldi-2025' 
        ee.Initialize(project=PROJECT_ID)
        return True
    except Exception as e:
        st.error(f"Falha ao conectar com o Google Earth Engine: {e}")
        return False

def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""
    with st.spinner("Processando dados no Google Earth Engine..."):
        geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
        if not geometry:
            st.error("Não foi possível definir a geometria da área de interesse. Verifique os filtros de localização.")
            return

        start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
        if not (start_date and end_date):
            st.error("Período de análise inválido.")
            return

        variable_config = gee_handler.ERA5_VARS[st.session_state.variavel]
        
        # Lógica para decidir se a análise é para Mapas ou Séries Temporais
        if st.session_state.nav_option == "Mapas":
            ee_image = gee_handler.get_era5_image(st.session_state.variavel, start_date, end_date, geometry)
            if not ee_image: return
            
            final_vis_params = copy.deepcopy(variable_config['vis_params'])
            if st.session_state.variavel == "Precipitação Total" and st.session_state.tipo_periodo == "Anual":
                final_vis_params['max'] = 3000

            st.subheader("Resultado da Análise")
            if st.session_state.map_type == "Estático":
                png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(ee_image, feature, final_vis_params, variable_config['unit'])
                if not (png_url and jpg_url and colorbar_img): return
                st.image(png_url, caption="Mapa Estático Gerado")
                st.image(colorbar_img, caption="Legenda", width=600)
                with st.expander("Opções de Exportação de Mapa"):
                    map_btn1, map_btn2 = st.columns(2)
                    with map_btn1:
                        st.download_button(label="Exportar (PNG)", data=requests.get(png_url).content, file_name="mapa.png", mime="image/png", use_container_width=True)
                    with map_btn2:
                        st.download_button(label="Exportar (JPEG)", data=requests.get(jpg_url).content, file_name="mapa.jpeg", mime="image/jpeg", use_container_width=True)
            elif st.session_state.map_type == "Interativo":
                map_visualizer.create_interactive_map(ee_image, feature, final_vis_params, variable_config['unit'])
            
            with st.expander("Tabela de Dados Amostrados"):
                df_table = gee_handler.get_sampled_data_as_dataframe(ee_image, geometry, st.session_state.variavel)
                if not df_table.empty:
                    st.dataframe(df_table)
                    tbl_btn1, tbl_btn2 = st.columns(2)
                    with tbl_btn1:
                        st.download_button(label="Exportar (CSV)", data=df_table.to_csv(index=False).encode('utf-8'), file_name="dados_mapa.csv", mime="text/csv", use_container_width=True)
                    with tbl_btn2:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_table.to_excel(writer, index=False, sheet_name='Dados')
                        st.download_button(label="Exportar (XLSX)", data=output.getvalue(), file_name="dados_mapa.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.warning("Não foi possível amostrar dados para a tabela.")

        elif st.session_state.nav_option == "Séries Temporais":
            df_series = gee_handler.get_time_series_data(st.session_state.variavel, start_date, end_date, geometry)
            
            st.subheader("Resultado da Análise")
            charts_visualizer.display_time_series_chart(df_series, st.session_state.variavel, variable_config['unit'])

            if not df_series.empty:
                with st.expander("Exportar Dados da Série Temporal"):
                    st.dataframe(df_series)
                    tbl_btn1, tbl_btn2 = st.columns(2)
                    with tbl_btn1:
                        st.download_button(label="Exportar (CSV)", data=df_series.to_csv(index=False).encode('utf-8'), file_name="dados_serie_temporal.csv", mime="text/csv", use_container_width=True)
                    with tbl_btn2:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_series.to_excel(writer, index=False, sheet_name='Dados')
                        st.download_button(label="Exportar (XLSX)", data=output.getvalue(), file_name="dados_serie_temporal.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def main():
    """Função principal que organiza e executa a aplicação Streamlit."""

    from gee_handler import inicializar_gee

    inicializar_gee()

    ui_antigo.configurar_pagina()
    if not initialize_gee(): return

    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui_antigo.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui_antigo.renderizar_pagina_sobre()
    else:
        # Etapa de exibição dos resultados (após validação)
        if st.session_state.get('area_validada', False):
            ui_antigo.renderizar_pagina_principal(opcao_menu)
            ui_antigo.renderizar_resumo_selecao()
            run_full_analysis()
        
        # Etapa de confirmação da área (se necessário)
        elif st.session_state.get('show_confirmation_map', False):
            ui_antigo.renderizar_pagina_principal(opcao_menu)
            ui_antigo.renderizar_resumo_selecao()
            tipo_loc = st.session_state.get('tipo_localizacao')
            
            if tipo_loc == "Círculo (Lat/Lon/Raio)":
                map_visualizer.display_circle_map(st.session_state.latitude, st.session_state.longitude, st.session_state.raio)
                ui_antigo.renderizar_validacao_mapa()
            elif tipo_loc == "Polígono":
                map_visualizer.display_polygon_draw_map()
                ui_antigo.renderizar_validacao_mapa()
        
        # Gatilho inicial, após clicar em "Gerar Análise"
        elif st.session_state.get('analysis_triggered', False):
            st.session_state.analysis_triggered = False # Consome o gatilho
            tipo_loc = st.session_state.get('tipo_localizacao')
            if tipo_loc in ["Estado", "Município"]:
                st.session_state.area_validada = True
            else:
                st.session_state.show_confirmation_map = True
            st.rerun()
            
        # Tela inicial padrão
        else:
            ui_antigo.renderizar_pagina_principal(opcao_menu)

if __name__ == "__main__":
    main()