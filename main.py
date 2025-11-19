# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido v47)
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
import streamlit as st

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
        /* Cria uma camada branca (rgba 255,255,255) com a opacidade definida acima da imagem */
        background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), 
                          url("{image_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stContainer {{ /* Estilo para o container principal */
        background-color: rgba(255, 255, 255, 0.85); /* Fundo semi-transparente para o conteúdo */
        padding: 10px;
        border-radius: 10px;
    }}
    /* Corrigir o fundo do sidebar */
    .css-161cc6e {{ /* Seletor comum para o sidebar no Streamlit */
        background-color: rgba(255, 255, 255, 0.95);
    }}
    /* Corrigir o fundo da tab */
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
        background-color: #4CAF50; /* Verde */
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
    (Função idêntica à v41)
    """
    try:
        # 1. Definir FeatureCollection e Nome da Localização
        if tipo_localizacao == "Estado":
            feature_collection, local_name = gee_handler.get_brazil_state(uf)
        elif tipo_localizacao == "Município":
            feature_collection, local_name = gee_handler.get_brazil_municipality(uf, municipio)
        elif tipo_localizacao == "Polígono":
            feature_collection, local_name = gee_handler.convert_geojson_to_ee(drawn_geometry), "Polígono Personalizado"
        
        # 2. Obter Parâmetros da Variável
        dataset, band, unit = gee_handler.get_variable_params(variavel_analise)

        # 3. Executar o Mapeamento
        ee_image, vis_params = gee_handler.get_gee_image(dataset, band, start_date, end_date)
        
        # 4. Gerar Mapa Interativo e Dados para Download
        map_html, map_title, map_download_data = map_visualizer.create_interactive_map(
            ee_image=ee_image, 
            feature=feature_collection.first(), # Pega a primeira feature para o mapa
            vis_params=vis_params, 
            unit_label=unit,
            variable_label=variavel_analise
        )

        # 5. Executar a Série Temporal (apenas para o primeiro elemento/feature)
        time_series_data = gee_handler.extract_time_series_for_feature(
            dataset=dataset,
            band=band,
            start_date=start_date,
            end_date=end_date,
            feature=feature_collection.first(),
            # Parâmetros de agregação (mantidos como padrão)
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
    (Função idêntica à v41)
    """
    st.session_state.analysis_results = None
    st.session_state.analysis_triggered = True
    
    try:
        start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    except Exception as e:
        st.error(f"Erro ao definir o intervalo de datas: {e}")
        return

    st.session_state.analysis_results = run_analysis(
        st.session_state.tipo_localizacao, 
        st.session_state.uf_selecionado, 
        st.session_state.municipio_selecionado, 
        st.session_state.drawn_geometry if 'drawn_geometry' in st.session_state else None, 
        st.session_state.tipo_periodo, 
        st.session_state.variavel_analise, 
        start_date, 
        end_date
    )
    
    st.session_state.analysis_triggered = False


def clear_results_callback():
    """
    (Função idêntica à v41)
    """
    st.session_state.analysis_results = None
    st.session_state.drawn_geometry = None
    st.session_state.map_key = st.session_state.get('map_key', 0) + 1
    st.session_state.map_initialized = False


def handle_polygon_drawing(drawn_items):
    """
    (v47) - **CORREÇÃO CRÍTICA**: Remove st.rerun() e usa apenas o estado.
    
    Verifica se um polígono ou círculo foi desenhado.
    Se sim, salva a geometria e define o estado para mostrar a mensagem de sucesso.
    """
    if drawn_items and 'features' in drawn_items:
        # Percorre as features desenhadas
        for feature in drawn_items['features']:
            if feature['geometry']['type'] in ['Polygon', 'Circle']:
                # Salva apenas a última geometria desenhada
                st.session_state.drawn_geometry = feature['geometry']
                st.session_state.geometry_is_drawn = True # Novo estado
                st.session_state.show_success_message = True # Mensagem de sucesso na próxima execução
                # **NÃO FORÇA O RERUN AQUI**
                return
    
    # Se não houver geometria ou o usuário apagou, limpa o estado
    if st.session_state.get('drawn_geometry') and (not drawn_items or not drawn_items.get('features')):
         st.session_state.drawn_geometry = None
         st.session_state.geometry_is_drawn = False
         st.session_state.show_success_message = False


# ----------------------------------------------------------------------------------
# (Função main - Lógica alterada para Polígono)
# ----------------------------------------------------------------------------------
def main():
    set_background()

    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True

    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    
    # Renderiza a sidebar, que atualiza vários itens em st.session_state
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    # Renderiza o corpo principal da página (onde o mapa pode ser exibido)
    ui.renderizar_pagina_principal(opcao_menu)

    # ==================================================================
    # [CORREÇÃO] TRECHO QUE FALTAVA
    # Verifica se o botão foi clicado e executa a função de análise
    # ==================================================================
    if st.session_state.get("analysis_triggered"):
        with st.spinner("🔄 Processando dados climáticos... Por favor, aguarde."):
            run_analysis_callback()
    # ==================================================================

    # Renderiza o corpo principal da página (onde o mapa pode ser exibido)
    ui.renderizar_pagina_principal(opcao_menu)
    
    # --------------------------------------------------------------------------
    # LÓGICA DE EXIBIÇÃO DA ANÁLISE E DO MAPA PARA POLÍGONO
    # --------------------------------------------------------------------------
    
    is_polygon_mode = (
        opcao_menu == "Mapas" and 
        st.session_state.get('tipo_localizacao') == "Polígono"
    )
    is_analysis_running = st.session_state.get("analysis_triggered", False)
    has_geometry = 'drawn_geometry' in st.session_state and st.session_state.drawn_geometry is not None
    has_results = "analysis_results" in st.session_state and st.session_state.analysis_results is not None
    
    # Lógica para o modo Polígono
    if is_polygon_mode:
        
        # 1. Renderiza o Mapa de Desenho
        # Usa uma chave única para garantir que o mapa seja recarregado se a geomatria mudar
        map_key = st.session_state.get('map_key', 0)
        
        # Cria o mapa de folium (agora com um localizador de placeholder)
        m = folium.Map(location=[-14.235, -51.9253], zoom_start=4, control_scale=True, tiles="OpenStreetMap", key=map_key)
        
        # Adiciona a funcionalidade de Desenho
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

        # Se houver uma geometria desenhada anteriormente, adicione-a ao mapa
        if has_geometry:
            folium.GeoJson(st.session_state.drawn_geometry, name="Geometria Anterior").add_to(m)
        
        # Exibe o mapa e captura os itens desenhados
        # Esta é a parte que causa o rerun
        output = st_folium(m, width=700, height=500, key=f"polygon_map_{map_key}")
        
        # 2. Manipula o desenho
        if output and 'all_draw_features' in output:
            handle_polygon_drawing(output['all_draw_features'])
        
        # 3. Exibe mensagens de status
        if is_analysis_running:
            st.info("⌛ Processando análise no Google Earth Engine...")
        elif st.session_state.get('show_success_message'):
             st.success("✅ Polígono/Círculo capturado! Clique em **Executar Análise**.")
             st.session_state.show_success_message = False # Limpa a mensagem

        # 4. Botão de Limpar Geometria (apenas se houver geometria)
        if has_geometry:
            st.button("❌ Limpar Polígono/Círculo", on_click=clear_results_callback, use_container_width=True)
            
        # 5. Exibe os resultados (se existirem)
        if has_results:
            charts_visualizer.render_results_if_available(st.session_state)
            
    else:
        # Se não for modo Polígono, apenas exibe os resultados se existirem
        if has_results:
            charts_visualizer.render_results_if_available(st.session_state)


if __name__ == "__main__":
    main()

