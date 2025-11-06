# ==================================================================================
# main.py — Script principal do sistema Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import utils
import ee
import pandas as pd
import locale
import traceback

# ==================================================================================
# CONFIGURAÇÃO INICIAL DO STREAMLIT
# ==================================================================================
# ⚠️ Deve ser o primeiro comando Streamlit do script
st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

st.markdown(
    "<h3 style='text-align:center;'>🌦️ Clima-Cast-Crepaldi — Sistema Integrado de Dados Meteorológicos</h3>",
    unsafe_allow_html=True
)

# ==================================================================================
# DEFINIÇÃO DE LOCALIZAÇÃO
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Os meses podem aparecer em inglês.")

# ==================================================================================
# INICIALIZAÇÃO DO GOOGLE EARTH ENGINE
# ==================================================================================
st.info("🔄 Inicializando conexão com o Google Earth Engine...")
try:
    gee_handler.initialize_gee()
    st.success("✅ Conexão com o Google Earth Engine estabelecida!")
except Exception as e:
    st.error("❌ Falha ao conectar com o Google Earth Engine.")
    st.code(traceback.format_exc())
    st.stop()

# ==================================================================================
# INTERFACE LATERAL (SIDEBAR)
# ==================================================================================
try:
    ui.render_sidebar()
except Exception as e:
    st.error("❌ Erro ao carregar a barra lateral.")
    st.code(traceback.format_exc())
    st.stop()

# ==================================================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE
# ==================================================================================
def run_full_analysis():
    """Executa a lógica completa de busca, processamento e exibição de resultados."""
    try:
        with st.spinner("🔍 Processando dados no Google Earth Engine..."):
            variavel, start_date, end_date = ui.obter_parametros_principais()
            geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
            if geometry is None:
                st.warning("Área de interesse inválida ou não definida.")
                return

            # Obtenção de imagem e série temporal
            ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
            df_timeseries = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)

            if ee_image is None:
                st.error("⚠️ Nenhuma imagem foi retornada do Google Earth Engine.")
                return

            # Mapa estático
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, utils.get_variable_config(variavel)["vis_params"],
                unit_label=utils.get_variable_config(variavel)["unit"]
            )

        # Armazena resultados no session_state
        st.session_state.ee_image_result = ee_image
        st.session_state.df_timeseries_result = df_timeseries
        st.session_state.static_map_urls = {"png": png_url, "jpg": jpg_url, "colorbar": colorbar_img}

        st.success("✅ Análise concluída com sucesso!")

    except Exception as e:
        st.error("❌ Erro durante a execução da análise.")
        st.code(traceback.format_exc())

# ==================================================================================
# EXIBIÇÃO DOS RESULTADOS
# ==================================================================================
def render_analysis_results_from_state():
    """Renderiza resultados armazenados no session_state."""
    try:
        urls = st.session_state.get("static_map_urls", {})
        df = st.session_state.get("df_timeseries_result", None)

        # --- Mapa estático ---
        if urls:
            st.subheader("🗺️ Mapa estático — ERA5-Land")
            if "png" in urls and urls["png"]:
                st.image(urls["png"], caption="Mapa estático gerado a partir do ERA5-Land", use_column_width=True)
            if "colorbar" in urls and urls["colorbar"]:
                st.markdown("### Barra de cores")
                st.markdown(f"![]({urls['colorbar']})")

        # --- Série temporal ---
        if df is not None and not df.empty:
            st.subheader("📈 Série temporal da variável selecionada")
            charts_visualizer.exibir_grafico_series_temporais(df)
        else:
            st.info("Nenhuma série temporal disponível para a área e período selecionados.")
    except Exception as e:
        st.error("❌ Erro ao renderizar resultados.")
        st.code(traceback.format_exc())

# ==================================================================================
# EXECUÇÃO PRINCIPAL
# ==================================================================================
def main():
    """Ponto de entrada do aplicativo."""
    try:
        if st.session_state.get("analysis_triggered", False):
            run_full_analysis()

        render_analysis_results_from_state()
    except Exception as e:
        st.error("❌ Erro inesperado na execução principal.")
        st.code(traceback.format_exc())

# ==================================================================================
# CHAMADA DO MAIN
# ==================================================================================
if __name__ == "__main__":
    main()
