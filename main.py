# ==================================================================================
# main.py — Clima-Cast-Crepaldi (versão estável final)
# ==================================================================================
import streamlit as st
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import utils
import copy
import locale
import base64
import requests


# ---------------------- CONFIGURAÇÃO DE LOCALE ----------------------
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        pass


# ---------------------- FUNÇÃO PRINCIPAL DE ANÁLISE ----------------------
def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    # Geometria da área selecionada
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry:
        st.warning("Selecione uma área de interesse válida no painel à esquerda.")
        return

    # Período
    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    # Variável ERA5
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg:
        st.error("Variável não reconhecida.")
        return

    st.markdown("---")
    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao()

    # -------------------- Aba MAPAS --------------------
    if aba == "Mapas":
        tipo_mapa = st.session_state.get("map_type", "Interativo")
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None:
            st.warning("Não há dados disponíveis para o período selecionado.")
            return

        vis_params = copy.deepcopy(var_cfg["vis_params"])

        if tipo_mapa == "Interativo":
            map_visualizer.create_interactive_map(ee_image, feature, vis_params, var_cfg["unit"])

        elif tipo_mapa == "Estático":
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, vis_params, var_cfg["unit"]
            )

            if png_url:
                st.image(png_url, caption="Mapa Estático", use_container_width=True)
            if colorbar_img:
                st.image(colorbar_img, caption="Legenda", use_container_width=True)

            st.markdown("### Exportar Mapas")
            if png_url:
                st.download_button(
                    "Exportar (PNG)",
                    data=base64.b64decode(png_url.split(",")[1]),
                    file_name="mapa.png",
                    mime="image/png",
                    use_container_width=True,
                )
            if jpg_url:
                st.download_button(
                    "Exportar (JPEG)",
                    data=base64.b64decode(jpg_url.split(",")[1]),
                    file_name="mapa.jpeg",
                    mime="image/jpeg",
                    use_container_width=True,
                )

    # -------------------- Aba SÉRIES TEMPORAIS --------------------
    elif aba == "Séries Temporais":
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is None or df.empty:
            st.warning("Não foi possível extrair a série temporal.")
            return
        charts_visualizer.display_time_series_chart(df, variavel, var_cfg["unit"])


# ---------------------- FUNÇÃO MAIN ----------------------
def main():
    # Inicializa GEE
    gee_handler.inicializar_gee()

    # Layout base
    ui.configurar_pagina()

    # Sidebar e seleção
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    # -------------------- SOBRE --------------------
    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    # -------------------- PRINCIPAL --------------------
    ui.renderizar_pagina_principal(opcao_menu)

    # Executa apenas quando clicar em "Gerar Análise"
    if st.session_state.get("analysis_triggered", False):
        st.session_state.analysis_triggered = False
        run_full_analysis()


# ---------------------- EXECUÇÃO DIRETA ----------------------
if __name__ == "__main__":
    main()
