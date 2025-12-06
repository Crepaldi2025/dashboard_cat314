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
    key = f"loc_type:{loc_type}"
    if loc_type == "Estado": key += f"|estado:{session_state.get('estado')}"
    elif loc_type == "Município": key += f"|estado:{session_state.get('estado')}|municipio:{session_state.get('municipio')}"
    elif loc_type == "Círculo (Lat/Lon/Raio)": key += f"|lat:{session_state.get('latitude')}|lon:{session_state.get('longitude')}|raio:{session_state.get('raio')}"
    elif loc_type == "Polígono": key += f"|geojson:{hash(str(session_state.get('drawn_geometry')))}"
    return key

def run_analysis_logic(variavel, start_date, end_date, geo_caching_key, aba):
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry: return None 
    
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    # Lógica compartilhada para "Mapas" e "Múltiplos Mapas"
    if aba in ["Mapas", "Múltiplos Mapas"]:
        target_hour = None
        if st.session_state.get('tipo_periodo') == "Horário Específico":
            target_hour = st.session_state.get('hora_especifica')
        
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry, target_hour)
        
        if ee_image:
            results["ee_image"] = ee_image
            # Apenas gera tabela de dados se for mapa único
            if aba == "Mapas":
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
    
    # --- LÓGICA MÚLTIPLOS (MAPAS OU SÉRIES) ---
    if aba in ["Múltiplos Mapas", "Múltiplas Séries"]:
        variaveis = st.session_state.get("variaveis_multiplas", [])
        if not variaveis: return

        tipo_per = st.session_state.tipo_periodo
        if tipo_per == "Horário Específico":
            data_unica = st.session_state.get('data_horaria')
            if data_unica:
                start_date = data_unica
                end_date = data_unica + timedelta(days=1) 
            else: start_date, end_date = None, None
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

    # --- LÓGICA PADRÃO (ÚNICO) ---
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")
    tipo_per = st.session_state.tipo_periodo
    
    if tipo_per == "Horário Específico":
        data_unica = st.session_state.get('data_horaria')
        if data_unica:
            start_date = data_unica
            end_date = data_unica + timedelta(days=1) 
        else: start_date, end_date = None, None
    else:
        start_date, end_date = utils.get_date_range(tipo_per, st.session_state)

    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        with st.spinner("Processando dados no Google Earth Engine..."):
            analysis_data = run_analysis_logic(variavel, start_date, end_date, geo_key, aba)
        
        if analysis_data is None:
            st.warning("Não foi possível obter dados.")
            st.session_state.analysis_results = None
        else:
            st.session_state.analysis_results = analysis_data

    except Exception as e:
        st.error(f"Erro: {e}")
        st.session_state.analysis_results = None

def render_analysis_results():
    aba = st.session_state.get("nav_option", "Mapas")

    # --- RENDERIZAÇÃO SKEW-T ---
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

    # --- Pré-cálculo dos Títulos ---
    tipo_periodo = st.session_state.get('tipo_periodo', '')
    tipo_local = st.session_state.get('tipo_localizacao', '').lower()
    periodo_str, local_str = "", ""
    
    if tipo_periodo == "Personalizado":
        inicio, fim = st.session_state.get('data_inicio'), st.session_state.get('data_fim')
        if inicio and fim: periodo_str = f"de {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mensal":
        mes, ano = st.session_state.get('mes_mensal', ''), st.session_state.get('ano_mensal', '')
        periodo_str = f"mensal ({mes} de {ano})"
    elif tipo_periodo == "Anual":
        ano = st.session_state.get('ano_anual', '')
        periodo_str = f"anual ({ano})"
    elif tipo_periodo == "Horário Específico":
        data = st.session_state.get('data_horaria')
        hora = st.session_state.get('hora_especifica')
        if data: periodo_str = f"em {data.strftime('%d/%m/%Y')} às {hora}:00 (UTC)"
    
    if tipo_local == "estado":
        estado_raw = st.session_state.get('estado', '')
        val = estado_raw.split(' - ')[0] if estado_raw else ""
        local_str = f"no {tipo_local} de {val}"
    elif tipo_local == "município":
        mun = st.session_state.get('municipio', '')
        local_str = f"no {tipo_local} de {mun}"
    elif tipo_local == "polígono": local_str = "para a área desenhada"
    else: local_str = "para o círculo definido"

    # --- RENDERIZAÇÃO MÚLTIPLOS MAPAS ---
    if aba == "Múltiplos Mapas" and results.get("mode") == "multi_map":
        st.subheader("Comparação de Variáveis (Mapas)")
        ui.renderizar_resumo_selecao()
        st.markdown("---")
        
        data_dict = results["data"]
        vars_list = list(data_dict.keys())
        col1, col2 = st.columns(2)
        cols_obj = [col1, col2]
        
        for i, var_name in enumerate(vars_list):
            res_item = data_dict[var_name]
            with cols_obj[i % 2]:
                st.markdown(f"**{var_name}**")
                png, jpg, cbar = map_visualizer.create_static_map(res_item["ee_image"], res_item["feature"], gee_handler.obter_vis_params_interativo(var_name), res_item["var_cfg"]["unit"])
                if png:
                    st.image(png, use_container_width=True)
                    if cbar: st.image(cbar, use_container_width=True)
                    try:
                        titulo_completo = f"{var_name} {periodo_str} {local_str}"
                        title_bytes = map_visualizer._make_title_image(titulo_completo, 800)
                        map_png = base64.b64decode(png.split(",")[1])
                        map_jpg = base64.b64decode(jpg.split(",")[1])
                        cbar_bytes = base64.b64decode(cbar.split(",")[1]) if cbar else None
                        final_png = map_visualizer._stitch_images_to_bytes(title_bytes, map_png, cbar_bytes, format='PNG')
                        final_jpg = map_visualizer._stitch_images_to_bytes(title_bytes, map_jpg, cbar_bytes, format='JPEG')
                        sub_c1, sub_c2 = st.columns(2)
                        var_slug = var_name.lower().replace(" ", "_")
                        if final_png: sub_c1.download_button("💾 PNG", final_png, f"{var_slug}.png", "image/png", use_container_width=True)
                        if final_jpg: sub_c2.download_button("💾 JPG", final_jpg, f"{var_slug}.jpg", "image/jpeg", use_container_width=True)
                    except: pass
        return

    # --- RENDERIZAÇÃO MÚLTIPLAS SÉRIES ---
    if aba == "Múltiplas Séries" and results.get("mode") == "multi_series":
        st.subheader("Comparação de Variáveis (Séries Temporais)")
        ui.renderizar_resumo_selecao()
        
        # --- AJUDA GERAL COMPLETA (IGUAL AO CHART_VISUALIZER) ---
        with st.expander("ℹ️ Ajuda: Entenda os ícones e ferramentas dos gráficos"):
            st.markdown("### 📈 Guia de Ferramentas")
            
            st.markdown("**1️⃣ Barra de Ferramentas (Canto Superior Direito)**")
            st.markdown("""
            * `📷` **Câmera:** Baixa o gráfico atual como imagem (PNG).
            * `🔍` **Zoom:** Clique e arraste na tela para aproximar uma área específica.
            * `✥` **Pan (Mover):** Clique e arraste para mover o gráfico para os lados.
            * `➕` / `➖` **Zoom In/Out:** Aproxima ou afasta a visualização centralizada.
            * `🏠` **Casinha (Reset):** Retorna o gráfico para a visualização original.
            * `🔲` **Autoscale:** Ajusta os eixos automaticamente para caber todos os dados.
            """)
            
            st.markdown("**2️⃣ Interação e Atalhos**")
            st.markdown("""
            * **Zoom Rápido (Botões no topo):** Use `1m` (Mês), `6m` (Semestre), `1a` (Ano) ou `Tudo`.
            * **Valor Exato:** Passe o mouse sobre a linha azul para ver a data e o valor exato (Tooltip).
            * **Tela Cheia:** Passe o mouse no gráfico e procure o ícone `⛶` para expandir.
            """)
        # --------------------------------------------------------
        
        st.markdown("---")
        
        data_dict = results["data"]
        vars_list = list(data_dict.keys())
        col1, col2 = st.columns(2)
        cols_obj = [col1, col2]
        
        for i, var_name in enumerate(vars_list):
            res_item = data_dict[var_name]
            unit = res_item["var_cfg"]["unit"]
            df = res_item["time_series_df"]
            
            with cols_obj[i % 2]:
                st.markdown(f"##### {var_name}")
                # AQUI: show_help=False para não repetir a ajuda
                charts_visualizer.display_time_series_chart(df, var_name, unit, show_help=False)
                st.markdown("---")
        return

    # --- RENDERIZAÇÃO ÚNICA (PADRÃO) ---
    var_cfg = results["var_cfg"]
    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao() 

    variavel = st.session_state.get('variavel', '')
    titulo_mapa = f"{variavel} {periodo_str} {local_str}"
    titulo_serie = f"Série Temporal de {variavel} {periodo_str} {local_str}"

    if aba == "Mapas":
        st.markdown("---") 
        if "ee_image" in results:
            feature = results["feature"]
            tipo_mapa = st.session_state.get("map_type", "Interativo")
            st.subheader(titulo_mapa)
            vis_params = gee_handler.obter_vis_params_interativo(variavel)

            if tipo_mapa == "Interativo":
                with st.popover("ℹ️ Ajuda: Como usar o Mapa"):
                    st.markdown("### 🧭 Guia de Botões")
                    st.markdown("**1️⃣ Navegação e Visualização**")
                    st.markdown("* `➕` / `➖` **Zoom:** Aproxima ou afasta a visão.\n* `⛶` **Tela Cheia:** Expande o mapa.\n* `🗂️` **Camadas:** Alterna Satélite/Ruas.")
                    st.markdown("**2️⃣ Ferramentas de Desenho**")
                    st.markdown("* `📍` **Marcador** | `╱` **Linha** | `⬟` **Polígono** | `⬛` **Retângulo** | `⭕` **Círculo**")
                    st.markdown("**3️⃣ Edição**")
                    st.markdown("* `📝` **Editar** | `🗑️` **Lixeira**")
                map_visualizer.create_interactive_map(results["ee_image"], feature, vis_params, var_cfg["unit"]) 
            
            elif tipo_mapa == "Estático":
                with st.spinner("Gerando imagem estática..."):
                    png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(results["ee_image"], feature, vis_params, var_cfg["unit"])
                if png_url:
                    st.image(png_url, width=500)
                    if colorbar_img: st.image(colorbar_img, width=500)
                    st.markdown("### Exportar Mapas")
                    try:
                        title_bytes = map_visualizer._make_title_image(titulo_mapa, 800)
                        map_png = base64.b64decode(png_url.split(",")[1])
                        map_jpg = base64.b64decode(jpg_url.split(",")[1])
                        cbar = base64.b64decode(colorbar_img.split(",")[1])
                        final_png = map_visualizer._stitch_images_to_bytes(title_bytes, map_png, cbar, format='PNG')
                        final_jpg = map_visualizer._stitch_images_to_bytes(title_bytes, map_jpg, cbar, format='JPEG')
                        c1, c2 = st.columns(2)
                        if final_png: c1.download_button("📷 Baixar Mapa (PNG)", final_png, "mapa.png", "image/png", use_container_width=True)
                        if final_jpg: c2.download_button("📷 Baixar Mapa (JPEG)", final_jpg, "mapa.jpeg", "image/jpeg", use_container_width=True)
                    except: pass

        st.markdown("---") 
        st.subheader("Tabela de Dados") 
        if "map_dataframe" in results and not results["map_dataframe"].empty:
             df_map = results["map_dataframe"]
             cols = df_map.columns.tolist()
             val_col = [c for c in cols if c not in ['Latitude', 'Longitude']][0]
             unit = var_cfg["unit"]
             st.dataframe(
                df_map, 
                use_container_width=True, 
                hide_index=True, 
                column_config={
                    "Latitude": st.column_config.NumberColumn("Latitude", format="%.4f", width="small"), 
                    "Longitude": st.column_config.NumberColumn("Longitude", format="%.4f", width="small"), 
                    val_col: st.column_config.NumberColumn(val_col, format=f"%.2f {unit}", width="medium")
                }
            )
             cd1, cd2 = st.columns(2)
             csv = df_map.to_csv(index=False).encode('utf-8')
             with cd1: st.download_button("Exportar CSV (Dados)", csv, "dados_mapa.csv", "text/csv", use_container_width=True)
             try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer: 
                    df_map.to_excel(writer, index=False, sheet_name='Dados')
                with cd2: 
                    st.download_button("Exportar XLSX (Dados)", buf.getvalue(), "dados_mapa.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
             except: pass

    elif aba == "Séries Temporais":
        if "time_series_df" in results:
            st.subheader(titulo_serie)
            charts_visualizer.display_time_series_chart(results["time_series_df"], st.session_state.variavel, var_cfg["unit"], show_help=True)

def render_polygon_drawer():
    st.subheader("Desenhe sua Área de Interesse")
    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google")
    Draw(export=False, draw_options={"polygon": {"allowIntersection": False, "showArea": True}, "rectangle": {"allowIntersection": False, "showArea": True}, "circle": False, "marker": False, "polyline": False}, edit_options={"edit": True, "remove": True}).add_to(m)
    map_data = st_folium(m, width=None, height=500, returned_objects=["all_drawings"])
    if map_data and map_data.get("all_drawings"):
        drawing = map_data["all_drawings"][-1]
        if drawing["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
            if st.session_state.get('drawn_geometry') != drawing["geometry"]:
                st.session_state.drawn_geometry = drawing["geometry"]
                st.success("✅ Polígono capturado!")
                st.rerun()
    elif 'drawn_geometry' in st.session_state and (not map_data or not map_data.get("all_drawings")):
        del st.session_state['drawn_geometry']
        st.rerun()

def main():
    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True
        mensagem_container = st.empty()
        mensagem_container.success("✅ Conectado ao Google Earth Engine com sucesso!")
        time.sleep(5)
        mensagem_container.empty()
        
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)
    
    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return
    
    ui.renderizar_pagina_principal(opcao_menu)
    
    # Ativa desenho de polígono se necessário
    is_polygon = (
        opcao_menu in ["Mapas", "Múltiplos Mapas", "Séries Temporais", "Múltiplas Séries"] and 
        st.session_state.get('tipo_localizacao') == "Polígono"
    )
        
    is_running = st.session_state.get("analysis_triggered", False)
    has_geom = 'drawn_geometry' in st.session_state
    has_res = "analysis_results" in st.session_state and st.session_state.analysis_results is not None
    
    if is_polygon and not is_running and not has_geom and not has_res: 
        render_polygon_drawer()
    
    if is_running:
        st.session_state.analysis_triggered = False 
        run_full_analysis() 
    
    render_analysis_results()

if __name__ == "__main__": main()
