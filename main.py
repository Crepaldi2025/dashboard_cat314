# ==================================================================================
# main.py — Aplicativo principal do Clima-Cast-Crepaldi (fluxo simples e estável)
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

# Locale (silencioso)
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        pass


# ---------------------------------------------
# Núcleo da análise (Mapas / Séries)
# ---------------------------------------------
def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    # Geometria da AOI (Estado/Município/Círculo/Polígono)
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry:
        st.error("❌ Não foi possível definir a área de interesse. Confira o painel à esquerda.")
        return

    # Período
    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.error("⚠️ Período inválido.")
        return

    # Config da variável
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg:
        st.error("⚠️ Variável não reconhecida.")
        return

    # MAPAS
    if aba == "Mapas":
        # Busca imagem do ERA5-Land já processada/recortada
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None:
            st.warning("Não há dados para o período selecionado.")
            return

        st.markdown("---")
        st.subheader("Resultado da Análise")
        ui.renderizar_resumo_selecao()

        vis_params = copy.deepcopy(var_cfg["vis_params"])
        tipo_mapa = st.session_state.get("map_type", "Interativo")

        if tipo_mapa == "Interativo":
            # Apenas o mapa interativo. Sem exportação aqui.
            map_visualizer.create_interactive_map(
                ee_image, feature, vis_params, var_cfg["unit"]
            )

        else:  # Estático
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, vis_params, var_cfg["unit"]
            )

            if png_url:
                st.image(png_url, caption="Mapa Estático (PNG)", use_container_width=True)
            if colorbar_img:
                st.image(colorbar_img, caption="Legenda", use_container_width=True)

            st.markdown("### Exportar Mapas")
            col1, col2 = st.columns(2)
            with col1:
                if png_url:
                    try:
                        st.download_button(
                            label="Exportar (PNG)",
                            data=requests.get(png_url).content,
                            file_name="mapa.png",
                            mime="image/png",
                            use_container_width=True,
                        )
                    except Exception:
                        # fallback base64 (quando create_static_map retorna data URL)
                        if png_url.startswith("data:image"):
                            png_bytes = base64.b64decode(png_url.split(",")[1])
                            st.download_button(
                                label="Exportar (PNG)",
                                data=png_bytes,
                                file_name="mapa.png",
                                mime="image/png",
                                use_container_width=True,
                            )
            with col2:
                if jpg_url:
                    try:
                        st.download_button(
                            label="Exportar (JPEG)",
                            data=requests.get(jpg_url).content,
                            file_name="mapa.jpeg",
                            mime="image/jpeg",
                            use_container_width=True,
                        )
                    except Exception:
                        if jpg_url.startswith("data:image"):
                            jpg_bytes = base64.b64decode(jpg_url.split(",")[1])
                            st.download_button(
                                label="Exportar (JPEG)",
                                data=jpg_bytes,
                                file_name="mapa.jpeg",
                                mime="image/jpeg",
                                use_container_width=True,
                            )

    # SÉRIES TEMPORAIS
    elif aba == "Séries Temporais":
        st.markdown("---")
        st.subheader("Resultado da Análise")
        ui.renderizar_resumo_selecao()

        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is None or df.empty:
            st.warning("Não foi possível extrair a série temporal.")
            return
        charts_visualizer.display_time_series_chart(df, variavel, var_cfg["unit"])


# ---------------------------------------------
# Função principal
# ---------------------------------------------
def main():
    # Inicializa GEE (mantendo seu nome de função)
    gee_handler.inicializar_gee()

    # Cabeçalho/estrutura
    ui.configurar_pagina()

    # Sidebar e opção de navegação
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    # Página SOBRE: sempre mostra e encerra
    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    # Página principal (título/data)
    ui.renderizar_pagina_principal(opcao_menu)

    # Quando o usuário clicar em "Gerar Análise"
    if st.session_state.get("analysis_triggered", False):
        # zera o gatilho para evitar loop
        st.session_state.analysis_triggered = False
        run_full_analysis()
    else:
        # Mensagem discreta enquanto nada foi rodado
        st.info("Configure os filtros no painel à esquerda e clique em **Gerar Análise**.")


# Execução direta
if __name__ == "__main__":
    main()
