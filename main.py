# ==================================================================================
# main.py — Script principal do sistema Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import locale
import traceback

# Módulos do app
import ui
import utils
import gee_handler
import map_visualizer
import charts_visualizer

# ==================================================================================
# CONFIGURAÇÃO INICIAL — DEVE SER O PRIMEIRO COMANDO STREAMLIT
# ==================================================================================
st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

st.markdown(
    "<h3 style='text-align:center;'>🌦️ Clima-Cast-Crepaldi — Sistema Integrado de Dados Meteorológicos</h3>",
    unsafe_allow_html=True
)

# ==================================================================================
# LOCALIZAÇÃO (pt_BR com fallback)
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Meses podem aparecer em inglês.")

# ==================================================================================
# INICIALIZAÇÃO DO GOOGLE EARTH ENGINE
# ==================================================================================
st.info("🔄 Inicializando conexão com o Google Earth Engine...")
try:
    gee_handler.initialize_gee()
    st.success("✅ Conexão com o Google Earth Engine estabelecida!")
except Exception:
    st.error("❌ Falha ao conectar com o Google Earth Engine.")
    st.code(traceback.format_exc())
    st.stop()

# ==================================================================================
# SIDEBAR
# ==================================================================================
try:
    ui.render_sidebar()
except Exception:
    st.error("❌ Erro ao carregar a barra lateral.")
    st.code(traceback.format_exc())
    st.stop()

# ==================================================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE
# ==================================================================================
def run_full_analysis():
    """Executa a análise: obtém geometria, imagem ERA5, série temporal e mapas."""
    try:
        with st.spinner("🔍 Processando dados no Google Earth Engine..."):
            # Parâmetros
            variavel, start_date, end_date = ui.obter_parametros_principais()
            if not utils.validar_datas(start_date, end_date):
                return

            geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
            if geometry is None or feature is None:
                st.warning("⚠️ Área de interesse inválida ou não definida.")
                return

            # Config da variável (vis_params + unit)
            var_cfg = utils.get_variable_config(variavel)
            if not var_cfg:
                st.error("⚠️ Configuração da variável não encontrada.")
                return
            vis_params = var_cfg["vis_params"]
            unit_label = var_cfg["unit"]

            # Dados ERA5-Land
            ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
            if ee_image is None:
                st.error("⚠️ Nenhuma imagem foi retornada do ERA5-Land.")
                return

            df_timeseries = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)

            # Mapa estático (PNG/JPG + colorbar)
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, vis_params, unit_label=unit_label
            )

        # Armazena resultados para persistência
        st.session_state.ee_image_result = ee_image
        st.session_state.feature_result = feature
        st.session_state.df_timeseries_result = df_timeseries
        st.session_state.static_map_urls = {"png": png_url, "jpg": jpg_url, "colorbar": colorbar_img}
        st.session_state.vis_params = vis_params
        st.session_state.unit_label = unit_label

        st.success("✅ Análise concluída com sucesso!")

    except Exception:
        st.error("❌ Erro durante a execução da análise.")
        st.code(traceback.format_exc())

# ==================================================================================
# EXIBIÇÃO DOS RESULTADOS
# ==================================================================================
def render_analysis_results_from_state():
    """Renderiza mapas (interativo + estático) e série temporal, se disponíveis."""
    try:
        ee_image = st.session_state.get("ee_image_result")
        feature = st.session_state.get("feature_result")
        urls = st.session_state.get("static_map_urls", {})
        df = st.session_state.get("df_timeseries_result")
        vis_params = st.session_state.get("vis_params")
        unit_label = st.session_state.get("unit_label", "")

        # --- Mapa interativo (com fundo de satélite) ---
        if ee_image is not None and feature is not None and vis_params:
            st.subheader("🗺️ Mapa interativo — ERA5-Land")
            map_visualizer.create_interactive_map(ee_image, feature, vis_params, unit_label=unit_label)

        # --- Mapa estático ---
        if urls and urls.get("png"):
            st.subheader("🗺️ Mapa estático — ERA5-Land")
            st.image(urls["png"], caption="Mapa estático (ERA5-Land)", use_column_width=True)
            if urls.get("colorbar"):
                st.markdown("### Barra de cores")
                st.markdown(f"![]({urls['colorbar']})")

        # --- Série temporal ---
        if df is not None and not df.empty:
            st.subheader("📈 Série temporal")
            charts_visualizer.exibir_grafico_series_temporais(df)
        else:
            st.info("Nenhuma série temporal disponível para a área e o período selecionados.")
    except Exception:
        st.error("❌ Erro ao renderizar os resultados.")
        st.code(traceback.format_exc())

# ==================================================================================
# EXECUÇÃO
# ==================================================================================
def main():
    try:
        if st.session_state.get("analysis_triggered", False):
            run_full_analysis()
        render_analysis_results_from_state()
    except Exception:
        st.error("❌ Erro inesperado na execução principal.")
        st.code(traceback.format_exc())

# ==================================================================================
# ENTRADA
# ==================================================================================
if __name__ == "__main__":
    main()
