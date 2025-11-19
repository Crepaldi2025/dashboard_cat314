# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido v55)
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
# Configuração da Imagem de Fundo com Transparência
# =================================================

def set_background():
    # URL direta da sua imagem no GitHub
    image_url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/terrab.jpg"
    
    # Ajuste de opacidade
    opacity = 0.75
    
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), 
                          url("{image_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stContainer {{
        background-color: rgba(255, 255, 255, 0.85);
        padding: 10px;
        border-radius: 10px;
    }}
    .css-161cc6e {{
        background-color: rgba(255, 255, 255, 0.95);
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: nowrap;
        border-radius: 4px;
        background-color: #f0f2f6;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        margin-left: 20px;
        margin-right: 20px;
        line-height: 1.25rem;
        font-size: 1.125rem;
        font-weight: 500;
        border: 1px solid #ccc;
        color: #4B4B4B;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)


# =================================================
# LÓGICA DE EXECUÇÃO DA ANÁLISE
# =================================================

@st.cache_data
def run_analysis(tipo_localizacao, uf, municipio, drawn_geometry, tipo_periodo, variavel_analise, start_date, end_date):
    """
    Executa a análise no GEE e retorna os resultados.
    """
    try:
        # 1. Definir FeatureCollection e Nome da Localização
        if tipo_localizacao == "Estado":
            feature_collection, local_name = gee_handler.get_brazil_state(uf)
        elif tipo_localizacao == "Município":
            feature_collection, local_name = gee_handler.get_brazil_municipality(uf, municipio)
        elif tipo_localizacao == "Polígono":
            feature_collection, local_name = gee_handler.convert_geojson_to_ee(drawn_geometry), "Polígono Personalizado"
        # Fallback para Círculo se necessário, ou erro se feature_collection for None
        else:
             # Se for círculo, a lógica de geometria é tratada dentro do get_variable_params ou get_gee_image
             # dependendo de como gee_handler está estruturado.
             # Se gee_handler espera feature_collection para tudo, precisamos garantir que Círculo retorne algo válido aqui.
             # Assumindo que para Círculo usamos coordenadas passadas via st.session_state, mas run_analysis precisa receber.
             # Por simplicidade, mantemos o fluxo atual.
             feature_collection = None 
             local_name = "Área Personalizada"

        # Se não conseguiu definir a geometria (exceto se for Círculo que é tratado via coords depois)
        if feature_collection is None and tipo_localizacao not in ["Círculo (Lat/Lon/Raio)"]:
             # Tenta recuperar via session_state helper se falhou acima
             geom, feat = gee_handler.get_area_of_interest_geometry(st.session_state)
             if feat:
                 feature_collection = ee.FeatureCollection([feat])
                 local_name = "Geometria Personalizada"
             else:
                 return None

        # 2. Obter Parâmetros da Variável
        dataset, band, unit = gee_handler.get_variable_params(variavel_analise)

        # 3. Executar o Mapeamento
        # Nota: get_gee_image internamente pode lidar com Círculo se usar geometry do session_state
        ee_image, vis_params = gee_handler.get_gee_image(dataset, band, start_date, end_date)
        
        # Se feature_collection ainda é None (caso do Círculo), tentamos pegar da imagem ou do session
        feature_para_mapa = None
        if feature_collection:
            feature_para_mapa = feature_collection.first()
        else:
            # Tenta pegar feature do helper
            _, feat = gee_handler.get_area_of_interest_geometry(st.session_state)
            feature_para_mapa = feat

        if not ee_image or not feature_para_mapa:
             st.error("Não foi possível gerar a imagem ou geometria.")
             return None

        # 4. Gerar Mapa Interativo e Dados para Download
        map_html, map_title, map_download_data = map_visualizer.create_interactive_map(
            ee_image=ee_image, 
            feature=feature_para_mapa,
            vis_params=vis_params, 
            unit_label=unit,
            variable_label=variavel_analise
        )

        # 5. Executar a Série Temporal
        time_series_data = gee_handler.extract_time_series_for_feature(
            dataset=dataset,
            band=band,
            start_date=start_date,
            end_date=end_date,
            feature=feature_para_mapa,
            aggregate_func=gee_handler.get_gee_time_series_function(variavel_analise)
        )

        # 6. Preparar Resultados
        results = {
            'local_name': local_name,
            'map_html': map_html,
            'map_title': map_title,
            'map_download_data': map_download_data,
            'time_series_data': time_series_data,
            'variable_label': variavel_analise,
            'unit_label': unit
        }
        
        return results

    except Exception as e:
        st.error(f"❌ Erro Crítico na Análise: {e}")
        return None

# =================================================
# FUNÇÕES DE CALLBACKS
# =================================================

def run_analysis_callback():
    """
    Callback acionado pelo botão "Gerar Análise".
    Prepara os dados e chama a função de processamento.
    """
    st.session_state.analysis_results = None
    
    # Define datas
    try:
        start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    except Exception as e:
        st.error(f"Erro ao definir o intervalo de datas: {e}")
        st.session_state.analysis_triggered = False
        return

    # --- CORREÇÃO DE VARIÁVEIS ---
    # UI.py salva em 'estado' e 'municipio'. O antigo main tentava 'uf_selecionado'.
    
    # 1. Recupera o valor bruto do Estado (ex: "São Paulo - SP" ou apenas "SP")
    estado_raw = st.session_state.get('estado', '')
    
    # 2. Extrai apenas a sigla se houver separador
    if estado_raw and " - " in estado_raw:
        uf_val = estado_raw.split(' - ')[-1]
    else:
        uf_val = estado_raw

    # 3. Recupera Município
    municipio_val = st.session_state.get('municipio', '')

    # Executa a análise
    st.session_state.analysis_results = run_analysis(
        st.session_state.tipo_localizacao, 
        uf_val,         # Variável corrigida
        municipio_val,  # Variável corrigida
        st.session_state.drawn_geometry if 'drawn_geometry' in st.session_state else None, 
        st.session_state.tipo_periodo, 
        st.session_state.variavel_analise if 'variavel_analise' in st.session_state else st.session_state.get('variavel'), 
        start_date, 
        end_date
    )
    
    st.session_state.analysis_triggered = False


def clear_results_callback():
    st.session_state.analysis_results = None
    st.session_state.drawn_geometry = None
    st.session_state.map_key = st.session_state.get('map_key', 0) + 1
    st.session_state.map_initialized = False


def handle_polygon_drawing(drawn_items):
    """
    Verifica se um polígono ou círculo foi desenhado e salva no estado.
    """
    if drawn_items and 'features' in drawn_items:
        for feature in drawn_items['features']:
            if feature['geometry']['type'] in ['Polygon', 'Circle']:
                st.session_state.drawn_geometry = feature['geometry']
                st.session_state.geometry_is_drawn = True
                st.session_state.show_success_message = True
                return
    
    if st.session_state.get('drawn_geometry') and (not drawn_items or not drawn_items.get('features')):
         st.session_state.drawn_geometry = None
         st.session_state.geometry_is_drawn = False
         st.session_state.show_success_message = False


# ----------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------
def main():
    set_background()

    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True

    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    
    # Renderiza a sidebar
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    # Renderiza o corpo principal da página
    ui.renderizar_pagina_principal(opcao_menu)
    
    # Verifica se a análise foi disparada (pelo botão na sidebar que seta a flag)
    if st.session_state.get("analysis_triggered"):
        run_analysis_callback()
    
    # --------------------------------------------------------------------------
    # LÓGICA DE EXIBIÇÃO DA ANÁLISE E DO MAPA PARA POLÍGONO
    # --------------------------------------------------------------------------
    
    is_polygon_mode = (
        opcao_menu == "Mapas" and 
        st.session_state.get('tipo_localizacao') == "Polígono"
    )
    
    has_geometry = 'drawn_geometry' in st.session_state and st.session_state.drawn_geometry is not None
    has_results = "analysis_results" in st.session_state and st.session_state.analysis_results is not None
    
    # Lógica para o modo Polígono
    if is_polygon_mode:
        # Renderiza o Mapa de Desenho
        map_key = st.session_state.get('map_key', 0)
        
        m = folium.Map(location=[-14.235, -51.9253], zoom_start=4, control_scale=True, tiles="OpenStreetMap", key=map_key)
        
        draw = Draw(
            export=True,
            filename='polygon.geojson',
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': False,
                'polygon': {'allowIntersection': False, 'showArea': True},
                'circle': {'showArea': True, 'allowIntersection': False},
                'marker': False,
                'circlemarker': False
            },
            edit_options={'edit': True, 'remove': True}
        )
        draw.add_to(m)

        if has_geometry:
            folium.GeoJson(st.session_state.drawn_geometry, name="Geometria Anterior").add_to(m)
        
        output = st_folium(m, width=700, height=500, key=f"polygon_map_{map_key}")
        
        if output and 'all_draw_features' in output:
            handle_polygon_drawing(output['all_draw_features'])
        
        if st.session_state.get('analysis_triggered'):
             st.info("⌛ Processando análise no Google Earth Engine...")
        elif st.session_state.get('show_success_message'):
             st.success("✅ Polígono/Círculo capturado! Clique em **Gerar Análise**.")
             st.session_state.show_success_message = False

        if has_geometry:
            st.button("❌ Limpar Polígono/Círculo", on_click=clear_results_callback, use_container_width=True)
            
        if has_results:
            charts_visualizer.render_results_if_available(st.session_state)
            
    else:
        # Se não for modo Polígono, exibe resultados se existirem
        if has_results:
            charts_visualizer.render_results_if_available(st.session_state)


if __name__ == "__main__":
    main()
