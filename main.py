# ==================================================================================
# main.py — Clima-Cast-Crepaldi (versão estável - restaurada)
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
# Compatibilidade de versões do Streamlit
# --------------------------------------------------------------------------
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

# --------------------------------------------------------------------------
# Locale padrão (Português do Brasil)
# --------------------------------------------------------------------------
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except locale.Error:
        pass

# --------------------------------------------------------------------------
# Função principal de análise
# --------------------------------------------------------------------------
def run_full_analysis():
    """Executa toda a lógica de busca de dados e exibição de resultados."""

    from gee_handler import inicializar_gee
    status = inicializar_gee()

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
            st.info("⏳ Selecione um Estado ou Município antes de gerar a análise.")
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

            # ---------- mapa estático ----------
            if st.session_state.map_type == "Estático":
                png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                    ee_image, feature, final_vis_params, variable_config["unit"]
                )

                if png_url:
                    st.image(
                        png_url,
                        caption="Mapa Estático com Legenda",
                        width=700,
                        output_format="PNG",
                    )

                    with st.expander("💾 Opções de Exportação de Mapa"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="Exportar (PNG)",
                                data=png_url,
                                file_name="mapa_com_legenda.png",
                                mime="image/png",
                                use_container_width=True,
                            )
                        with col2:
                            st.download_button(
                                label="Exportar (JPEG)",
                                data=jpg_url,
                                file_name="mapa_com_legenda.jpeg",
                                mime="image/jpeg",
                                use_container_width=True,
                            )

                    with st.expander("📋 Tabela de Dados Amostrados"):
                        df_table = gee_handler.get_sampled_data_as_dataframe(
                            ee_image, geometry, st.session_state.variavel
                        )
                        if not df_table.empty:
                            st.dataframe(df_table)
                            c1, c2 = st.columns(2)
                            with c1:
                                st.download_button(
                                    "Exportar (CSV)",
                                    data=df_table.to_csv(index=False).encode("utf-8"),
                                    file_name="dados_mapa.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                )
                            with c2:
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                                    df_table.to_excel(
                                        writer, index=False, sheet_name="Dados"
                                    )
                                st.download_button(
                                    "Exportar (XLSX)",
                                    data=output.getvalue(),
                                    file_name="dados_mapa.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                )
                        else:
                            st.warning("Não foi possível amostrar dados para a tabela.")

            # ---------- mapa interativo ----------
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

            if not df_series.empty:
                with st.expander("💾 Exportar Dados da Série Temporal"):
                    st.dataframe(df_series)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button(
                            "Exportar (CSV)",
                            data=df_series.to_csv(index=False).encode("utf-8"),
                            file_name="dados_serie_temporal.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    with c2:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine="openpyxl") as writer:
                            df_series.to_excel(writer, index=False, sheet_name="Dados")
                        st.download_button(
                            "Exportar (XLSX)",
                            data=output.getvalue(),
                            file_name="dados_serie_temporal.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

# --------------------------------------------------------------------------
# Função principal da aplicação
# --------------------------------------------------------------------------
def main():
    """Organiza e executa a aplicação Streamlit."""

    from gee_handler import inicializar_gee
    inicializar_gee()  # Inicialização silenciosa e cacheada

    ui.configurar_pagina()
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
    else:
        if st.session_state.get("area_validada", False):
            ui.renderizar_pagina_principal(opcao_menu)
            ui.renderizar_resumo_selecao()
            run_full_analysis()

        elif st.session_state.get("show_confirmation_map", False):
            ui.renderizar_pagina_principal(opcao_menu)
            ui.renderizar_resumo_selecao()
            tipo_loc = st.session_state.get("tipo_localizacao")
            if tipo_loc == "Círculo (Lat/Lon/Raio)":
                map_visualizer.display_circle_map(
                    st.session_state.latitude,
                    st.session_state.longitude,
                    st.session_state.raio,
                )
                ui.renderizar_validacao_mapa()
            elif tipo_loc == "Polígono":
                map_visualizer.display_polygon_draw_map()
                ui.renderizar_validacao_mapa()

        elif st.session_state.get("analysis_triggered", False):
            st.session_state.analysis_triggered = False
            tipo_loc = st.session_state.get("tipo_localizacao")
            if tipo_loc in ["Estado", "Município"]:
                st.session_state.area_validada = True
            else:
                st.session_state.show_confirmation_map = True
            st.rerun()

        else:
            ui.renderizar_pagina_principal(opcao_menu)

# --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
