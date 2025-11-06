# ==================================================================================
# main.py — Aplicativo principal do Clima-Cast-Crepaldi (versão corrigida)
# ==================================================================================
import streamlit as st
import ui
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

# ==================================================================================
# CONFIGURAÇÃO DE LOCALE
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Nomes de meses podem aparecer em inglês.")


# ==================================================================================
# EXECUÇÃO COMPLETA — MÓDULO DE ANÁLISE
# ==================================================================================
def run_full_analysis():
    """Executa a lógica principal de análise, conforme aba e tipo de mapa."""

    tipo_aba = st.session_state.get("nav_option", "Mapas")
    tipo_mapa = st.session_state.get("map_type", "Interativo")
    variavel = st.session_state.variavel

    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry:
        st.error("❌ Não foi possível definir a geometria da área de interesse.")
        return

    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.error("⚠️ Período de análise inválido.")
        return

    variable_config = gee_handler.ERA5_VARS[variavel]

    # Apenas quando a aba é MAPAS
    if tipo_aba == "Mapas":
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if not ee_image:
            st.warning("Não há dados disponíveis para o período selecionado.")
            return

        st.markdown("---")
        st.subheader("Resultado da Análise")
        ui.renderizar_resumo_selecao()

        final_vis_params = copy.deepcopy(variable_config["vis_params"])

        if tipo_mapa == "Estático":
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, final_vis_params, variable_config["unit"]
            )
            if png_url:
                st.image(png_url, caption="Mapa Estático Gerado", use_container_width=True)
            if colorbar_img:
                st.image(colorbar_img, caption="Legenda", width=600)

            st.markdown("### Exportar Mapas")
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Exportar (PNG)",
                    data=requests.get(png_url).content,
                    file_name="mapa.png",
                    mime="image/png",
                    use_container_width=True
                )
            with col2:
                st.download_button(
                    label="Exportar (JPEG)",
                    data=requests.get(jpg_url).content,
                    file_name="mapa.jpeg",
                    mime="image/jpeg",
                    use_container_width=True
                )

        elif tipo_mapa == "Interativo":
            map_visualizer.create_interactive_map(
                ee_image, feature, final_vis_params, variable_config["unit"]
            )

    # Apenas quando a aba é SÉRIES TEMPORAIS
    elif tipo_aba == "Séries Temporais":
        st.markdown("---")
        st.subheader("Resultado da Análise")
        ui.renderizar_resumo_selecao()

        df_series = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        charts_visualizer.display_time_series_chart(df_series, variavel, variable_config["unit"])

    # Página SOBRE não executa análise
    elif tipo_aba == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()


# ==================================================================================
# FUNÇÃO PRINCIPAL
# ==================================================================================
def main():
    """Organiza a execução geral do aplicativo."""
    from gee_handler import inicializar_gee
    inicializar_gee()

    ui.configurar_pagina()
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    # Exibe conforme estado da sessão
    if st.session_state.get('analysis_triggered', False):
        st.session_state.analysis_triggered = False
        st.session_state.area_validada = True
        st.rerun()

    if st.session_state.get('area_validada', False):
        ui.renderizar_pagina_principal(opcao_menu)
        run_full_analysis()

    elif st.session_state.get('show_confirmation_map', False):
        ui.renderizar_pagina_principal(opcao_menu)
        tipo_loc = st.session_state.get('tipo_localizacao')
        if tipo_loc == "Círculo (Lat/Lon/Raio)":
            map_visualizer.display_circle_map(st.session_state.latitude, st.session_state.longitude, st.session_state.raio)
            ui.renderizar_validacao_mapa()
        elif tipo_loc == "Polígono":
            map_visualizer.display_polygon_draw_map()
            ui.renderizar_validacao_mapa()

    else:
        ui.renderizar_pagina_principal(opcao_menu)


# ==================================================================================
# EXECUÇÃO DIRETA
# ==================================================================================
if __name__ == "__main__":
    main()
