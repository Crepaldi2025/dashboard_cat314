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

# --- FUNÇÃO DE AJUDA DOS GRÁFICOS ---
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

# --- FUNÇÃO DE AJUDA DO MAPA ---
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
    if df is None or df.empty:
        return

    try:
        df_export = df.astype(str)
    except:
        df_export = df

    csv = df_export.to_csv(index=False).encode('utf-8')
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False)
    excel_data = buffer.getvalue()
    
    c1, c2 = st.columns(2)
    c1.download_button(
        label="💾 Baixar CSV",
        data=csv,
        file_name=f"{filename_prefix}.csv",
        mime="text/csv",
        key=f"btn_csv_{key_suffix}",
        use_container_width=True
    )
    c2.download_button(
        label="📊 Baixar Excel",
        data=excel_data,
        file_name=f"{filename_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_xlsx_{key_suffix}",
        use_container_width=True
    )

def get_geo_caching_key(session_state):
    loc_type = session_state.get('tipo_localizacao')
    if session_state.get('nav_option') == 'Shapefile':
        uploaded = session_state.get('hidro_upload')
        return f"hidro:{uploaded.name if uploaded else 'none'}"
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

    if aba in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile"]:
        target_hour = None
        if st.session_state.get('tipo_periodo') == "Horário Específico":
            target_hour = st.session_state.get('hora_especifica')
        ee_image = gee_handler.get_era5_image(variavel, start_date, end_date, geometry, target_hour)
        if ee_image:
            results["ee_image"] = ee_image
            if aba in ["Mapas", "Shapefile"]:
                df_map_samples = gee_handler.get_sampled_data_as_dataframe(ee_image, geometry, variavel)
                if df_map_samples is not None: results["map_dataframe"] = df_map_samples
            
    elif aba in ["Séries Temporais", "Múltiplas Séries"]:
        df = gee_handler.get_time_series_data(variavel, start_date, end_date, geometry)
        if df is not None: results["time_series_df"] = df

    return results

def run_full_analysis():
    aba = st.session_state.get("nav_option", "Mapas")
    
    if aba == "Skew-T":
        lat = st.session_state.get("skew_lat")
        lon = st.session_state.get("skew_lon")
        date = st.session_state.get("skew_date")
        hour = st.session_state.get("skew_hour")
        with st.spinner("Gerando Skew-T (ERA5/GFS)..."):
            df = skewt_handler.get_vertical_profile_data(lat, lon, date, hour)
            st.session_state.skewt_results = {"df": df, "params": (lat, lon, date, hour)}
        return
    
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

            # --- ADICIONE ESTE AVISO AQUI ---
            with st.expander("ℹ️ Sobre limites de conexão (Erro 429)", expanded=False):
                st.info(
                    "**O que significa 'Erro 429 - Too Many Requests'?**\n\n"
                    "O Open-Meteo é um serviço gratuito de alta qualidade. Para evitar sobrecarga, "
                    "eles bloqueiam temporariamente o acesso se receberem muitos pedidos em poucos segundos.\n\n"
                    "👉 **Dica:** Se isso acontecer, aguarde cerca de **1 minuto** e tente novamente. "
                    "Evite clicar em 'Gerar' várias vezes seguidas rapidamente."
                )
            # --------------------------------
            
            ui.renderizar_resumo_selecao()
            st.markdown("""<style>div[data-testid="stMetricValue"] {font-size: 1.1rem !important;}</style>""", unsafe_allow_html=True)
            res = st.session_state.skewt_results
            if res["df"] is not None:
                skewt_visualizer.render_skewt_plot(res["df"], *res["params"])
                
                with st.expander("📥 Exportar Dados da Sondagem"):
                    try:
                        # 1. Copia o dataframe
                        df_formatted = pd.DataFrame(res["df"]).copy()
                        
                        # 2. Reseta o índice se for data (para não perder informação na conversão)
                        if isinstance(df_formatted.index, pd.DatetimeIndex):
                            df_formatted.reset_index(inplace=True)

                        # 3. Limpa unidades físicas (MetPy) e converte para número
                        for col in df_formatted.columns:
                            # Tenta extrair .magnitude (MetPy) ou mantem o valor
                            df_formatted[col] = df_formatted[col].apply(lambda x: getattr(x, 'magnitude', x))
                            # Tenta converter para numérico para podermos formatar
                            df_formatted[col] = pd.to_numeric(df_formatted[col], errors='ignore')

                        # 4. Formata colunas numéricas (float) para 1 casa decimal
                        for col in df_formatted.select_dtypes(include=['float']).columns:
                            df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.1f}")
                        # Ajuste os nomes abaixo conforme as colunas reais 
                        colunas_unidades = {
                            "pressure": "Pressão (hPa)",
                            "temperature": "Temperatura (°C)",
                            "relative_humidity": "UR (%)",
                            "u_component": "Vento U (m/s)",
                            "v_component": "Vento V (m/s)",
                        }
                        df_formatted = df_formatted.rename(columns=colunas_unidades)
                        # 5. Converte TUDO para string final (resolve o erro JSON definitivamente)
                        df_final = df_formatted.astype(str)

                        st.dataframe(df_final, use_container_width=True)
                        render_download_buttons(df_final, "sondagem_skewt", "skewt")
                        
                    except Exception as e:
                        # Fallback de segurança: apenas converte para string sem formatação bonita
                        st.dataframe(res["df"].astype(str), use_container_width=True)
                        render_download_buttons(res["df"].astype(str), "sondagem_skewt", "skewt")
        return

    if "analysis_results" not in st.session_state or st.session_state.analysis_results is None:
        return

    results = st.session_state.analysis_results

    tipo_periodo = st.session_state.get('tipo_periodo', '')
    periodo_str = ""
    if tipo_periodo == "Personalizado": periodo_str = f"de {st.session_state.get('data_inicio').strftime('%d/%m/%Y')} a {st.session_state.get('data_fim').strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mensal": periodo_str = f"mensal ({st.session_state.get('mes_mensal')}/{st.session_state.get('ano_mensal')})"
    elif tipo_periodo == "Anual": periodo_str = f"anual ({st.session_state.get('ano_anual')})"
    elif tipo_periodo == "Horário Específico": periodo_str = f"em {st.session_state.get('data_horaria').strftime('%d/%m/%Y')} às {st.session_state.get('hora_especifica')}:00"
    
    local_str = "Local Selecionado"
    if aba == "Shapefile": local_str = "na Área Personalizada (Shapefile)"
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

    if aba == "Sobreposição (Camadas)" and results.get("mode") == "overlay":
        st.subheader("Mapa de Sobreposição (Overlay)")
        ui.renderizar_resumo_selecao()
        with st.popover("ℹ️ Como controlar a visualização?"): 
            st.markdown("""
            **Use o ícone 🗂️ (Camadas) no canto superior direito para:**
            1. **Ligar/Desligar** as camadas de dados (Base/Topo).
            2. **Exibir ou Ocultar** o Contorno da área (linha vermelha).
            3. **Visualizar** a imagem de satélite ao fundo.
            """)
        mode = st.session_state.get('overlay_mode', "Transparência")
        map_visualizer.create_overlay_map(
            results["layer1"]["res"]["ee_image"], results["layer1"]["name"], 
            results["layer2"]["res"]["ee_image"], results["layer2"]["name"], 
            results["layer1"]["res"]["feature"], 
            opacity1=st.session_state.get('opacity_1', 1.0), 
            opacity2=st.session_state.get('opacity_2', 0.6), 
            mode=mode
        )

        if mode == "Split Map (Cortina)":
            st.markdown(
                "<div style='text-align: center; margin-top: 10px; color: #555; background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ccc;'>"
                "↔️ <b>Dica:</b> Clique e arraste a <b>barra vertical central</b> para alternar entre as camadas."
                "</div>", 
                unsafe_allow_html=True
            )
        
        return

  
    if aba == "Múltiplos Mapas" and results.get("mode") == "multi_map":
        st.subheader("Comparação de Variáveis")
        ui.renderizar_resumo_selecao()
        
        # 1. Escolha do Modo
        st.markdown("#### 🎨 Tipo de Visualização")
        modo_multiplo = st.radio(
            "Formato dos Mapas", 
            ["Estático (Imagens para Download)", "Interativo (Navegável)"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        st.markdown("---")

        cols = st.columns(2)

        # 2. Lógica Condicional
        if "Estático" in modo_multiplo:
            # Importações de segurança
            import base64
            
            # --- MODO ANTIGO (Imagens) ---
            for i, var_name in enumerate(results["data"]):
                res = results["data"][var_name]
                with cols[i % 2]:
                    st.markdown(f"**{var_name}**")
                    png, jpg, cbar = map_visualizer.create_static_map(res["ee_image"], res["feature"], gee_handler.obter_vis_params_interativo(var_name), res["var_cfg"]["unit"])
                    
                    if png:
                        # CORREÇÃO AQUI:
                        # 1. Decodificamos o base64 para bytes (mais seguro para o st.image)
                        # 2. Usamos 'use_column_width=True' (funciona em todas as versões do Streamlit)
                        st.image(base64.b64decode(png.split(",")[1]), use_column_width=True) 
                        
                        if cbar: 
                            st.image(base64.b64decode(cbar.split(",")[1]), use_column_width=True)

                        try:
                            # Botões de download (mantidos)
                            title = f"{var_name} {periodo_str} {local_str}"
                            tb = map_visualizer._make_title_image(title, 800)
                            mp = base64.b64decode(png.split(",")[1])
                            jp = base64.b64decode(jpg.split(",")[1])
                            cb = base64.b64decode(cbar.split(",")[1]) if cbar else None
                            fp = map_visualizer._stitch_images_to_bytes(tb, mp, cb, 'PNG')
                            fj = map_visualizer._stitch_images_to_bytes(tb, jp, cb, 'JPEG')
                            sub_c1, sub_c2 = st.columns(2)
                            var_slug = var_name.lower().replace(" ", "_")
                            if fp: sub_c1.download_button("💾 Baixar PNG", fp, f"{var_slug}.png", "image/png", use_container_width=True, key=f"btn_png_{i}")
                            if fj: sub_c2.download_button("💾 Baixar JPG", fj, f"{var_slug}.jpg", "image/jpeg", use_container_width=True, key=f"btn_jpg_{i}")
                        except: pass
        
        else:
            # --- NOVO MODO (Interativo) ---
            # Reutiliza a função create_interactive_map que já existe!
            
            # Dica flutuante apenas uma vez
            render_map_tips()
            
            for i, var_name in enumerate(results["data"]):
                res = results["data"][var_name]
                with cols[i % 2]:
                    st.markdown(f"##### {var_name}")
                    
                    # Chama o mapa interativo para cada variável
                    map_visualizer.create_interactive_map(
                        res["ee_image"], 
                        res["feature"], 
                        gee_handler.obter_vis_params_interativo(var_name), 
                        res["var_cfg"]["unit"]
                    )
        return
        
    if aba == "Múltiplas Séries" and results.get("mode") == "multi_series":
        st.subheader("Comparação de Séries")
        ui.renderizar_resumo_selecao()
        
        # Ajuda no topo para fácil acesso
        render_chart_tips()
        
        
        # Toggle para alternar visualização
        usar_grafico_unico = st.toggle("📉 Visualizar em Gráfico Único (Eixos Mistos)", value=False)
        
        if usar_grafico_unico:
            # OPÇÃO A: Apenas o gráfico unificado
            charts_visualizer.display_multiaxis_chart(results["data"])
        else:
            # OPÇÃO B: Apenas os gráficos separados (lado a lado)
            cols = st.columns(2)
            for i, var_name in enumerate(results["data"]):
                res = results["data"][var_name]
                with cols[i % 2]:
                    st.markdown(f"##### {var_name}")
                    charts_visualizer.display_time_series_chart(
                        res["time_series_df"], 
                        var_name, 
                        res["var_cfg"]["unit"], 
                        show_help=False
                    )
        return
    var_cfg = results["var_cfg"]
    st.subheader(f"Análise: {st.session_state.get('variavel')} {local_str}")
    ui.renderizar_resumo_selecao() 

    # ... (dentro de render_analysis_results) ...

    if aba in ["Mapas", "Shapefile"]:
        if "ee_image" in results:
            vis_params = gee_handler.obter_vis_params_interativo(st.session_state.variavel)
            tipo_mapa = st.session_state.get("map_type", "Interativo")
            
            # --- MODO INTERATIVO ---
            if tipo_mapa == "Interativo":
                render_map_tips()
                
                # 1. Define opacidade padrão
                opacity_val = 1.0 
                
                # 2. Se for Shapefile, mostra o slider
                if aba == "Shapefile":
                    st.markdown("#### 🎚️ Ajuste de Transparência")
                    opacity_val = st.slider(
                        "Opacidade da Camada", 
                        min_value=0.0, 
                        max_value=1.0, 
                        value=0.7, 
                        step=0.1, 
                        key='shp_opacity'
                    )

                # 3. CHAMADA ÚNICA DO MAPA (Sem duplicatas!)
                map_visualizer.create_interactive_map(
                    results["ee_image"], 
                    results["feature"], 
                    vis_params, 
                    var_cfg["unit"],
                    opacity=opacity_val 
                )

            # --- MODO ESTÁTICO ---
            else:
                with st.spinner("Gerando imagem..."):
                    png, jpg, cbar = map_visualizer.create_static_map(results["ee_image"], results["feature"], vis_params, var_cfg["unit"])
                
                # Importação de segurança
                import base64
                
                if png:
                    # Exibe imagens (Decodificando base64 para evitar erros)
                    st.image(base64.b64decode(png.split(",")[1]), width=600) 
                    if cbar: st.image(base64.b64decode(cbar.split(",")[1]), width=600)
                    
                    try:
                        title = f"{st.session_state.variavel} {periodo_str} {local_str}"
                        tb = map_visualizer._make_title_image(title, 800)
                        mp = base64.b64decode(png.split(",")[1])
                        jp = base64.b64decode(jpg.split(",")[1])
                        cb = base64.b64decode(cbar.split(",")[1]) if cbar else None
                        
                        fp = map_visualizer._stitch_images_to_bytes(tb, mp, cb, 'PNG')
                        fj = map_visualizer._stitch_images_to_bytes(tb, jp, cb, 'JPEG')
                        
                        c1, c2 = st.columns(2)
                        if fp: c1.download_button("💾 Baixar PNG", fp, "mapa.png", "image/png", use_container_width=True)
                        if fj: c2.download_button("💾 Baixar JPG", fj, "mapa.jpeg", "image/jpeg", use_container_width=True)
                    except: pass
    elif aba == "Séries Temporais":
        if "time_series_df" in results:
            render_chart_tips()
            charts_visualizer.display_time_series_chart(results["time_series_df"], st.session_state.variavel, var_cfg["unit"], show_help=False)

def render_polygon_drawer():
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
    
    is_polygon = (
        opcao_menu in ["Mapas", "Múltiplos Mapas", "Séries Temporais", "Múltiplas Séries", "Sobreposição (Camadas)"] and 
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

if __name__ == "__main__":
    main()





















