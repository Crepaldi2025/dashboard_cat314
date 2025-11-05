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
# Configuração de Locale (compatível com ambientes diferentes)
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        st.warning("Locale 'pt_BR.UTF-8' não encontrado. Nomes de meses podem aparecer em inglês.")

# ==================================================================================
# Função principal de execução completa
# ==================================================================================
def run_full_analysis():
    """Executa a busca de dados no GEE e exibe os resultados no Streamlit."""

    with st.spinner("🔄 Processando dados no Google Earth Engine..."):
        # ------------------------------------------------------------
        # 1. Inicialização do GEE e variáveis
        # ------------------------------------------------------------
        ee.Initialize()

        tipo_area = st.session_state.get("tipo_area", "Município")
        tipo_variavel = st.session_state.get("tipo_variavel", "Precipitação")
        tipo_periodo = st.session_state.get("tipo_periodo", "Mensal")

        # ------------------------------------------------------------
        # 2. Obtenção das datas conforme período
        # ------------------------------------------------------------
        start_date, end_date = utils.get_date_range(tipo_periodo, st.session_state)

        # ------------------------------------------------------------
        # 3. Seleção da variável e parâmetros visuais
        # ------------------------------------------------------------
        variable_config = utils.get_variable_config(tipo_variavel)
        dataset_id = variable_config["dataset"]
        vis_params = variable_config["vis_params"]

        # ------------------------------------------------------------
        # 4. Busca da imagem agregada no GEE
        # ------------------------------------------------------------
        ee_image = gee_handler.get_aggregated_image(dataset_id, tipo_variavel, start_date, end_date)
        feature = gee_handler.get_selected_feature(tipo_area, st.session_state)

        # ------------------------------------------------------------
        # 5. Aplicação dos parâmetros visuais finais
        # ------------------------------------------------------------
        final_vis_params = {
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"]
        }

        # ------------------------------------------------------------
        # 6. Geração dos mapas
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

        # ------------------------------------------------------------
        # 7. Extração de estatísticas e gráficos
        # ------------------------------------------------------------
        st.markdown("### 📈 Estatísticas e Gráficos")

        stats_df = gee_handler.extract_statistics(ee_image, feature, tipo_variavel, start_date, end_date)
        charts_visualizer.display_charts(stats_df, tipo_variavel, variable_config["unit"])

        # ------------------------------------------------------------
        # 8. Exibição dos dados em tabela
        # ------------------------------------------------------------
        st.markdown("### 📊 Dados Tabulares")
        st.dataframe(stats_df)

        st.success("✅ Processamento concluído com sucesso!")

# ==================================================================================
# Função principal do app (interface)
# ==================================================================================
def main():
    """Função principal do aplicativo Streamlit."""
    ui.render_sidebar()

    page = st.session_state.get("page", "Análise Completa")

    if page == "Análise Completa":
        run_full_analysis()
    elif page == "Sobre":
        ui.render_about_page()
    else:
        st.warning("Página não reconhecida. Verifique a navegação lateral.")

# ==================================================================================
# Execução direta
# ==================================================================================
if __name__ == "__main__":
    main()
