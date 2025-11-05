# ==================================================================================
# main.py — Clima-Cast-Crepaldi (versão leve, estável e compatível)
# ==================================================================================
import streamlit as st
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import utils
import ee
import io
import pandas as pd
import copy
import locale

# --------------------------------------------------------------------------
# Locale padrão (Português do Brasil)
# --------------------------------------------------------------------------
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass

# --------------------------------------------------------------------------
# Compatibilidade entre versões do Streamlit
# --------------------------------------------------------------------------
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

# --------------------------------------------------------------------------
# Botão de limpeza de cache e estado
# --------------------------------------------------------------------------
st.sidebar.markdown("### ⚙️ Diagnóstico rápido")
if st.sidebar.button("🧹 Limpar cache e estado"):
    st.cache_data.clear()
    st.cache_resource.clear()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("Cache e estado limpos. Recarregue o app.")
    st.stop()

# --------------------------------------------------------------------------
# Função principal de análise
# --------------------------------------------------------------------------
def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""
    status = gee_handler.inicializar_gee()

    if status == "local":
        st.toast("✅ Conectado ao Earth Engine (modo local).")
    elif status == "service_account":
        st.toast("✅ Conectado ao Earth Engine via Service Account.")
    elif status is None:
        st.error("⚠️ Falha ao conectar ao Google Earth Engine.")
        return

    with st.spinner("🔄 Processando dados no Google Earth Engine..."):
        geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
        if not geometry:
            st.error("Não foi possível definir a geometria da área de interesse.")
            return

        start_date, end_date = utils.get_date_range(
            st.session_state.tipo_periodo, st.session_state
        )
        if not (start_date and end_date):
            st.error("Período de análise inválido.")
            return

        variable_config = gee_handler.ERA5_VARS[st.session_state.variavel]
        nav_option = st.session_state.nav_option

        # ------------------------------------------------------------------
        # MODO MAPAS
        # ------------------------------------------------------------------
        if nav_option == "Mapas":
            ee_image = gee_handler.get_era5_image(
                st.session_state.variavel, start_date, end_date, geometry
            )
            if not ee_image:
                return

            final_vis_params = copy.deepcopy(variable_config["vis_params"])
            if (
                st.session_state.variavel == "Precipitação Total"
                and st.session_state.tipo_periodo == "Anual"
            ):
                final_vis_params["max"] = 3000

            st.subheader("🗺️ Resultado da Análise")

            if st.session_state.map_type == "Estático":
                mapa_final = map_visualizer.create_static_map(
                    ee_image, feature, final_vis_params, variable_config["unit"]
                )
                if mapa_final:
                    st.image(
                        mapa_final,
                        caption="Mapa Estático",
                        width=700,
                        output_format="PNG",
                    )

            elif st.session_state.map_type == "Interativo":
                map_visualizer.create_interactive_map(
                    ee_image, feature, final_vis_params, variable_config["unit"]
                )

        # ------------------------------------------------------------------
        # MODO SÉRIES TEMPORAIS
        # ------------------------------------------------------------------
        elif nav_option == "Séries Temporais":
            df_series = gee_handler.get_time_series_data(
                st.session_state.variavel, start_date, end_date, geometry
            )

            st.subheader("📈 Resultado da Análise")

            charts_visualizer.display_time_series_chart(
                df_series, st.session_state.variavel, variable_config["unit"]
            )

# --------------------------------------------------------------------------
# Função principal da aplicação
# --------------------------------------------------------------------------
def main():
    """Organiza e executa o fluxo principal do app."""
    ui.configurar_pagina()
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
    else:
        if st.session_state.get("analysis_triggered", False):
            st.session_state.analysis_triggered = False
            st.session_state.area_validada = True
            st.rerun()  # ✅ versão compatível e estável

        if st.session_state.get("area_validada", False):
            ui.renderizar_pagina_principal(opcao_menu)
            ui.renderizar_resumo_selecao()
            run_full_analysis()
        else:
            ui.renderizar_pagina_principal(opcao_menu)

# --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
