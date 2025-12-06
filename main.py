# ==================================================================================
# main.py 
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
import io
import pandas as pd
import time
import folium
from folium.plugins import Draw 
from streamlit_folium import st_folium
from datetime import timedelta 

# --- IMPORTAÇÕES DO SKEW-T ---
import skewt_handler 
import skewt_visualizer

def set_background():
    image_url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/terrab.jpg"
    opacity = 0.7
    page_bg_img = f"""<style>.stApp {{background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), url("{image_url}"); background-size: cover; background-position: center center; background-repeat: no-repeat; background-attachment: fixed;}}</style>"""
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_background()

def get_geo_caching_key(session_state):
    loc_type = session_state.get('tipo_localizacao')
    
    # Se for hidrografia, a chave é baseada no nome do arquivo enviado
    if session_state.get('nav_option') == 'Hidrografia':
        uploaded = session_state.get('hidro_upload')
        return f"hidro:{uploaded.name if uploaded else 'none'}"

    key = f"loc_type:{loc_type}"
    if loc_type == "Estado": key += f"|estado:{session_state.get('estado')}"
    elif loc_type == "Município": key += f"|estado:{session_state.get('estado')}|municipio:{session_state.get('municipio')}"
    elif loc_type == "Círculo (Lat/Lon/Raio)": key += f"|lat:{session_state.get('latitude')}|lon:{session_state.get('longitude')}|raio:{session_state.get('raio')}"
    elif loc_type == "Polígono": key += f"|geojson:{hash(str(session_state.get('drawn_geometry')))}"
    return key

def run_analysis_logic(variavel, start_date, end_date, geo_caching_key, aba):
    # O gee_handler já sabe lidar com o upload se a aba for Hidrografia
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    
    if not geometry: return None 
    
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    # Lógica compartilhada para Todos os Modos de Mapa (incluindo Hidrografia)
    if aba in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Hidrografia"]:
        target_hour = None
        if st.session_state.get('tipo_periodo') == "Horário Específico":
            target_hour = st.session_state.get('hora_especifica')
        
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry, target_hour)
        
        if ee_image:
            results["ee_image"] = ee_image
            # Gera tabela de dados se for mapa único ou hidro
            if aba in ["Mapas", "Hidrografia"]:
                df_map_samples = gee_handler.get_sampled_data_as_dataframe(ee_image, geometry, variavel)
                if df_map_samples is not None: results["map_dataframe"] = df_map_samples
            
    elif aba in ["Séries Temporais", "Múltiplas Séries"]:
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is not None: results["time_series_df"] = df

    return results

def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    
    # --- LÓGICA SKEW-T ---
    if aba == "Skew-T":
        lat = st.session_state.get("skew_lat")
        lon = st.session_state.get("skew_lon")
        date = st.session_state.get("skew_date")
        hour = st.session_state.get("skew_hour")
        
        with st.spinner("Gerando Skew-T (ERA5/GFS)..."):
            df = skewt_handler.get_vertical_profile_data(lat, lon, date, hour)
            st.session_state.skewt_results = {"df": df, "params": (lat, lon, date, hour)}
        return
    
    # --- LÓGICA SOBREPOSIÇÃO ---
    if aba == "Sobreposição (Camadas)":
        v1 = st.session_state.get("var_camada_1")
        v2 = st.session_state.get("var_camada_2")
        
        tipo_per = st.session_state.tipo_periodo
        if tipo_per == "Horário Específico":
            data_unica = st.session_state.get('data_horaria')
            start_date = data_unica
            end_date = data_unica + timedelta(days=1) if data_unica else None
        else:
            start_date, end_date = utils.get_date_range(tipo_per, st.session_state)
        
        if not (start_date and end_date): return
        geo_key = get_geo_caching_key(st.session_state)
        
        with st.spinner("Gerando camadas..."):
            res1 = run_analysis_logic(v1, start_date, end_date, geo_key, aba)
            res2 = run_analysis_logic(v2, start_date, end_date, geo_key, aba)
            
            if res1 and res2:
                st.session_state.analysis_results = {
                    "mode": "overlay",
                    "layer1": {"res": res1, "name": v1},
                    "layer2": {"res": res2, "name": v2}
                }
        return

    # --- LÓGICA MÚLTIPLOS ---
    if aba in ["Múltiplos Mapas", "Múltiplas Séries"]:
        variaveis = st.session_state.get("variaveis_multiplas", [])
        if not variaveis: return
        
        tipo_per = st.session_state.tipo_periodo
        if tipo_per == "Horário Específico":
            data_unica = st.session_state.get('data_horaria')
            start_date = data_unica
            end_date = data_unica + timedelta(days=1) if data_unica else None
        else:
            start_date, end_date = utils.get_date_range(tipo_per, st.session_state)
            
        if not (start_date and end_date): return
        geo_key = get_geo_caching_key(st.session_state)
        
        results_multi = {}
        msg_loading = f"Gerando {len(variaveis)} gráficos..." if aba == "Múltiplas Séries" else f"Gerando {len(variaveis)} mapas..."
        
        with st.spinner(f"{msg_loading} isso pode levar alguns segundos."):
            for var in variaveis:
                res = run_analysis_logic(var, start_date, end_date, geo_key, aba)
                if res: results_multi[var] = res
        
        mode_tag = "multi_series" if aba == "Múltiplas Séries" else "multi_map"
        st.session_state.analysis_results = {"mode": mode_tag, "data": results_multi}
        return

    # --- LÓGICA PADRÃO (ÚNICO / HIDROGRAFIA) ---
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")
    tipo_per = st.session_state.tipo_periodo
    
    if tipo_per == "Horário Específico":
        data_unica = st.session_state.get('data_horaria')
        start_date = data_unica
        end_date = data_unica + timedelta(days=1) if data_unica else None
    else:
        start_date, end_date = utils.get_date_range(tipo_per, st.session_state)

    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        with st.spinner("Processando dados no Google Earth Engine..."):
            # O parâmetro 'aba' aqui passa 'Hidrografia' ou 'Mapas' ou 'Séries'
            analysis_data = run_analysis_logic(variavel, start_date, end_date, geo_key, aba)
        
        if analysis_data is None:
            st.warning("Não foi possível obter dados. Verifique a área ou a data.")
            st.session_state.analysis_results = None
        else:
            st.session_state.analysis_results = analysis_data

    except Exception as e:
        st.error(f"Erro: {e}")
        st.session_state.analysis_results = None

def render_analysis_results():
    aba = st.session_state.get("nav_option", "Mapas")

    if aba == "Skew-T":
        if "skewt_results" in st.session_state:
            ui.renderizar_resumo_selecao()
            st.markdown("""<style>div[data-testid="stMetricValue"] {font-size: 1.1rem !important;}</style>""", unsafe_allow_html=True)
            res = st.session_state.skewt_results
            if res["df"] is not None:
                skewt_visualizer.render_skewt_plot(res["df"], *res["params"])
        return

    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        return

    results = st.session_state.analysis_results

    # Títulos e Strings
    tipo_periodo = st.session_state.get('tipo_periodo', '')
    periodo_str = ""
    if tipo_periodo == "Personalizado": periodo_str = f"de {st.session_state.get('data_inicio').strftime('%d/%m/%Y')} a {st.session_state.get('data_fim').strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mensal": periodo_str = f"mensal ({st.session_state.get('mes_mensal')}/{st.session_state.get('ano_mensal')})"
    elif tipo_periodo == "Anual": periodo_str = f"anual ({st.session_state.get('ano_anual')})"
    elif tipo_periodo == "Horário Específico": periodo_str = f"em {st.session_state.get('data_horaria').strftime('%d/%m/%Y')} às {st.session_state.get('hora_especifica')}:00"
    
    local_str = "Local Selecionado"
    if aba == "Hidrografia": local_str = "na Bacia Hidrográfica (Shapefile)"
    else:
        tipo_local = st.session_state.get('tipo_localizacao', '').lower()
        if tipo_local == "estado":
            val = st.session_state.get('estado', '').split(' - ')[0]
            local_str = f"no estado de {val}"
        elif tipo_local == "município":
            val = st.session_state.get('municipio', '')
            local_str = f"no município de {val}"
        elif tipo_local == "polígono": local_str = "para a área desenhada"
        elif "círculo" in tipo_local: local_str = "para o círculo definido"

    # --- RENDERIZAÇÃO ESPECIAL: SOBREPOSIÇÃO ---
    if aba == "Sobreposição (Camadas)" and results.get("mode") == "overlay":
        st.subheader("Mapa de Sobreposição (Overlay)")
        ui.renderizar_resumo_selecao()
        st.markdown("---")
        with st.popover("ℹ️ Como ver as camadas?"): st.markdown("**Use o ícone 🗂️ no canto do mapa.**")
        
        mode = st.session_state.get('overlay_mode', "Transparência")
        map_visualizer.create_overlay_map(
            results["layer1"]["res"]["ee_image"], results["layer1"]["name"], 
            results["layer2"]["res"]["ee_image"], results["layer2"]["name"], 
            results["layer1"]["res"]["feature"], 
            opacity1=st.session_state.get('opacity_1', 1.0), 
            opacity2=st.session_state.get('opacity_2', 0.6), 
            mode=mode
        )
        return

    # --- RENDERIZAÇÃO ESPECIAL: MÚLTIPLOS MAPAS ---
    if aba == "Múltiplos Mapas" and results.get("mode") == "multi_map":
        st.subheader("Comparação de Variáveis")
        ui.renderizar_resumo_selecao()
        st.markdown("---")
        cols = st.columns(2)
        for i, var_name in enumerate(results["data"]):
            res = results["data"][var_name]
            with cols[i % 2]:
                st.markdown(f"**{var_name}**")
                png, jpg, cbar = map_visualizer.create_static_map(res["ee_image"], res["feature"], gee_handler.obter_vis_params_interativo(var_name), res["var_cfg"]["unit"])
                if png:
                    st.image(png, use_container_width=True)
                    if cbar: st.image(cbar, use_container_width=True)
                    # Botão de exportação individual
                    try:
                        title = f"{var_name} {periodo_str} {local_str}"
                        tb = map_visualizer._make_title_image(title, 800)
                        mp = base64.b64decode(png.split(",")[1])
                        jp = base64.b64decode(jpg.split(",")[1])
                        cb = base64.b64decode(cbar.split(",")[1]) if cbar else None
                        fp = map_visualizer._stitch_images_to_bytes(tb, mp, cb, 'PNG')
                        fj = map_visualizer._stitch_images_to_bytes(tb, jp, cb, 'JPEG')
                        sub_c1, sub_c2 = st.columns(2)
                        var_slug = var_name.lower().replace(" ", "_")
                        # CORREÇÃO AQUI: sub_c1 e sub_c2
                        if fp: sub_c1.download_button("💾 PNG", fp, f"{var_slug}.png", "image/png", use_container_width=True)
                        if fj: sub_c2.download_button("💾 JPG", fj, f"{var_slug}.jpg", "image/jpeg", use_container_width=True)
                    except: pass
        return

    # --- RENDERIZAÇÃO ESPECIAL: MÚLTIPLAS SÉRIES ---
    if aba == "Múltiplas Séries" and results.get("mode") == "multi_series":
        st.subheader("Comparação de Séries")
        ui.renderizar_resumo_selecao()
        with st.expander("ℹ️ Ajuda dos Gráficos"): st.markdown("Use a barra no topo do gráfico para zoom e pan.")
        st.markdown("---")
        cols = st.columns(2)
        for i, var_name in enumerate(results["data"]):
            res = results["data"][var_name]
            with cols[i % 2]:
                st.markdown(f"##### {var_name}")
                charts_visualizer.display_time_series_chart(res["time_series_df"], var_name, res["var_cfg"]["unit"], show_help=False)
        return

    # --- RENDERIZAÇÃO PADRÃO (MAPA ÚNICO OU HIDROGRAFIA) ---
    var_cfg = results["var_cfg"]
    st.subheader(f"Análise: {st.session_state.get('variavel')} {local_str}")
    ui.renderizar_resumo_selecao() 

    if aba in ["Mapas", "Hidrografia"]:
        st.markdown("---") 
        if "ee_image" in results:
            vis_params = gee_handler.obter_vis_params_interativo(st.session_state.variavel)
            tipo_mapa = st.session_state.get("map_type", "Interativo")
            
            if tipo_mapa == "Interativo":
                # Ajuda e Mapa Interativo
                with st.popover("ℹ️ Ajuda do Mapa"): 
                    st.markdown("**Controles:** Zoom, Tela Cheia, Camadas.\n**Ferramentas:** Marcador, Linha, Polígono, Retângulo, Círculo, Editar, Lixeira.")
                map_visualizer.create_interactive_map(results["ee_image"], results["feature"], vis_params, var_cfg["unit"])
            else:
                # Mapa Estático
                with st.spinner("Gerando imagem..."):
                    png, jpg, cbar = map_visualizer.create_static_map(results["ee_image"], results["feature"], vis_params, var_cfg["unit"])
                if png:
                    st.image(png, width=500)
                    if cbar: st.image(cbar, width=500)
                    # Exportação Mapa Único
                    try:
                        title = f"{st.session_state.variavel} {periodo_str} {local_str}"
                        tb = map_visualizer._make_title_image(title, 800)
                        mp = base64.b64decode(png.split(",")[1])
                        jp = base64.b64decode(jpg.split(",")[1])
                        cb = base64.b64decode(cbar.split(",")[1]) if cbar else None
                        fp = map_visualizer._stitch_images_to_bytes(tb, mp, cb, 'PNG')
                        fj = map_visualizer._stitch_images_to_bytes(tb, jp, cb, 'JPEG')
                        c1, c2 = st.columns(2)
                        if fp: c1.download_button("💾 PNG", fp, "mapa.png", "image/png", use_container_width=True)
                        if fj: c2.download_button("💾 JPG", fj, "mapa.jpeg", "image/jpeg", use_container_width=True)
                    except: pass

        # Tabela de Dados
        st.markdown("---")
        st.subheader("Tabela de Dados")
        if "map_dataframe" in results and not results["map_dataframe"].empty:
            st.dataframe(results["map_dataframe"], use_container_width=True, hide_index=True)
            csv = results["map_dataframe"].to_csv(index=False).encode('utf-8')
            st.download_button("💾 Exportar CSV", csv, "dados_mapa.csv", "text/csv")

    elif aba == "Séries Temporais":
        if "time_series_df" in results:
            charts_visualizer.display_time_series_chart(results["time_series_df"], st.session_state.variavel, var_cfg["unit"], show_help=True)

def render_polygon_drawer():
    # ... (Mantido código original do polígono) ...
    st.subheader("Desenhe sua Área de Interesse")
    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google")
    Draw(export=False, draw_options={"polygon": {"allowIntersection": False, "showArea": True}, "rectangle": {"allowIntersection": False, "showArea": True}, "circle": False, "marker": False, "polyline": False}, edit_options={"edit": True, "remove": True}).add_to(m)
    map_data = st_folium(m, width=None, height=500, returned_objects=["all_drawings"])
    if map_data and map_data.get("all_drawings"):
        drawing = map_data["all_drawings"][-1]
        if drawing["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
            st.session_state.drawn_geometry = drawing["geometry"]
            st.success("✅ Polígono capturado!")
            st.rerun()
    elif 'drawn_geometry' in st.session_state and (not map_data or not map_data.get("all_drawings")):
        del st.session_state['drawn_geometry']
        st.rerun()

if __name__ == "__main__": main()
