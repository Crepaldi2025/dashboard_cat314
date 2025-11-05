# ==================================================================================
# main.py — Aplicativo principal Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import ee
import utils
import pandas as pd
import locale

# ==================================================================================
# Configuração de Locale (compatível com diferentes sistemas)
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Meses podem aparecer em inglês.")

# ==================================================================================
# Função principal: Análise de Mapas
# ==================================================================================
def run_map_analysis():
    """Executa a busca de dados e geração de mapas no GEE."""
    with st.spinner("🔄 Processando dados no Google Earth Engine..."):
        ee.Initialize()

        # ------------------------------------------------------------
        # 1. Coleta das seleções feitas pelo usuário
        # ------------------------------------------------------------
        tipo_area = st.session_state.get("tipo_area", "Município")
        tipo_variavel = st.session_state.get("tipo_variavel", "Precipitação")
        tipo_periodo = st.session_state.get("tipo_periodo", "Mensal")

        # ------------------------------------------------------------
        # 2. Datas de início e fim
        # ------------------------------------------------------------
        start_date, end_date = utils.get_date_range(tipo_periodo, st.session_state)

        # ------------------------------------------------------------
        # 3. Configuração da variável (dataset e visualização)
        # ------------------------------------------------------------
        variable_config = utils.get_variable_config(tipo_variavel)
        dataset_id = variable_config["dataset"]
        vis_params = variable_config["vis_params"]

        # ------------------------------------------------------------
        # 4. Busca de imagem agregada e área selecionada
        # ------------------------------------------------------------
        ee_image = gee_handler.get_aggregated_image(dataset_id, tipo_variavel, start_date, end_date)
        feature = gee_handler.get_selected_feature(tipo_area, st.session_state)

        # ------------------------------------------------------------
        # 5. Parâmetros visuais finais
        # ------------------------------------------------------------
        final_vis_params = {
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"],
        }

        # ------------------------------------------------------------
        # 6. Exibição dos Mapas
        # ------------------------------------------------------------
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
# Função principal do aplicativo
# ==================================================================================
def main():
    """Função principal do Clima-Cast-Crepaldi."""
    st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

    # Renderiza o menu lateral
    ui.render_sidebar()

    page = st.session_state.get("page", "Mapas")

    # ------------------------------------------------------------
    # Seção 1 — Mapas
    # ------------------------------------------------------------
    if page == "Mapas":
        run_map_analysis()

    # ------------------------------------------------------------
    # Seção 2 — Séries Temporais
    # ------------------------------------------------------------
    elif page == "Séries Temporais":
        charts_visualizer.display_time_series_page()

    # ------------------------------------------------------------
    # Seção 3 — Sobre o Aplicativo
    # ------------------------------------------------------------
    elif page == "Sobre":
        ui.render_about_page()

    # ------------------------------------------------------------
    # Página desconhecida (fallback)
    # ------------------------------------------------------------
    else:
        st.warning("Página não reconhecida. Verifique o menu lateral.")

# ==================================================================================
# Execução direta
# ==================================================================================
if __name__ == "__main__":
    main()
