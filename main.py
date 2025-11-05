# ==================================================================================
# main.py — Aplicativo principal Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st

# ✅ ESTE É O PRIMEIRO COMANDO STREAMLIT DO APP
st.set_page_config(page_title="Clima-Cast-Crepaldi", page_icon="🌤️", layout="wide")

import ui
import gee_handler
import map_visualizer
import charts_visualizer
import ee
import utils
import pandas as pd
import locale

# ==================================================================================
# Configuração de Locale (português com fallback)
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        # usamos print() para não acionar o Streamlit antes da hora
        print("Aviso: Locale 'pt_BR.UTF-8' não encontrado. Meses podem aparecer em inglês.")

# ==================================================================================
# Função: Análise de Mapas
# ==================================================================================
def run_map_analysis():
    """Executa a busca de dados e geração dos mapas no Google Earth Engine."""
    with st.spinner("🔄 Processando dados no Google Earth Engine..."):
        ee.Initialize()

        tipo_area = st.session_state.get("tipo_area", "Município")
        tipo_variavel = st.session_state.get("tipo_variavel", "Precipitação")
        tipo_periodo = st.session_state.get("tipo_periodo", "Mensal")

        start_date, end_date = utils.get_date_range(tipo_periodo, st.session_state)
        variable_config = utils.get_variable_config(tipo_variavel)

        dataset_id = variable_config["dataset"]
        vis_params = variable_config["vis_params"]

        ee_image = gee_handler.get_aggregated_image(dataset_id, tipo_variavel, start_date, end_date)
        feature = gee_handler.get_selected_feature(tipo_area, st.session_state)

        final_vis_params = {
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"],
        }

        st.markdown("### 🗺️ Mapas de Visualização")

        # Mapa interativo
        map_visualizer.display_interactive_map(
            dataset=ee_image,
            vis_params=final_vis_params,
            latitude=feature.geometry().centroid().coordinates().get(1).getInfo(),
            longitude=feature.geometry().centroid().coordinates().get(0).getInfo(),
            title=f"{tipo_variavel} — {tipo_area}"
        )

        # Mapa estático
        map_visualizer.display_static_map(
            image=ee_image,
            vis_params=final_vis_params,
            region=feature.geometry(),
            title=f"Mapa Estático — {tipo_variavel}"
        )

        st.success("✅ Mapas gerados com sucesso!")

# ==================================================================================
# Função: Séries Temporais
# ==================================================================================
def run_time_series_analysis():
    """Executa a análise de séries temporais e exibe gráficos e tabelas."""
    with st.spinner("📈 Gerando séries temporais..."):
        ee.Initialize()

        tipo_area = st.session_state.get("tipo_area", "Município")
        tipo_variavel = st.session_state.get("tipo_variavel", "Precipitação")
        periodo_series = st.session_state.get("periodo_series", "Mensal")

        start_date, end_date = utils.get_date_range(periodo_series, st.session_state)
        variable_config = utils.get_variable_config(tipo_variavel)
        dataset_id = variable_config["dataset"]
        unit = variable_config["unit"]

        ee_image = gee_handler.get_aggregated_image(dataset_id, tipo_variavel, start_date, end_date)
        feature = gee_handler.get_selected_feature(tipo_area, st.session_state)

        df_stats = gee_handler.extract_statistics(
            ee_image, feature, tipo_variavel, start_date, end_date
        )

        charts_visualizer.display_charts(df_stats, tipo_variavel, unit)

        st.markdown("---")
        st.download_button(
            label="📥 Baixar dados em CSV",
            data=df_stats.to_csv(index=False).encode("utf-8"),
            file_name=f"serie_{tipo_variavel}.csv",
            mime="text/csv"
        )

        st.success("✅ Séries temporais geradas com sucesso!")

# ==================================================================================
# Função principal
# ==================================================================================
def main():
    """Função principal do Clima-Cast-Crepaldi."""
    ui.render_sidebar()

    page = st.session_state.get("page", "Mapas")

    if page == "Mapas":
        run_map_analysis()

    elif page == "Séries Temporais":
        run_time_series_analysis()

    elif page == "Sobre":
        ui.render_about_page()

    else:
        st.warning("Página não reconhecida. Verifique o menu lateral.")

# ==================================================================================
# Execução direta
# ==================================================================================
if __name__ == "__main__":
    main()
