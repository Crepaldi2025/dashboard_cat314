# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido v14)
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

# --- INÍCIO DA CORREÇÃO v14 (EXPORTAÇÃO DE MAPA) ---
import io
import pandas as pd # Necessário para a exportação do DataFrame
# --- FIM DA CORREÇÃO v14 ---

# Revertendo para a estratégia folium + streamlit-folium APENAS para o desenho
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium

# ==================================================================================
# FUNÇÕES DE CACHE (Modificada)
# ==================================================================================
def get_geo_caching_key(session_state):
    loc_type = session_state.get('tipo_localizacao')
    key = f"loc_type:{loc_type}"
    if loc_type == "Estado":
        key += f"|estado:{session_state.get('estado')}"
    elif loc_type == "Município":
        key += f"|estado:{session_state.get('estado')}|municipio:{session_state.get('municipio')}"
    elif loc_type == "Círculo (Lat/Lon/Raio)":
        key += f"|lat:{session_state.get('latitude')}|lon:{session_state.get('longitude')}|raio:{session_state.get('raio')}"
    elif loc_type == "Polígono":
        key += f"|geojson:{hash(str(session_state.get('drawn_geometry')))}"
    return key

@st.cache_data(ttl=3600)
def cached_run_analysis(variavel, start_date, end_date, geo_caching_key, aba):
    """
    Função cacheada que busca os dados do GEE.
    Executa a parte "lenta" da análise.
    """
    
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry: return None 
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    if aba == "Mapas":
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None: return None
        results["ee_image"] = ee_image
        
        # --- INÍCIO DA CORREÇÃO v14 (Coleta de dados da tabela) ---
        # Amostra a imagem para gerar a tabela
        df_map_samples = gee_handler.get_sampled_data_as_dataframe(
            ee_image, 
            geometry, # Geometria da área
            variavel    # Nome da variável
        )
        if df_map_samples is not None and not df_map_samples.empty:
            results["map_dataframe"] = df_map_samples
        # --- FIM DA CORREÇÃO v14 ---
            
        if st.session_state.get("map_type", "Interativo") == "Estático":
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, var_cfg["vis_params"], var_cfg["unit"]
            )
            results["static_maps"] = (png_url, jpg_url, colorbar_img)

    elif aba == "Séries Temporais":
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is None or df.empty: return None
        results["time_series_df"] = df

    return results

# ---------------------- FUNÇÃO PRINCIPAL DE ANÁLISE (Modificada) ----------------------
def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        # --- INÍCIO DA CORREÇÃO v14 ---
        # A amostragem de dados (get_sampled_data_as_dataframe) usa .getInfo()
        # e pode ser lenta, então o spinner deve englobar a chamada.
        spinner_message = "Processando dados no Google Earth Engine..."
        if aba == "Mapas":
            spinner_message = "Processando imagem e amostrando dados... Isso pode levar um momento."
        
        with st.spinner(spinner_message):
        # --- FIM DA CORREÇÃO v14 ---
            analysis_data = cached_run_analysis(
                variavel, start_date, end_date, geo_key, aba
            )
        
        if analysis_data is None:
            st.warning("Não foi possível obter dados para a seleção. Verifique os parâmetros.")
            st.session_state.analysis_results = None
        else:
            st.session_state.analysis_results = analysis_data

    except Exception as e:
        st.error(f"Ocorreu um erro durante a análise: {e}")
        st.session_state.analysis_results = None


def render_analysis_results():
    """
    Renderiza os resultados que estão salvos em st.session_state.analysis_results.
    """
    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        return

    results = st.session_state.analysis_results
    aba = st.session_state.get("nav_option", "Mapas")
    
    st.markdown("---")
    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao() 

    if aba == "Mapas":
        tipo_mapa = st.session_state.get("map_type", "Interativo")
        if "ee_image" not in results:
            st.warning("Não há dados de imagem para exibir.")
            return

        ee_image = results["ee_image"]
        feature = results["feature"]
        var_cfg = results["var_cfg"]
        vis_params = copy.deepcopy(var_cfg["vis_params"])

        if tipo_mapa == "Interativo":
            map_visualizer.create_interactive_map(ee_image, feature, vis_params, var_cfg["unit"]) 

        elif tipo_mapa == "Estático":
            if "static_maps" not in results:
                st.warning("Erro ao gerar mapas estáticos.")
                return
            png_url, jpg_url, colorbar_img = results["static_maps"]

            if png_url:
                st.image(png_url, caption="Mapa Estático", use_container_width=True)
            if colorbar_img:
                st.image(colorbar_img, caption="Legenda", use_container_width=True)

            st.markdown("### Exportar Mapas")
            if png_url:
                st.download_button("Exportar (PNG)", data=base64.b64decode(png_url.split(",")[1]), file_name="mapa.png", mime="image/png", use_container_width=True)
            if jpg_url:
                st.download_button("Exportar (JPEG)", data=base64.b64decode(jpg_url.split(",")[1]), file_name="mapa.jpeg", mime="image/jpeg", use_container_width=True)

        # --- INÍCIO DA CORREÇÃO v14 (Exibição e Exportação da Tabela) ---
        st.markdown("---")
        st.subheader("Dados Amostrais do Mapa")

        if "map_dataframe" not in results or results["map_dataframe"].empty:
            st.warning("Não foi possível extrair dados amostrais para a tabela.")
        else:
            df_map = results["map_dataframe"]
            st.dataframe(df_map, use_container_width=True)
            
            # Lógica de exportação (copiada de charts_visualizer)
            variavel = st.session_state.variavel
            variable_name = variavel.split(" (")[0]
            
            df_export = df_map
            file_name_safe = f"mapa_amostras_{variable_name.lower().replace(' ', '_')}"

            # 1. Preparar CSV
            csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
            
            # 2. Preparar Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Dados Amostrais')
            excel_data = excel_buffer.getvalue()

            # 3. Botões
            col_btn_1, col_btn_2 = st.columns(2)
            with col_btn_1:
                st.download_button(
                    label="Exportar Amostra (CSV)",
                    data=csv_data,
                    file_name=f"{file_name_safe}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_btn_2:
                st.download_button(
                    label="Exportar Amostra (XLSX)",
                    data=excel_data,
                    file_name=f"{file_name_safe}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        # --- FIM DA CORREÇÃO v14 ---

    elif aba == "Séries Temporais":
        if "time_series_df" not
