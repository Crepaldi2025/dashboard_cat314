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
# Funções principais de execução e renderização
# ==================================================================================

def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""
    with st.spinner("Processando dados no Google Earth Engine..."):
        variavel, start_date, end_date = ui.obter_parametros_principais()
        geometry, nome_local = gee_handler.get_area_of_interest_geometry(st.session_state)
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        df_timeseries = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        url_mapa_estatico = map_visualizer.create_static_map(ee_image, variavel, geometry, nome_local)

    # === Atualização: persistência dos resultados no session_state ===
    st.session_state.ee_image_result = ee_image
    st.session_state.df_timeseries_result = df_timeseries
    st.session_state.static_map_urls = {"principal": url_mapa_estatico}

    st.success("✅ Análise concluída com sucesso!")


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
# Função principal da aplicação
# ==================================================================================
def main():
    # === Correção: set_page_config é o primeiro comando Streamlit da função ===
    st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

    # --- Configuração de idioma e locale ---
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except locale.Error:
            st.warning("Locale 'pt_BR.UTF-8' não encontrado. Nomes de meses podem aparecer em inglês.")

    # --- Inicializa variáveis de estado ---
    if "analysis_triggered" not in st.session_state:
        st.session_state.analysis_triggered = False

    # --- Interface lateral ---
    ui.render_sidebar()

    # --- Execução principal da análise ---
    if st.session_state.get("analysis_triggered", False):
        run_full_analysis()

    # --- Renderização dos resultados armazenados ---
    render_analysis_results_from_state()


# ==================================================================================
# Execução
# ==================================================================================
if __name__ == "__main__":
    main()
