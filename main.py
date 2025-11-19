# ==================================================================================
# main.py — Clima-Cast-Crepaldi (v67 - Tabela Padronizada)
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

# =================================================
# Configuração da Imagem de Fundo
# =================================================

def set_background():
    image_url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/terrab.jpg"
    opacity = 0.7
    
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), 
                          url("{image_url}");
        background-size: cover; 
        background-position: center center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_background()

# ==================================================================================
# FUNÇÕES DE CACHE E LÓGICA
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

def run_analysis_logic(variavel, start_date, end_date, geo_caching_key, aba):
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

def run_full_analysis():
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
            spinner_message = "Processando imagem e amostrando dados..."
        
        with st.spinner(spinner_message):
            analysis_data = run_analysis_logic(
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


# ==================================================================================
# RENDERIZAÇÃO (PADRONIZADA)
# ==================================================================================
def render_analysis_results():
    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        return

    results = st.session_state.analysis_results
    aba = st.session_state.get("nav_option", "Mapas")
    var_cfg = results["var_cfg"]

    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao() 

    # Variáveis de Título
    variavel = st.session_state.get('variavel', '')
    tipo_periodo = st.session_state.get('tipo_periodo', '')
    tipo_local = st.session_state.get('tipo_localizacao', '').lower()
    
    periodo_str = ""
    local_str = ""
    
    if tipo_periodo == "Personalizado":
        inicio = st.session_state.get('data_inicio')
        fim = st.session_state.get('data_fim')
        if inicio and fim:
            periodo_str = f"de {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mensal":
        mes = st.session_state.get('mes_mensal', '')
        ano = st.session_state.get('ano_mensal', '')
        periodo_str = f"mensal ({mes} de {ano})"
    elif tipo_periodo == "Anual":
        ano = st.session_state.get('ano_anual', '')
        periodo_str = f"anual ({ano})"
    
    if tipo_local == "estado":
        estado_raw = st.session_state.get('estado', '')
        val = estado_raw.split(' - ')[0] if estado_raw else ""
        local_str = f"no {tipo_local} de {val}"
    elif tipo_local == "município":
        mun = st.session_state.get('municipio', '')
        local_str = f"no {tipo_local} de {mun}"
    elif tipo_local == "polígono":
        local_str = "para a área desenhada"
    else: 
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
            with st.popover("ℹ️ Ajuda: Botões do Mapa Interativo"):
                st.markdown("""
                **Controles de Navegação e Visualização:**
                * **Zoom (+/-):** Aproxima ou afasta a visualização do mapa.
                * **Tela Cheia (⛶):** Expande o mapa para ocupar toda a tela.
                * **Camadas (🗂️):** Alterna entre Satélite e Mapa de Ruas.
                
                **Ferramentas de Desenho (Barra Esquerda):**
                * **Linha (╱):** Desenhar rotas.
                * **Polígono (⬟):** Desenhar áreas irregulares.
                * **Retângulo (⬛):** Desenhar áreas quadradas.
                * **Círculo (⭕):** Desenhar áreas circulares.
                * **Marcador (📍):** Adicionar pontos.
                * **Editar (📝):** Mover/Alterar desenhos.
                * **Lixeira (🗑️):** Apagar desenhos.
                """)
            
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
            if png_url: st.image(png_url, width=400)
            if colorbar_b64: st.image(colorbar_b64, width=400)
            
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

                col_exp1, col_exp2 = st.columns(2)
                if final_png_data:
                    with col_exp1:
                        st.download_button(
                            label="📷 Baixar Mapa (PNG)", 
                            data=final_png_data, 
                            file_name="mapa_completo.png", 
                            mime="image/png", 
                            use_container_width=True
                        )
                if final_jpg_data:
                    with col_exp2:
                        st.download_button(
                            label="📷 Baixar Mapa (JPEG)", 
                            data=final_jpg_data, 
                            file_name="mapa_completo.jpeg", 
                            mime="image/jpeg", 
                            use_container_width=True
                        )

            except Exception as e:
                st.error(f"Erro na exportação: {e}")
                if png_url:
                    st.download_button("📷 Baixar Mapa (Somente Imagem)", data=base64.b64decode(png_url.split(",")[1]), file_name="mapa.png", mime="image/png", use_container_width=True)

        st.markdown("---") 
        st.subheader("Tabela de Dados") 

        if "map_dataframe" not in results or results["map_dataframe"].empty:
            st.warning("Não foi possível extrair dados amostrais.")
        else:
            df_map = results["map_dataframe"]
            
            # --- CONFIGURAÇÃO DE TABELA PROFISSIONAL PARA O MAPA ---
            # Identifica dinamicamente a coluna de valor (que não é Lat/Lon)
            cols = df_map.columns.tolist()
            val_col = [c for c in cols if c not in ['Latitude', 'Longitude']][0]
            unit = var_cfg["unit"]
            
            st.dataframe(
                df_map, 
                use_container_width=True,
                hide_index=True, # Esconde o índice numérico
                column_config={
                    "Latitude": st.column_config.NumberColumn(
                        "Latitude", format="%.4f", width="small"
                    ),
                    "Longitude": st.column_config.NumberColumn(
                        "Longitude", format="%.4f", width="small"
                    ),
                    val_col: st.column_config.NumberColumn(
                        val_col,
                        format=f"%.2f {unit}", # Adiciona a unidade (ex: 25.00 °C)
                        width="medium"
                    )
                }
            )
            # -------------------------------------------------------
            
            col_d1, col_d2 = st.columns(2)
            
            csv = df_map.to_csv(index=False).encode('utf-8')
            with col_d1:
                st.download_button(
                    label="Exportar CSV (Dados)", 
                    data=csv, 
                    file_name="dados_mapa.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )
            
            try:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_map.to_excel(writer, index=False, sheet_name='Dados Amostrais')
                excel_data = excel_buffer.getvalue()
                with col_d2:
                    st.download_button(
                        label="Exportar XLSX (Dados)", 
                        data=excel_data, 
                        file_name="dados_mapa.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                        use_container_width=True
                    )
            except Exception as e:
                st.warning("Biblioteca openpyxl não encontrada.")

    elif aba == "Séries Temporais":
        st.markdown("---")
        st.subheader(titulo_serie)
        
        if "time_series_df" not in results:
            st.warning("Não foi possível extrair a série temporal.")
            return
            
        df = results["time_series_df"]
        charts_visualizer.display_time_series_chart(df, st.session_state.variavel, var_cfg["unit"])

def render_polygon_drawer():
    st.subheader("Desenhe sua Área de Interesse")
    
    m = folium.Map(
        location=[-15.78, -47.93], 
        zoom_start=4,
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", 
        attr="Google"
    )

    Draw(
        export=False,
        draw_options={
            "polygon": {"allowIntersection": False, "showArea": True},
            "rectangle": {"allowIntersection": False, "showArea": True},
            "circle": False, "marker": False, "polyline": False,
        },
        edit_options={"edit": True, "remove": True}
    ).add_to(m)
    
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

if __name__ == "__main__":
    main()
