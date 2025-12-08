# ==================================================================================
# main.py 
# ==================================================================================
import streamlit as st
import ui
import gee_handler
import map_visualizer
import charts_visualizer
import utils
import base64 
import io
import pandas as pd
import time
import folium
from folium.plugins import Draw 
from streamlit_folium import st_folium
from datetime import timedelta 
import skewt_handler 
import skewt_visualizer

# --- CONFIGURAÇÃO INICIAL ---
def set_background():
    image_url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/terrab.jpg"
    opacity = 0.7
    page_bg_img = f"""<style>.stApp {{background-image: linear-gradient(rgba(255, 255, 255, {opacity}), rgba(255, 255, 255, {opacity})), url("{image_url}"); background-size: cover; background-position: center center; background-repeat: no-repeat; background-attachment: fixed;}}</style>"""
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_background()

# --- FUNÇÃO DE AJUDA DOS GRÁFICOS (RESTAURADA COMPLETA) ---
def render_chart_tips():
    with st.expander("ℹ️ Ajuda: Entenda os ícones e ferramentas do gráfico"):
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

# --- FUNÇÃO DE AJUDA DO MAPA (RESTAURADA COMPLETA) ---
def render_map_tips():
    with st.popover("ℹ️ Ajuda: Ferramentas do Mapa"):
        st.markdown("### 🗺️ Guia de Navegação")
        st.markdown("**1️⃣ Controles de Visualização**")
        st.markdown("""
        * `➕` / `➖` **Zoom:** Aproxime ou afaste a visão do mapa.
        * `⛶` **Tela Cheia:** Expande o mapa para ocupar todo o monitor (ícone lateral).
        * `🗂️` **Camadas:** (Ícone no topo direito) Alterne entre Dados e Contorno.
        """)
        st.markdown("**2️⃣ Desenho e Marcação (Barra Lateral Esquerda)**")
        st.markdown("""
        * `⬟` **Polígono:** Desenhe áreas livres (clique ponto a ponto).
        * `⬛` **Retângulo:** Desenhe áreas quadradas (clique e arraste).
        * `⭕` **Círculo:** Desenhe uma área circular (clique no centro e arraste).
        * `📍` **Marcador:** Adiciona um pino em um ponto de interesse.
        * `╱` **Linha:** Desenhe rotas ou meça distâncias.
        """)
        st.markdown("**3️⃣ Edição**")
        st.markdown("""
        * `📝` **Editar:** Permite ajustar ou mover os desenhos existentes.
        * `🗑️` **Lixeira:** Remove todos os desenhos ou o item selecionado.
        """)

# --- FUNÇÃO PADRONIZADA DE EXPORTAÇÃO (CSV + XLSX) ---
def render_download_buttons(df, filename_prefix, key_suffix):
    if df is None or df.empty: return
    try: df_export = df.astype(str)
    except: df_export = df
    csv = df_export.to_csv(index=False).encode('utf-8')
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer: df_export.to_excel(writer, index=False)
    excel_data = buffer.getvalue()
    c1, c2 = st.columns(2)
    c1.download_button("💾 Baixar CSV", csv, f"{filename_prefix}.csv", "text/csv", key=f"btn_csv_{key_suffix}", use_container_width=True)
    c2.download_button("📊 Baixar Excel", excel_data, f"{filename_prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"btn_xlsx_{key_suffix}", use_container_width=True)

def get_geo_caching_key(session_state):
    loc_type = session_state.get('tipo_localizacao')
    if session_state.get('nav_option') == 'Shapefile':
        uploaded = session_state.get('shapefile_upload')
        return f"shp:{uploaded.name if uploaded else 'none'}"
    key = f"loc_type:{loc_type}"
    if loc_type == "Estado": key += f"|estado:{session_state.get('estado')}"
    elif loc_type == "Município": key += f"|estado:{session_state.get('estado')}|municipio:{session_state.get('municipio')}"
    elif loc_type == "Círculo (Lat/Lon/Raio)": key += f"|lat:{session_state.get('latitude')}|lon:{session_state.get('longitude')}|raio:{session_state.get('raio')}"
    elif loc_type == "Polígono": key += f"|geojson:{hash(str(session_state.get('drawn_geometry')))}"
    return key

# --- LÓGICA DE ANÁLISE ---
def run_analysis_logic(variavel, start_date, end_date, geo_caching_key, aba):
    geometry, feature = gee_handler.get_area_of_interest_geometry(st.session_state)
    if not geometry: return None 
    var_cfg = gee_handler.ERA5_VARS.get(variavel)
    if not var_cfg: return None
    results = {"geometry": geometry, "feature": feature, "var_cfg": var_cfg}

    # 1. Mapas e Shapefile
    if aba in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile"]:
        target_hour = None
        if st.session_state.get('tipo_periodo') == "Horário Específico":
            target_hour = st.session_state.get('hora_especifica')
        
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry, target_hour)
        
        if ee_image:
            results["ee_image"] = ee_image
            # Gera dados para a tabela
            if aba in ["Mapas", "Shapefile"]:
                df_map_samples = gee_handler.get_sampled_data_as_dataframe(ee_image, geometry, variavel)
                if df_map_samples is not None: results["map_dataframe"] = df_map_samples
            
    # 2. Séries Temporais
    elif aba in ["Séries Temporais", "Múltiplas Séries"]:
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is not None: results["time_series_df"] = df

    return results

# --- 1. SKEW-T (COM TRATAMENTO DE ERRO 429) ---
    if aba == "Skew-T":
        lat, lon = st.session_state.get("skew_lat"), st.session_state.get("skew_lon")
        date, hour = st.session_state.get("skew_date"), st.session_state.get("skew_hour")
        
        try:
            with st.spinner("Gerando Skew-T (ERA5/GFS)..."):
                # Tenta baixar os dados
                df = skewt_handler.get_vertical_profile_data(lat, lon, date, hour)
                
                # Se der certo, salva no session_state
                st.session_state.skewt_results = {"df": df, "params": (lat, lon, date, hour)}
                
        except Exception as e:
            # --- SE DER ERRO, MOSTRA O AVISO AMIGÁVEL AQUI ---
            st.session_state.skewt_results = None # Limpa resultados antigos
            
            st.warning("⚠️ **Não foi possível obter os dados neste momento.**")
            
            with st.expander("ℹ️ Entenda o motivo (Erro 429 / Conexão)", expanded=True):
                st.info(
                    "**O que aconteceu?**\n\n"
                    "O serviço de dados (Open-Meteo) provavelmente bloqueou a conexão temporariamente "
                    "por excesso de pedidos (Erro 429) ou instabilidade momentânea.\n\n"
                    "👉 **Solução:** Aguarde cerca de **1 minuto** e tente clicar em 'Gerar Análise' novamente."
                )
            
            # Mostra o erro técnico pequeno abaixo, caso seja outra coisa
            st.error(f"Detalhe técnico do erro: {e}")
            
        return
    
    if aba == "Sobreposição (Camadas)":
        v1, v2 = st.session_state.get("var_camada_1"), st.session_state.get("var_camada_2")
        tipo_per = st.session_state.tipo_periodo
        if tipo_per == "Horário Específico":
            d = st.session_state.get('data_horaria')
            start_date, end_date = d, d + timedelta(days=1) if d else None
        else: start_date, end_date = utils.get_date_range(tipo_per, st.session_state)
        if not (start_date and end_date): return
        geo_key = get_geo_caching_key(st.session_state)
        with st.spinner("Gerando camadas..."):
            res1 = run_analysis_logic(v1, start_date, end_date, geo_key, aba)
            res2 = run_analysis_logic(v2, start_date, end_date, geo_key, aba)
            if res1 and res2: st.session_state.analysis_results = {"mode": "overlay", "layer1": {"res": res1, "name": v1}, "layer2": {"res": res2, "name": v2}}
        return

    if aba in ["Múltiplos Mapas", "Múltiplas Séries"]:
        vars_sel = st.session_state.get("variaveis_multiplas", [])
        if not vars_sel: return
        tipo_per = st.session_state.tipo_periodo
        if tipo_per == "Horário Específico":
            d = st.session_state.get('data_horaria')
            start_date, end_date = d, d + timedelta(days=1) if d else None
        else: start_date, end_date = utils.get_date_range(tipo_per, st.session_state)
        if not (start_date and end_date): return
        geo_key = get_geo_caching_key(st.session_state)
        results_multi = {}
        with st.spinner("Gerando dados..."):
            for var in vars_sel:
                res = run_analysis_logic(var, start_date, end_date, geo_key, aba)
                if res: results_multi[var] = res
        st.session_state.analysis_results = {"mode": "multi_series" if aba == "Múltiplas Séries" else "multi_map", "data": results_multi}
        return

    # Lógica Padrão (Mapas, Shapefile, Séries)
    variavel = st.session_state.get("variavel", "Temperatura do Ar (2m)")
    tipo_per = st.session_state.tipo_periodo
    if tipo_per == "Horário Específico":
        d = st.session_state.get('data_horaria')
        start_date, end_date = d, d + timedelta(days=1) if d else None
    else: start_date, end_date = utils.get_date_range(tipo_per, st.session_state)
    if not (start_date and end_date): st.warning("Selecione um período válido."); return
    geo_key = get_geo_caching_key(st.session_state)
    try:
        with st.spinner("Processando dados..."):
            analysis_data = run_analysis_logic(variavel, start_date, end_date, geo_key, aba)
        st.session_state.analysis_results = analysis_data if analysis_data else None
    except Exception as e: st.error(f"Erro: {e}"); st.session_state.analysis_results = None

def render_analysis_results():
    aba = st.session_state.get("nav_option", "Mapas")

    # 1. SKEW-T
    if aba == "Skew-T":
        if "skewt_results" in st.session_state:

            # --- AVISO RESTAURADO (COMPLETO) ---
            with st.expander("ℹ️ Sobre limites de conexão (Erro 429)", expanded=False):
                st.info(
                    "**O que significa 'Erro 429 - Too Many Requests'?**\n\n"
                    "O Open-Meteo é um serviço gratuito de alta qualidade. Para evitar sobrecarga, "
                    "eles bloqueiam temporariamente o acesso se receberem muitos pedidos em poucos segundos.\n\n"
                    "👉 **Dica:** Se isso acontecer, aguarde cerca de **1 minuto** e tente novamente. "
                    "Evite clicar em 'Gerar' várias vezes seguidas rapidamente."
                )
            # -----------------------------------            
            
            ui.renderizar_resumo_selecao()
            res = st.session_state.skewt_results
            if res["df"] is not None:
                skewt_visualizer.render_skewt_plot(res["df"], *res["params"])
                with st.expander("📥 Exportar Dados"):
                    render_download_buttons(pd.DataFrame(res["df"]).astype(str), "skewt", "sk")
        return

    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None: return
    results = st.session_state.analysis_results

    tipo_periodo = st.session_state.get('tipo_periodo', '')
    periodo_str = ""
    if tipo_periodo == "Personalizado": periodo_str = f"de {st.session_state.get('data_inicio').strftime('%d/%m/%Y')} a {st.session_state.get('data_fim').strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mensal": periodo_str = f"mensal ({st.session_state.get('mes_mensal')}/{st.session_state.get('ano_mensal')})"
    elif tipo_periodo == "Anual": periodo_str = f"anual ({st.session_state.get('ano_anual')})"
    elif tipo_periodo == "Horário Específico": periodo_str = f"em {st.session_state.get('data_horaria').strftime('%d/%m/%Y')} às {st.session_state.get('hora_especifica')}:00"

    local_str = "Local Selecionado"
    if aba == "Shapefile": 
        local_str = "na Área Personalizada (Shapefile)"
        with st.expander("❓ Não tem um Shapefile? Aprenda a criar um em 1 minuto 👇"):
            st.markdown("1. Vá em **[geojson.io](https://geojson.io/)**.\n2. Desenhe sua área (Polígono).\n3. Menu: **Save > Shapefile**.\n4. Envie o ZIP aqui.")
    
    # 2. SOBREPOSIÇÃO
    if aba == "Sobreposição (Camadas)" and results.get("mode") == "overlay":
        st.subheader("Mapa de Sobreposição")
        ui.renderizar_resumo_selecao()
        mode = st.session_state.get('overlay_mode', "Transparência")
        map_visualizer.create_overlay_map(results["layer1"]["res"]["ee_image"], results["layer1"]["name"], results["layer2"]["res"]["ee_image"], results["layer2"]["name"], results["layer1"]["res"]["feature"], opacity1=st.session_state.get('opacity_1', 1.0), opacity2=st.session_state.get('opacity_2', 0.6), mode=mode)
        
        # --- RESTAURADO O AVISO ESTILIZADO AQUI ---
        if mode == "Split Map (Cortina)":
            st.markdown(
                "<div style='text-align: center; margin-top: 10px; color: #555; background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ccc;'>"
                "↔️ <b>Dica:</b> Clique e arraste a <b>barra vertical central</b> para alternar entre as camadas."
                "</div>", 
                unsafe_allow_html=True
            )
        # ------------------------------------------
        return

    # 3. MÚLTIPLOS MAPAS
    if aba == "Múltiplos Mapas" and results.get("mode") == "multi_map":
        st.subheader("Comparação de Variáveis")
        ui.renderizar_resumo_selecao()
        if "Estático" in st.radio("Formato", ["Estático", "Interativo"], horizontal=True):
            cols = st.columns(2)
            for i, var in enumerate(results["data"]):
                with cols[i % 2]:
                    st.markdown(f"**{var}**")
                    png, jpg, cbar = map_visualizer.create_static_map(results["data"][var]["ee_image"], results["data"][var]["feature"], gee_handler.obter_vis_params_interativo(var), results["data"][var]["var_cfg"]["unit"])
                    if png:
                        st.image(base64.b64decode(png.split(",")[1]), use_column_width=True) 
                        if cbar: st.image(base64.b64decode(cbar.split(",")[1]), use_column_width=True)
                        st.markdown("📥 **Baixar:**")
                        c1, c2 = st.columns(2)
                        c1.download_button("PNG", base64.b64decode(png.split(",")[1]), f"{var}.png", "image/png", key=f"png_{i}")
                        c2.download_button("JPG", base64.b64decode(jpg.split(",")[1]), f"{var}.jpg", "image/jpeg", key=f"jpg_{i}")
        else:
            cols = st.columns(2)
            for i, var in enumerate(results["data"]):
                with cols[i % 2]:
                    st.markdown(f"**{var}**")
                    map_visualizer.create_interactive_map(results["data"][var]["ee_image"], results["data"][var]["feature"], gee_handler.obter_vis_params_interativo(var), results["data"][var]["var_cfg"]["unit"])
        return

    # 4. MÚLTIPLAS SÉRIES
    if aba == "Múltiplas Séries" and results.get("mode") == "multi_series":
        st.subheader("Comparação de Séries")
        ui.renderizar_resumo_selecao()
        if st.toggle("📉 Gráfico Único", value=False): charts_visualizer.display_multiaxis_chart(results["data"])
        else:
            cols = st.columns(2)
            for i, var in enumerate(results["data"]):
                with cols[i % 2]:
                    st.markdown(f"**{var}**")
                    charts_visualizer.display_time_series_chart(results["data"][var]["time_series_df"], var, results["data"][var]["var_cfg"]["unit"], show_help=False)
        return

    # 5. MAPAS E SHAPEFILE (CORRIGIDO E COMPLETO)
    var_cfg = results["var_cfg"]
    st.subheader(f"Análise: {st.session_state.get('variavel')} {local_str}")
    ui.renderizar_resumo_selecao() 

    if aba in ["Mapas", "Shapefile"]:
        if "ee_image" in results:
            vis = gee_handler.obter_vis_params_interativo(st.session_state.variavel)
            tipo_mapa = st.session_state.get("map_type", "Interativo")
            
            # --- MODO INTERATIVO ---
            if tipo_mapa == "Interativo":
                render_map_tips()
                opa = 1.0 
                if aba == "Shapefile":
                    st.markdown("#### 🎚️ Ajuste de Transparência")
                    opa = st.slider("Opacidade", 0.0, 1.0, 0.7, 0.1, key='shp_opacity')
                map_visualizer.create_interactive_map(results["ee_image"], results["feature"], vis, var_cfg["unit"], opacity=opa)

            # --- MODO ESTÁTICO ---
            else:
                with st.spinner("Gerando imagem..."):
                    png, jpg, cbar = map_visualizer.create_static_map(results["ee_image"], results["feature"], vis, var_cfg["unit"])
                
                if png:
                    st.image(base64.b64decode(png.split(",")[1]), use_column_width=True) 
                    if cbar: st.image(base64.b64decode(cbar.split(",")[1]), use_column_width=True)
                    
                    # TENTA GERAR COM TÍTULO, SE FALHAR USA O SIMPLES
                    try:
                        t = f"{st.session_state.variavel} {periodo_str} {local_str}"
                        tb = map_visualizer._make_title_image(t, 800)
                        mp, jp = base64.b64decode(png.split(",")[1]), base64.b64decode(jpg.split(",")[1])
                        cb = base64.b64decode(cbar.split(",")[1]) if cbar else None
                        final_png = map_visualizer._stitch_images_to_bytes(tb, mp, cb, 'PNG') or mp
                        final_jpg = map_visualizer._stitch_images_to_bytes(tb, jp, cb, 'JPEG') or jp
                    except:
                        final_png, final_jpg = base64.b64decode(png.split(",")[1]), base64.b64decode(jpg.split(",")[1])

                    # 1) BOTÕES DE DOWNLOAD DA IMAGEM
                    st.markdown("##### 📥 Baixar Mapa (Imagem)")
                    c1, c2 = st.columns(2)
                    c1.download_button("💾 Baixar PNG", final_png, "mapa.png", "image/png", use_container_width=True)
                    c2.download_button("💾 Baixar JPG", final_jpg, "mapa.jpeg", "image/jpeg", use_container_width=True)

            # --- DADOS E TABELA (SEMPRE VISÍVEIS SE HOUVER DADOS) ---
            if "map_dataframe" in results and not results["map_dataframe"].empty:
                st.markdown("---")
                # 2) Ver Tabela
                with st.expander("📊 Ver Tabela de Dados", expanded=False):
                    st.dataframe(results["map_dataframe"], use_container_width=True, hide_index=True, height=250)
                    
                    # 3) Baixar .csv e .xlsx
                    st.markdown("##### 📥 Baixar Dados da Tabela")
                    render_download_buttons(results["map_dataframe"], "dados_climaticos", "map_export")

    # 6. SÉRIES TEMPORAIS
    elif aba == "Séries Temporais":
        if "time_series_df" in results:
            render_chart_tips()
            charts_visualizer.display_time_series_chart(results["time_series_df"], st.session_state.variavel, var_cfg["unit"], show_help=False)

def render_polygon_drawer():
    st.subheader("Desenhe sua Área de Interesse")
    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google")
    Draw(export=False, draw_options={"polygon": True, "rectangle": True, "circle": False, "marker": False, "polyline": False}).add_to(m)
    map_data = st_folium(m, width=None, height=500, returned_objects=["all_drawings"])
    if map_data and map_data.get("all_drawings"):
        st.session_state.drawn_geometry = map_data["all_drawings"][-1]["geometry"]
        st.rerun()

def main():
    if 'gee_initialized' not in st.session_state:
        gee_handler.inicializar_gee()
        st.session_state.gee_initialized = True
    
    dados_geo, mapa_nomes_uf = gee_handler.get_brazilian_geopolitical_data_local()
    opcao_menu = ui.renderizar_sidebar(dados_geo, mapa_nomes_uf)
    
    if opcao_menu == "Sobre o Aplicativo": ui.renderizar_pagina_sobre(); return
    ui.renderizar_pagina_principal(opcao_menu)
    
    is_poly = (opcao_menu in ["Mapas", "Múltiplos Mapas", "Séries Temporais", "Múltiplas Séries", "Sobreposição (Camadas)"] and st.session_state.get('tipo_localizacao') == "Polígono")
    if is_poly and not st.session_state.get("analysis_triggered") and 'drawn_geometry' not in st.session_state: render_polygon_drawer()
    
    if st.session_state.get("analysis_triggered"):
        st.session_state.analysis_triggered = False
        run_full_analysis()
    
    render_analysis_results()

if __name__ == "__main__":
    main()



