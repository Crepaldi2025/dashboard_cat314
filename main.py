# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido v6)
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
import geemap.foliumap as geemap

# ==================================================================================
# FUNÇÕES DE CACHE (Idênticas, sem alteração)
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
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry: return None 
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    if aba == "Mapas":
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None: return None
        results["ee_image"] = ee_image
        
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

# ---------------------- FUNÇÃO PRINCIPAL DE ANÁLISE (Idêntica) ----------------------
def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        with st.spinner("Processando dados no Google Earth Engine... Isso pode levar um momento."):
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
            # Esta função já está correta (v5)
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

    elif aba == "Séries Temporais":
        if "time_series_df" not in results:
            st.warning("Não foi possível extrair a série temporal.")
            return
        df = results["time_series_df"]
        var_cfg = results["var_cfg"]
        charts_visualizer.display_time_series_chart(df, st.session_state.variavel, var_cfg["unit"])


# ----------------------------------------------------------------------------------
# CORREÇÃO v6:
# Corrigindo os dois problemas da imagem:
# 1. Botões de Desenho: Adicionado `draw_control=True` ao construtor.
# 2. Mapa Satélite: Removido `basemap="SATELLITE"` e adicionado
#    `mapa_desenho.add_tile_layer(...)` manualmente.
# ----------------------------------------------------------------------------------
def render_polygon_drawer():
    """
    Renderiza um mapa para o usuário desenhar um polígono.
    Usa geemap.Map e seu drawing tools nativo.
    """
    st.subheader("Desenhe sua Área de Interesse")
    st.info("Use as ferramentas no canto esquerdo do mapa para desenhar um polígono. Clique em 'Gerar Análise' na barra lateral quando terminar.")

    # --- INÍCIO DA CORREÇÃO v6 ---
    mapa_desenho = geemap.Map(
        center=[-15.78, -47.93], 
        zoom=4,
        draw_control=True,      # <-- SOLUÇÃO 1: Adiciona os botões de desenho
        draw_export=False,      # (Opcional) Oculta o botão de exportar
        edit_control=True       # (Opcional) Permite editar/deletar o polígono
    )

    # SOLUÇÃO 2: Adiciona manualmente o basemap de satélite
    mapa_desenho.add_tile_layer(
        url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        name="Google Satellite",
        attribution="Google",
    )
    # --- FIM DA CORREÇÃO v6 ---
    
    map_data = mapa_desenho.to_streamlit(
        width=None, 
        height=500, 
        use_container_width=True,
        return_last_drawn=True 
    )

    # Lógica de captura (v5, que estava correta)
    if map_data and isinstance(map_data, list) and len(map_data) > 0:
        drawing = map_data[-1] 
        
        if drawing and drawing.get("geometry") and drawing["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
            st.session_state.drawn_geometry = drawing["geometry"]
            st.success("✅ Polígono capturado! Você já pode clicar em 'Gerar Análise'.")
        else:
            if 'drawn_geometry' in st.session_state:
                del st.session_state['drawn_geometry']
            st.warning("Por favor, desenhe um POLÍGONO para a análise.")


# ---------------------- FUNÇÃO MAIN (Idêntica) ----------------------
def main():
    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True

    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    ui.renderizar_pagina_principal(opcao_menu)
    
    if opcao_menu == "Mapas" and st.session_state.get('tipo_localizacao') == "Polígono":
        render_polygon_drawer()

    if st.session_state.get("analysis_triggered", False):
        st.session_state.analysis_triggered = False 
        run_full_analysis() 

    render_analysis_results()

if __name__ == "__main__":
    main()
