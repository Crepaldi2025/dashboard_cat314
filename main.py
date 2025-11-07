# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido v41)
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
import folium
from folium.plugins import Draw 
from streamlit_folium import st_folium

# ==================================================================================
# FUNÇÕES DE CACHE (Idênticas)
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
    # (Função idêntica à v31)
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry: return None 
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    if aba == "Mapas":
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None: return None
        results["ee_image"] = ee_image
        df_map_samples = gee_handler.get_sampled_data_as_dataframe(ee_image, geometry, variavel)
        if df_map_samples is not None and not df_map_samples.empty:
            results["map_dataframe"] = df_map_samples
            
        if st.session_state.get("map_type", "Interativo") == "Estático":
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, var_cfg["vis_params"], var_cfg["unit"]
            )
            results["static_map_png_url"] = png_url
            results["static_map_jpg_url"] = jpg_url
            results["static_colorbar_b64"] = colorbar_img

    elif aba == "Séries Temporais":
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is None or df.empty: return None
        results["time_series_df"] = df

    return results

# ---------------------- FUNÇÃO PRINCIPAL DE ANÁLISE (Idêntica) ----------------------
def run_full_analysis():
    # (Função idêntica à v31)
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        spinner_message = "Processando dados no Google Earth Engine..."
        if aba == "Mapas":
            spinner_message = "Processando imagem e amostrando dados... Isso pode levar um momento."
        
        with st.spinner(spinner_message):
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


# ----------------------------------------------------------------------------------
# (Função idêntica à v36 - sem alterações)
# ----------------------------------------------------------------------------------
def render_analysis_results():
    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        return

    results = st.session_state.analysis_results
    aba = st.session_state.get("nav_option", "Mapas")
    
    var_cfg = results["var_cfg"]

    st.markdown("---") 
    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao() 

    # Geração do Título Dinâmico
    variavel = st.session_state.variavel
    tipo_periodo = st.session_state.tipo_periodo
    tipo_local = st.session_state.tipo_localizacao.lower()
    
    if tipo_periodo == "Personalizado":
        start_str = st.session_state.data_inicio.strftime('%d/%m/%Y')
        end_str = st.session_state.data_fim.strftime('%d/%m/%Y')
        periodo_str = f"de {start_str} a {end_str}"
    elif tipo_periodo == "Mensal":
        periodo_str = f"mensal ({st.session_state.mes_mensal} de {st.session_state.ano_mensal})"
    elif tipo_periodo == "Anual":
        periodo_str = f"anual ({st.session_state.ano_anual})"
    
    if tipo_local == "estado":
        local_str = f"no {tipo_local} de {st.session_state.estado.split(' - ')[0]}"
    elif tipo_local == "município":
        local_str = f"no {tipo_local} de {st.session_state.municipio}"
    elif tipo_local == "polígono":
        local_str = "para a área desenhada"
    else: # Círculo
        local_str = "para o círculo definido"
        
    titulo_mapa = f"{variavel} {periodo_str} {local_str}"
    titulo_serie = f"Série Temporal de {variavel} {periodo_str} {local_str}"


    if aba == "Mapas":
        
        st.markdown("---") 
        
        tipo_mapa = st.session_state.get("map_type", "Interativo")
        if "ee_image" not in results:
            st.warning("Não há dados de imagem para exibir.")
            return

        ee_image = results["ee_image"]
        feature = results["feature"]
        vis_params = copy.deepcopy(var_cfg["vis_params"])

        if tipo_mapa == "Interativo":
            st.subheader(titulo_mapa) 
            map_visualizer.create_interactive_map(
                ee_image, 
                feature, 
                vis_params, 
                var_cfg["unit"] 
            ) 

        elif tipo_mapa == "Estático":
            if "static_map_png_url" not in results:
                st.warning("Erro ao gerar mapas estáticos.")
                return
            png_url = results["static_map_png_url"]
            jpg_url = results["static_map_jpg_url"]
            colorbar_b64 = results["static_colorbar_b64"]

            st.subheader(titulo_mapa)
            map_width = 400 
            
            if png_url:
                st.image(png_url, width=map_width)
            if colorbar_b64:
                st.image(colorbar_b64, width=map_width)
            
            st.markdown("---") 
            st.markdown("### Exportar Mapas")
            
            try:
                title_bytes = map_visualizer._make_title_image(titulo_mapa, 800)
                map_png_bytes = base64.b64decode(png_url.split(",")[1])
                map_jpg_bytes = base64.b64decode(jpg_url.split(",")[1])
                colorbar_bytes = base64.b64decode(colorbar_b64.split(",")[1])
                
                final_png_data = map_visualizer._stitch_images_to_bytes(
                    title_bytes, map_png_bytes, colorbar_bytes, format='PNG'
                )
                final_jpg_data = map_visualizer._stitch_images_to_bytes(
                    title_bytes, map_jpg_bytes, colorbar_bytes, format='JPEG'
                )

                if final_png_data:
                    st.download_button("Exportar (PNG)", data=final_png_data, file_name="mapa_completo.png", mime="image/png", use_container_width=True)
                if final_jpg_data:
                    st.download_button("Exportar (JPEG)", data=final_jpg_data, file_name="mapa_completo.jpeg", mime="image/jpeg", use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao preparar imagens para download: {e}")
                st.download_button("Exportar (PNG - Somente Mapa)", data=base64.b64decode(png_url.split(",")[1]), file_name="mapa.png", mime="image/png", use_container_width=True)

        st.markdown("---") 
        st.subheader("Tabela de Dados") 

        if "map_dataframe" not in results or results["map_dataframe"].empty:
            st.warning("Não foi possível extrair dados amostrais para a tabela.")
        else:
            df_map = results["map_dataframe"]
            st.dataframe(df_map, use_container_width=True)
            
            st.subheader("Exportar Tabela")
            
            variavel = st.session_state.variavel
            variable_name = variavel.split(" (")[0]
            df_export = df_map
            file_name_safe = f"mapa_amostras_{variable_name.lower().replace(' ', '_')}"

            csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Dados Amostrais')
            excel_data = excel_buffer.getvalue()

            col_btn_1, col_btn_2 = st.columns(2)
            with col_btn_1:
                st.download_button("Exportar para CSV", data=csv_data, file_name=f"{file_name_safe}.csv", mime="text/csv", use_container_width=True)
            with col_btn_2:
                st.download_button("Exportar para XLSX (Excel)", data=excel_data, file_name=f"{file_name_safe}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    elif aba == "Séries Temporais":
        st.markdown("---")
        st.subheader(titulo_serie)
        
        if "time_series_df" not in results:
            st.warning("Não foi possível extrair a série temporal.")
            return
            
        df = results["time_series_df"]
        
        charts_visualizer.display_time_series_chart(
            df, 
            st.session_state.variavel, 
            var_cfg["unit"] 
        )

# ----------------------------------------------------------------------------------
# CORREÇÃO v41:
# A lógica de captura foi melhorada para não apagar a geometria
# quando o mapa recarrega (ex: ao clicar no rádio "Estático" -> "Interativo")
# ----------------------------------------------------------------------------------
def render_polygon_drawer():
    st.subheader("Desenhe sua Área de Interesse")
    st.info("Use as ferramentas no canto esquerdo do mapa para desenhar um polígono. Clique em 'Gerar Análise' na barra lateral quando terminar.")

    mapa_desenho = folium.Map(
        location=[-15.78, -47.93], 
        zoom_start=4,
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google"
    )

    Draw(
        export=False,
        position="topleft",
        draw_options={
            "polygon": {"allowIntersection": False, "showArea": True},
            "rectangle": {"allowIntersection": False, "showArea": True},
            "circle": False, "marker": False, "circlemarker": False, "polyline": False,
        },
        edit_options={"edit": True, "remove": True}
    ).add_to(mapa_desenho)
    
    map_data = st_folium(
        mapa_desenho, 
        width=None, 
        height=500, 
        use_container_width=True,
        returned_objects=["all_drawings"] 
    )
    
    geometry = None
    
    # --- INÍCIO DA CORREÇÃO v41 ---
    if map_data:
        # Pega a lista de desenhos retornada pelo mapa
        all_drawings = map_data.get("all_drawings")

        # CASO 1: O usuário desenhou algo (a lista não é vazia)
        if all_drawings and len(all_drawings) > 0:
            drawing = all_drawings[-1] 
            if drawing and isinstance(drawing, dict) and drawing.get("geometry"):
                if drawing["geometry"].get("type") in ["Polygon", "MultiPolygon"]:
                    geometry = drawing["geometry"]

        # CASO 2: O usuário apagou o desenho (a lista está explicitamente vazia: [])
        # Isso só acontece se o usuário usar a ferramenta "lixeira" no mapa.
        elif all_drawings == []: 
            if 'drawn_geometry' in st.session_state:
                 del st.session_state['drawn_geometry']
                 st.warning("Polígono removido.")
                 st.rerun()
        
        # CASO 3: O mapa apenas recarregou (all_drawings é None/NULL)
        # Ex: O usuário clicou em "Gerar Análise" ou trocou de "Estático" para "Interativo".
        # Neste caso, não fazemos NADA. O 'geometry' continua None.
        elif all_drawings is None:
            pass 
    
    # Lógica de validação (separada)
    if geometry:
        # Se uma nova geometria válida foi capturada (CASO 1)...
        if st.session_state.get('drawn_geometry') != geometry:
            st.session_state.drawn_geometry = geometry
            st.success("✅ Polígono capturado!")
            st.rerun() # Recarrega para habilitar o botão
            
    # A lógica 'else' que apagava o estado foi removida.
    # O estado só é apagado se o usuário *explicitamente* apagar (CASO 2).
    # --- FIM DA CORREÇÃO v41 ---

    
# ----------------------------------------------------------------------------------
# CORREÇÃO v41:
# A lógica de renderização do mapa de desenho foi ajustada para
# não apagar o polígono quando os resultados já existem.
# ----------------------------------------------------------------------------------
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
    
    # --- INÍCIO DA CORREÇÃO v41 ---
    # Define quando mostrar o mapa de desenho vs. os resultados
    
    # Estamos no modo Polígono?
    is_polygon_mode = (
        opcao_menu == "Mapas" and 
        st.session_state.get('tipo_localizacao') == "Polígono"
    )
    
    # A análise já foi disparada?
    is_analysis_running = st.session_state.get("analysis_triggered", False)
    
    # Já temos resultados para mostrar?
    has_results = "analysis_results" in st.session_state and st.session_state.analysis_results is not None

    # SÓ mostre o mapa de desenho se:
    # 1. Estamos no modo Polígono
    # 2. A análise NÃO está rodando agora
    # 3. NÃO há resultados para mostrar
    if is_polygon_mode and not is_analysis_running and not has_results:
        render_polygon_drawer()

    # Lógica de Execução
    if is_analysis_running:
        st.session_state.analysis_triggered = False 
        run_full_analysis() 

    # Lógica de Renderização de Resultados
    # (A função render_analysis_results() já verifica internamente se 'analysis_results' existe)
    render_analysis_results()
    # --- FIM DA CORREÇÃO v41 ---


if __name__ == "__main__":
    main()
