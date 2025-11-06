# ==================================================================================
# main.py — Aplicativo principal do Clima-Cast-Crepaldi
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
import base64

# Define o locale para Português do Brasil para todo o script.
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        # Fallback para sistemas Windows
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass


# ==================================================================================
# EXECUÇÃO COMPLETA
# ==================================================================================
def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""
    with st.spinner("Processando dados no Google Earth Engine..."):
        tipo_localizacao = st.session_state.tipo_localizacao
        tipo_periodo = st.session_state.tipo_periodo
        variavel = st.session_state.variavel

        # Garante que o GEE está inicializado
        gee_handler.initialize_gee()

        # Obtém os parâmetros da variável
        variable_config = utils.get_variable_config(variavel)
        dataset = variable_config["dataset"]
        band = variable_config["band"]
        palette = variable_config["palette"]
        variable_name = variable_config["label"]
        unit = variable_config["unit"]

        # Obtém geometria conforme seleção
        feature = ui.get_selected_feature(tipo_localizacao)
        if feature is None:
            st.error("❌ Nenhuma área de interesse válida foi selecionada. Volte ao painel lateral e escolha um Estado, Município ou Círculo válido.")
            st.stop()


        # Determina o período
        start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)

        # Obtém imagem processada
        ee_image = gee_handler.get_gee_data(dataset, band, start_date, end_date, feature)

        # Define parâmetros de visualização
        final_vis_params = {
            "min": variable_config["min"],
            "max": variable_config["max"],
            "palette": palette
        }

        st.markdown("---")
        st.subheader("Resultado da Análise")

        # Cria mapa interativo
        map_visualizer.create_interactive_map(ee_image, feature, final_vis_params, variable_config["unit"])

        # Cria mapa estático
        png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
        ee_image, feature, final_vis_params, variable_config["unit"]
        )


        st.markdown("### Exportar Mapas")

        # ============================
        # BOTÃO EXPORTAR PNG
        # ============================
        if png_url:
            png_bytes = base64.b64decode(png_url.split(",")[1])
            st.download_button(
                label="Exportar (PNG)",
                data=png_bytes,
                file_name="mapa.png",
                mime="image/png",
                use_container_width=True
            )

        # ============================
        # BOTÃO EXPORTAR JPEG
        # ============================
        if jpg_url:
            jpg_bytes = base64.b64decode(jpg_url.split(",")[1])
            st.download_button(
                label="Exportar (JPEG)",
                data=jpg_bytes,
                file_name="mapa.jpeg",
                mime="image/jpeg",
                use_container_width=True
            )

        st.success("✅ Análise concluída com sucesso!")


# ==================================================================================
# FUNÇÃO PRINCIPAL
# ==================================================================================
def main():
    st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide")

    # Interface
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)


    # Execução principal
    if st.session_state.get("analisar", False):
        run_full_analysis()


# ==================================================================================
# EXECUÇÃO DIRETA
# ==================================================================================
if __name__ == "__main__":
    main()


