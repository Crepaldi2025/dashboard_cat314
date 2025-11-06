# ==================================================================================
# main.py — Clima-Cast-Crepaldi (Corrigido)
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
import geemap.foliumap as geemap # Para o mapa de desenho (P7)
from streamlit_folium import st_folium # Para o mapa de desenho (P7)

# ---------------------- CONFIGURAÇÃO DE LOCALE ----------------------
# (Movido para ui.py, que é importado antes de tudo)

# ==================================================================================
# CORREÇÃO P1 e P2: FUNÇÕES DE CACHE
# ==================================================================================
# O cache não pode lidar com objetos 'ee.Geometry'.
# Criamos uma 'chave' de cache com base nas *seleções* do usuário.

def get_geo_caching_key(session_state):
    """Cria uma string 'hashable' única para os parâmetros de localização."""
    loc_type = session_state.get('tipo_localizacao')
    key = f"loc_type:{loc_type}"
    if loc_type == "Estado":
        key += f"|estado:{session_state.get('estado')}"
    elif loc_type == "Município":
        key += f"|estado:{session_state.get('estado')}|municipio:{session_state.get('municipio')}"
    elif loc_type == "Círculo (Lat/Lon/Raio)":
        key += f"|lat:{session_state.get('latitude')}|lon:{session_state.get('longitude')}|raio:{session_state.get('raio')}"
    elif loc_type == "Polígono":
        # O hash da geometria desenhada é o bastante
        key += f"|geojson:{hash(str(session_state.get('drawn_geometry')))}"
    return key

@st.cache_data(ttl=3600) # Cache de 1 hora
def cached_run_analysis(variavel, start_date, end_date, geo_caching_key, aba):
    """
    Função cacheada que busca os dados do GEE.
    Executa a parte "lenta" da análise.
    """
    
    # 1. Recriar a geometria (rápido, não precisa de cache)
    #    (Usamos st.session_state, o que é seguro em funções cacheadas
    #     SE elas forem recriadas com base na chave de cache)
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry:
        # st.warning não funciona bem aqui, então retornamos None
        return None 

    # 2. Obter configurações da variável
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg:
        return None

    # 3. Executar a análise de GEE (lento)
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    if aba == "Mapas":
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry)
        if ee_image is None:
            return None
        results["ee_image"] = ee_image
        
        # Gera mapas estáticos se necessário (lento)
        if st.session_state.get("map_type", "Interativo") == "Estático":
            png_url, jpg_url, colorbar_img = map_visualizer.create_static_map(
                ee_image, feature, var_cfg["vis_params"], var_cfg["unit"]
            )
            results["static_maps"] = (png_url, jpg_url, colorbar_img)

    elif aba == "Séries Temporais":
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is None or df.empty:
            return None
        results["time_series_df"] = df

    return results


# ---------------------- FUNÇÃO PRINCIPAL DE ANÁLISE ----------------------
def run_full_analysis():
    """
    Orquestra a análise e armazena os resultados no st.session_state.
    (CORREÇÃO P2)
    """
    aba = st.session_state.get("nav_option", "Mapas")
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")

    # Período
    start_date, end_date = utils.get_date_range(st.session_state.tipo_periodo, st.session_state)
    if not (start_date and end_date):
        st.warning("Selecione um período válido.")
        return

    # Chave de cache para os parâmetros
    geo_key = get_geo_caching_key(st.session_state)
    
    try:
        with st.spinner("Processando dados no Google Earth Engine... Isso pode levar um momento."):
            # Chama a função CACHEADA
            analysis_data = cached_run_analysis(
                variavel, start_date, end_date, geo_key, aba
            )
        
        if analysis_data is None:
            st.warning("Não foi possível obter dados para a seleção. Verifique os parâmetros.")
            st.session_state.analysis_results = None # Limpa resultados antigos
        else:
            # Sucesso! Salva os resultados no session_state para renderização.
            st.session_state.analysis_results = analysis_data

    except Exception as e:
        # Se o cache falhar (ex: erro no GEE), exibe o erro
        st.error(f"Ocorreu um erro durante a análise: {e}")
        st.session_state.analysis_results = None


def render_analysis_results():
    """
    Renderiza os resultados que estão salvos em st.session_state.analysis_results.
    (CORREÇÃO P2)
    """
    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        # Nenhum resultado para mostrar
        return

    results = st.session_state.analysis_results
    aba = st.session_state.get("nav_option", "Mapas")
    
    st.markdown("---")
    st.subheader("Resultado da Análise")
    ui.renderizar_resumo_selecao() # Mostra o resumo do que foi analisado

    # -------------------- Aba MAPAS --------------------
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
                st.download_button(
                    "Exportar (PNG)",
                    data=base64.b64decode(png_url.split(",")[1]),
                    file_name="mapa.png",
                    mime="image/png",
                    use_container_width=True,
                )
            if jpg_url:
                st.download_button(
                    "Exportar (JPEG)",
                    data=base64.b64decode(jpg_url.split(",")[1]),
                    file_name="mapa.jpeg",
                    mime="image/jpeg",
                    use_container_width=True,
                )

    # -------------------- Aba SÉRIES TEMPORAIS --------------------
    elif aba == "Séries Temporais":
        if "time_series_df" not in results:
            st.warning("Não foi possível extrair a série temporal.")
            return
            
        df = results["time_series_df"]
        var_cfg = results["var_cfg"]
        charts_visualizer.display_time_series_chart(df, st.session_state.variavel, var_cfg["unit"])


def render_polygon_drawer():
    """
    Renderiza um mapa para o usuário desenhar um polígono.
    (CORREÇÃO P7)
    """
    st.subheader("Desenhe sua Área de Interesse")
    st.info("Use as ferramentas no canto esquerdo do mapa para desenhar um polígono. Clique em 'Gerar Análise' na barra lateral quando terminar.")

    mapa_desenho = geemap.Map(center=[-15.78, -47.93], zoom=4)
    mapa_desenho.add_basemap("SATELLITE")
    
    # Usa st_folium para capturar os desenhos
    map_data = st_folium(
        mapa_desenho, 
        width=None, 
        height=500, 
        use_container_width=True,
        # Especifica que queremos os desenhos de volta
        feature_group_name="Polígono Desenhado", 
        returned_objects=["last_active_drawing"]
    )

    # Verifica se o usuário desenhou algo
    if map_data and map_data.get("last_active_drawing"):
        drawing = map_data["last_active_drawing"]
        # Salva a geometria no estado
        st.session_state.drawn_geometry = drawing["geometry"]
        st.success("✅ Polígono capturado! Você já pode clicar em 'Gerar Análise'.")


# ---------------------- FUNÇÃO MAIN ----------------------
def main():
    # Inicializa GEE (só roda uma vez)
    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True

    # Layout base
    # (st.set_page_config() foi movido para ui.py)
    # ui.configurar_pagina() # (Chamada em ui.py)

    # Sidebar e seleção
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)

    # -------------------- SOBRE --------------------
    if opcao_menu == "Sobre o Aplicativo":
        ui.renderizar_pagina_sobre()
        return

    # -------------------- PRINCIPAL --------------------
    ui.renderizar_pagina_principal(opcao_menu)
    
    # -------------------- CORREÇÃO P7: Mapa de Desenho --------------------
    # Se a aba for "Mapas" e o tipo "Polígono", mostra o mapa de desenho
    if opcao_menu == "Mapas" and st.session_state.get('tipo_localizacao') == "Polígono":
        render_polygon_drawer()

    # -------------------- CORREÇÃO P2: Lógica de Estado --------------------
    
    # 1. Se o botão "Gerar Análise" foi clicado:
    if st.session_state.get("analysis_triggered", False):
        # Zera o gatilho para evitar re-análise em cada rerun
        st.session_state.analysis_triggered = False 
        
        # Chama a função que executa a análise e salva os resultados no estado
        run_full_analysis() 

    # 2. Sempre tenta renderizar os resultados que estão no estado:
    #    (Isso garante que os resultados permaneçam na tela)
    render_analysis_results()


# ---------------------- EXECUÇÃO DIRETA ----------------------
if __name__ == "__main__":
    main()