# ==================================================================================
# main.py 
# ==================================================================================
import streamlit as st
import time
import folium
from folium.plugins import Draw 
from streamlit_folium import st_folium
from datetime import timedelta 

# Módulos do Projeto
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import utils

# Módulos Novos (Skew-T)
import skewt_handler 
import skewt_visualizer

def set_background():
    # Define o fundo apenas uma vez
    if 'bg_set' not in st.session_state:
        image_url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/terrab.jpg"
        opacity = 0.7
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), url("{image_url}");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)
        st.session_state.bg_set = True

def main():
    set_background()

    # Inicialização do GEE
    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True
        
    # Carrega dados geopolíticos
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    
    # Renderiza Sidebar e obtém opção
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)
    
    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return
    
    # Renderiza Cabeçalho
    ui.renderizar_pagina_principal(opcao_menu)
    
    # --- Lógica de Polígono (Mapas/Séries) ---
    if opcao_menu in ["Mapas", "Séries Temporais"] and st.session_state.get('tipo_localizacao') == "Polígono":
        if not st.session_state.get("analysis_triggered"):
            st.subheader("Desenhe sua Área")
            m = folium.Map(location=[-15.78, -47.93], zoom_start=4)
            Draw(export=False, draw_options={'polyline':False,'circle':False,'marker':False}).add_to(m)
            out = st_folium(m, height=400)
            if out and out['all_drawings']:
                st.session_state.drawn_geometry = out['all_drawings'][-1]['geometry']

    # --- Processamento (Quando clica em "Gerar") ---
    if st.session_state.get("analysis_triggered"):
        st.session_state.analysis_triggered = False 
        
        # CASO 1: Skew-T
        if opcao_menu == "Skew-T":
            lat = st.session_state.get("skew_lat")
            lon = st.session_state.get("skew_lon")
            date = st.session_state.get("skew_date")
            hour = st.session_state.get("skew_hour")
            
            with st.spinner("Obtendo dados atmosféricos (Open-Meteo)..."):
                # Chama o handler blindado
                df = skewt_handler.get_vertical_profile_data(lat, lon, date, hour)
                st.session_state.skewt_results = {"df": df, "params": (lat, lon, date, hour)}

        # CASO 2: Mapas/Séries (GEE)
        else:
            run_gee_analysis(opcao_menu)

    # --- Exibição de Resultados ---
    
    # Resultados Skew-T
    if opcao_menu == "Skew-T" and "skewt_results" in st.session_state:
        ui.renderizar_resumo_selecao()
        res = st.session_state.skewt_results
        if res["df"] is not None:
            skewt_visualizer.render_skewt_plot(res["df"], *res["params"])
    
    # Resultados Mapas/Séries
    elif "analysis_results" in st.session_state and st.session_state.analysis_results:
        # Recupera resultados
        results = st.session_state.analysis_results
        
        # Renderiza Resumo
        ui.renderizar_resumo_selecao()
        
        # Renderiza Mapa ou Gráfico
        if opcao_menu == "Mapas" and "ee_image" in results:
             vis = gee_handler.obter_vis_params_interativo(st.session_state.variavel)
             st.subheader(f"Mapa: {st.session_state.variavel}")
             
             if st.session_state.get("map_type") == "Interativo":
                 map_visualizer.create_interactive_map(results["ee_image"], results["feature"], vis, "")
             else:
                 png, jpg, cbar = map_visualizer.create_static_map(results["ee_image"], results["feature"], vis, "")
                 if png: 
                     st.image(png)
                     if cbar: st.image(cbar)

        elif opcao_menu == "Séries Temporais" and "time_series_df" in results:
            st.subheader(f"Série: {st.session_state.variavel}")
            charts_visualizer.display_time_series_chart(results["time_series_df"], st.session_state.variavel, "")

def run_gee_analysis(aba):
    """Lógica auxiliar para rodar o GEE."""
    try:
        variavel = st.session_state.variavel
        start, end = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
        geom, feat = gee_handler.get_area_of_interest_geometry(st.session_state)
        
        if not geom: 
            st.error("Localização não definida.")
            return

        with st.spinner("Processando no Google Earth Engine..."):
            if aba == "Mapas":
                img = gee_handler.get_era5_image(variavel, start, end, geom)
                if img:
                    st.session_state.analysis_results = {"ee_image": img, "feature": feat, "var_cfg": {}}
            else:
                df = gee_handler.get_time_series_data(variavel, start, end, geom)
                if df is not None:
                    st.session_state.analysis_results = {"time_series_df": df, "var_cfg": {}}
                    
    except Exception as e:
        st.error(f"Erro na análise: {e}")

if __name__ == "__main__": main()
