# ==================================================================================
# main.py — Script principal do sistema Clima-Cast-Crepaldi
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
# Função principal
# ==================================================================================
def main():
    # Deve ser o primeiro comando Streamlit
    st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

    # Configura idioma
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except locale.Error:
            st.warning("Locale 'pt_BR.UTF-8' não encontrado. Nomes de meses podem aparecer em inglês.")

    # Renderiza barra lateral
    ui.render_sidebar()

    # Executa análise se solicitada
    if st.session_state.get("analysis_triggered", False):
        run_full_analysis()

    # Renderiza resultados armazenados
    render_analysis_results_from_state()


# ==================================================================================
# Execução da análise principal
# ==================================================================================
def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""
    with st.spinner("Processando dados no Google Earth Engine..."):
        variavel, start_date, end_date = ui.obter_parametros_principais()
        geometry, nome_local = gee_handler.get_area_of_interest_geometry(st.session_state)
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        df_timeseries = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(ee_image, geometry, variavel)

    # Armazena no session_state
    st.session_state.ee_image_result = ee_image
    st.session_state.df_timeseries_result = df_timeseries
    st.session_state.static_map_urls = {"principal": png_url}

    st.success("✅ Análise concluída com sucesso!")


# ==================================================================================
# Exibição dos resultados
# ==================================================================================
def render_analysis_results_from_state():
    """Renderiza na tela os resultados armazenados no session_state."""
    urls = st.session_state.get("static_map_urls", {})
    df = st.session_state.get("df_timeseries_result", None)

    if urls:
        st.subheader("🗺️ Mapa estático")
        if "principal" in urls:
            st.image(urls["principal"], caption="Mapa estático (principal)", use_column_width=True)

    if df is not None and not df.empty:
        st.subheader("📈 Série temporal")
        charts_visualizer.exibir_grafico_series_temporais(df)


# ==================================================================================
# Execução principal
# ==================================================================================
if __name__ == "__main__":
    main()
