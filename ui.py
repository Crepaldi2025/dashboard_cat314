# ==================================================================================
# ui.py
# ==================================================================================

import streamlit as st
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import locale
import docx
import os
import requests
import pypandoc
import tempfile
import pytz
import re

# ------------------------------
# Configuração da Página e Cache
# ------------------------------

st.set_page_config(
    page_title="Clima-Cast-Crepaldi",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌦️"
)

try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    pass 

NOMES_MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

@st.cache_data
def _carregar_texto_docx(file_path):
    if not os.path.exists(file_path): return None 
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n\n".join(full_text)
    except Exception: return None

# -----------------------
# Apagar dados da memória
# -----------------------

def reset_analysis_state():
    for key in ['analysis_triggered', 'analysis_results', 'drawn_geometry', 'skewt_results']:
        if key in st.session_state: del st.session_state[key]

def reset_analysis_results_only():
    for key in ['analysis_triggered', 'analysis_results']:
        if key in st.session_state: del st.session_state[key]

# --------------------------
# Renderizar a barra lateral
# --------------------------

def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    with st.sidebar:
        # --- 1. TÍTULO ---
        st.markdown("<h2 style='text-align: center;'>🌦️ Clima-Cast-Crepaldi</h2>", unsafe_allow_html=True)
        st.markdown("---")

        # --- 2. NAVEGAÇÃO PRINCIPAL ---
        st.radio(
            "Modo de Visualização",
            ["Mapas", "Séries Temporais", "Skew-T", "Sobre o Aplicativo"],
            label_visibility="collapsed", 
            key='nav_option',
            on_change=reset_analysis_state
        )
        
        opcao = st.session_state.get('nav_option', 'Mapas')

        # --- OPÇÃO SKEW-T (COM NOTA ATUALIZADA) ---
        if opcao == "Skew-T":
            st.markdown("### 🌪️ Diagrama Skew-T")
            st.info("Gera um perfil vertical da atmosfera (Sondagem).")
            
            st.divider()
            st.markdown("#### 📍 Localização Pontual")
            
            c1, c2 = st.columns(2)
            with c1: st.number_input("Lat", value=-23.55, format="%.4f", key='skew_lat', on_change=reset_analysis_state)
            with c2: st.number_input("Lon", value=-46.63, format="%.4f", key='skew_lon', on_change=reset_analysis_state)
            
            st.divider()
            st.markdown("#### 📅 Momento")
            
            hoje = datetime.now()
            data_padrao = hoje - relativedelta(days=0) 
            
            st.date_input("Data", value=data_padrao, max_value=hoje, key='skew_date', format="DD/MM/YYYY", on_change=reset_analysis_state)
            st.slider("Hora (UTC)", 0, 23, 12, key='skew_hour', help="Hora em UTC (3 horas à frente de Brasília).", on_change=reset_analysis_state)

            # --- NOTA EXPLICATIVA SOBRE O LIMITE DE DATA ---
            st.caption("ℹ️ **Nota:** Dados de altitude (pressão) disponíveis apenas a partir de **23/03/2021** (limite histórico do modelo GFS). Para datas anteriores, apenas dados de superfície estão disponíveis.")

            st.divider()
            st.button(
                "🚀 Gerar Skew-T", 
                type="primary", 
                use_container_width=True, 
                on_click=lambda: st.session_state.update(analysis_triggered=True)
            )

        # --- OPÇÕES MAPAS E SÉRIES (MANTIDAS INTACTAS) ---
        elif opcao in ["Mapas", "Séries Temporais"]:
            st.markdown("### ⚙️ Parâmetros da Análise")
            
            # --- 3. BASE DE DADOS ---
            st.markdown("#### 🛰️ Base de Dados", help="Reanálise climática global de alta resolução (ECMWF).")
            st.selectbox(
                "Selecione a Base de Dados", 
                ["ERA5-LAND"], 
                key='base_de_dados', 
                on_change=reset_analysis_state,
                label_visibility="collapsed"
            )

            st.divider()

            # --- 4. VARIÁVEL ---
            st.markdown("#### 🌡️ Variável Meteorológica")
            st.selectbox(
                "Selecione a Variável", 
                [
                    "Temperatura do Ar (2m)", 
                    "Temperatura do Ponto de Orvalho (2m)",
                    "Temperatura da Superfície (Skin)",
                    "Precipitação Total", 
                    "Umidade Relativa (2m)", 
                    "Umidade do Solo (0-7 cm)",
                    "Umidade do Solo (7-28 cm)",
                    "Umidade do Solo (28-100 cm)",
                    "Umidade do Solo (100-289 cm)",
                    "Velocidade do Vento (10m)", 
                    "Radiação Solar Incidente"
                ], 
                key='variavel', 
                on_change=reset_analysis_state,
                label_visibility="collapsed"
            )
            
            st.divider()

            # --- 5. LOCALIZAÇÃO ---
            st.markdown("#### 📍 Localização")
            st.selectbox(
                "Tipo de Recorte", 
                ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"], 
                key='tipo_localizacao', 
                on_change=reset_analysis_state
            ) 
            
            tipo_loc = st.session_state.get('tipo_localizacao', 'Estado')
            lista_ufs = ["Selecione..."] + [f"{mapa_nomes_uf[uf]} - {uf}" for uf in sorted(mapa_nomes_uf)]

            if tipo_loc == "Estado":
                if len(lista_ufs) <= 1: st.error("⚠️ Lista de estados vazia (Fallback ativo).")
                st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
            
            elif tipo_loc == "Município":
                st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
                estado_str = st.session_state.get('estado', 'Selecione...')
                lista_muns = ["Selecione um estado primeiro"]
                if estado_str != "Selecione...":
                     uf_sigla = estado_str.split(' - ')[-1]
                     muns = dados_geo.get(uf_sigla, [])
                     if muns: lista_muns = ["Selecione..."] + muns
                st.selectbox("Município", lista_muns, key='municipio', on_change=reset_analysis_state)
            
            elif tipo_loc == "Círculo (Lat/Lon/Raio)":
                c1, c2 = st.columns(2)
                with c1: st.number_input("Lat", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                with c2: st.number_input("Lon", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
                with st.popover("ℹ️ Ajuda: Definindo o Círculo"):
                    st.markdown("**Como preencher:**\n* **Lat/Lon:** Graus decimais (ex: -22.42).\n* **Raio:** Km do centro à borda.")
            
            elif tipo_loc == "Polígono":
                if st.session_state.get('drawn_geometry'): st.success("✅ Polígono Definido", icon="🛡️")
                else: 
                    #st.markdown("<div style='background-color:#e0f7fa;padding:10px;border-radius:5px;border-left:5px solid #00acc1;font-size:0.85em;'><b style='color:#006064;'>👉 Desenhe no Mapa Principal</b><br>Utilize as ferramentas na lateral esquerda do mapa.</div>", unsafe_allow_html=True)
                    st.markdown("<div style='background-color:#e0f7fa;padding:10px;border-radius:5px;border-left:5px solid #00acc1;font-size:0.85em;'><b style='color:#006064;'>👉 Desenhe no Mapa Principal</b><br>Utilize as ferramentas na lateral esquerda do mapa.<br><br><b>Atenção:</b> se o recorte temporal for redefinido é necessário redesenhar o polígono.</div>", unsafe_allow_html=True)
                with st.popover("ℹ️ Guia de Ferramentas"): st.markdown("⬟ Polígono (Livre)\n⬛ Retângulo (Quadrado)\n📝 Editar\n🗑️ Lixeira")
            
            st.divider()

            # --- 6. PERÍODO ---
            st.markdown("#### 📅 Recorte Temporal")
            
            opcoes_periodo = ["Personalizado", "Mensal", "Anual"]
            if opcao == "Mapas": opcoes_periodo.append("Horário Específico")
            
            if opcao == "Mapas":
                st.selectbox("Tipo de Período", opcoes_periodo, key='tipo_periodo', on_change=reset_analysis_state, label_visibility="collapsed")
            else:
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_per = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1949, -1))
            st.session_state.date_error = False
            
            min_data = datetime(1950, 1, 1)
            max_data = datetime.now()
            
            if tipo_per == "Personalizado":
                hoje = datetime.now()
                fim_padrao = hoje.replace(day=1) - relativedelta(days=1)
                inicio_padrao = fim_padrao.replace(day=1)
                c1, c2 = st.columns(2)
                with c1: st.date_input("Início", value=inicio_padrao, min_value=min_data, max_value=max_data, key='data_inicio', on_change=reset_analysis_state, format="DD/MM/YYYY")
                with c2: st.date_input("Fim", value=fim_padrao, min_value=min_data, max_value=max_data, key='data_fim', on_change=reset_analysis_state, format="DD/MM/YYYY")
                if st.session_state.data_fim < st.session_state.data_inicio:
                    st.error("Data final anterior à inicial.")
                    st.session_state.date_error = True
            
            elif tipo_per == "Mensal":
                c1, c2 = st.columns(2)
                with c1: st.selectbox("Ano", lista_anos, key='ano_mensal', on_change=reset_analysis_state)
                with c2: st.selectbox("Mês", NOMES_MESES_PT, key='mes_mensal', on_change=reset_analysis_state)
            
            elif tipo_per == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            
            elif tipo_per == "Horário Específico":
                hoje = datetime.now()
                data_padrao = hoje - relativedelta(months=4)
                
                st.date_input("Data", value=data_padrao, min_value=min_data, max_value=max_data, key='data_horaria', on_change=reset_analysis_state, format="DD/MM/YYYY")
                st.slider("Hora (UTC)", 0, 23, 12, key='hora_especifica', on_change=reset_analysis_state, help="Hora em UTC (3 horas à frente de Brasília).")
                
                st.info("ℹ️ **Nota:** Esta opção retorna um dado pontual (snapshot) apenas para a hora escolhida.", icon="🕒")
            
            st.divider()

            # --- 7. VISUALIZAÇÃO ---
            if opcao == "Mapas":
                st.markdown("#### 🎨 Visualização")
                st.radio("Formato", ["Interativo", "Estático"], key='map_type', horizontal=True, on_change=reset_analysis_results_only, label_visibility="collapsed")
                st.divider()

            # --- 8. BOTÃO DE AÇÃO ---
            disable = st.session_state.get('date_error', False)
            if tipo_loc == "Polígono" and not st.session_state.get('drawn_geometry'): disable = True
            elif tipo_loc == "Círculo (Lat/Lon/Raio)" and not (st.session_state.get('latitude') and st.session_state.get('longitude')): disable = True

            st.button(
                "🚀 Gerar Análise", 
                type="primary", 
                use_container_width=True, 
                disabled=disable,
                on_click=lambda: st.session_state.update(analysis_triggered=True)
            )
            
            if not disable:
                st.markdown(
                    "<div style='font-size:14px;margin-top:8px;'>"
                    "⚠️ <b>Atenção:</b> Confira os filtros antes de gerar.<br>"
                    "Consultas de períodos longos ou áreas muito grandes podem levar mais tempo para carregar."
                    "</div>", 
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<div style='font-size:14px;color:#d32f2f;margin-top:8px;'>⚠️ <b>Obrigatório:</b> Defina a localização.</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("<div style='text-align:center;color:grey;font-size:12px;'>Desenvolvido por <b>Paulo C. Crepaldi</b><br>v1.0.0 | 2025</div>", unsafe_allow_html=True)
        
        return opcao

# -----------------------------
# Renderizar a página principal
# -----------------------------

def renderizar_pagina_principal(opcao):
    st.markdown("""<style>.block-container{padding-top:3rem!important;padding-bottom:5rem!important}h1{margin-top:0rem!important}.stExpander{border:1px solid #f0f2f6;border-radius:8px}</style>""", unsafe_allow_html=True)
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora, agora_utc = datetime.now(fuso_br), datetime.now(pytz.utc)
    c1, c2 = st.columns([3, 1.5])
    with c1:
        lc, tc = st.columns([1, 5])
        with lc: 
            if os.path.exists("logo.png"): st.image("logo.png", width=70)
            else: st.write("🌐")
        with tc: st.title(f"{opcao}")
    with c2:
        st.markdown(f"<div style='border:1px solid #e0e0e0;padding:8px;text-align:center;border-radius:8px;background-color:rgba(255,255,255,0.7);font-size:0.9rem;'><img src='https://flagcdn.com/24x18/br.png' style='vertical-align:middle;margin-bottom:2px;'> <b>BRT:</b> {agora.strftime('%d/%m/%Y %H:%M')}<br><span style='color:#666;font-size:0.8rem;'>🌐 UTC: {agora_utc.strftime('%d/%m/%Y %H:%M')}</span></div>", unsafe_allow_html=True)
    st.markdown("---")
    if "analysis_results" not in st.session_state and 'drawn_geometry' not in st.session_state and 'skewt_results' not in st.session_state:
        st.markdown("Configure sua análise no **Painel de Controle** à esquerda e clique em **Gerar Análise** para exibir os resultados aqui.")

def renderizar_resumo_selecao():
    # Verifica qual aba está ativa para decidir o que mostrar
    nav_option = st.session_state.get('nav_option')

    # --- LÓGICA PARA SKEW-T ---
    if nav_option == "Skew-T":
        with st.expander("📋 Resumo das Opções Selecionadas", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.markdown("**Análise:**\nSondagem (Skew-T)")
            with c2:
                lat = st.session_state.get('skew_lat')
                lon = st.session_state.get('skew_lon')
                st.markdown(f"**Localização:**\nLat: {lat} | Lon: {lon}")
            with c3:
                date = st.session_state.get('skew_date')
                hour = st.session_state.get('skew_hour')
                data_str = date.strftime('%d/%m/%Y') if date else "--/--/----"
                st.markdown(f"**Momento:**\n{data_str} às {hour}:00 UTC")
        return

    # --- LÓGICA PARA MAPAS E SÉRIES ---
    if "variavel" not in st.session_state:
        return

    with st.expander("📋 Resumo das Opções Selecionadas", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"**Variável:**\n{st.session_state.variavel}")
        with c2:
            tipo = st.session_state.tipo_localizacao
            local_txt = ""
            if tipo == "Estado": local_txt = st.session_state.estado
            elif tipo == "Município": local_txt = f"{st.session_state.municipio} ({st.session_state.estado})"
            elif tipo == "Círculo (Lat/Lon/Raio)": local_txt = "Área Circular"
            elif tipo == "Polígono": local_txt = "Polígono Personalizado"
            st.markdown(f"**Local ({tipo}):**\n{local_txt}")
        with c3:
            periodo = st.session_state.tipo_periodo
            per_txt = ""
            if periodo == "Personalizado": per_txt = f"{st.session_state.data_inicio.strftime('%d/%m/%Y')} - {st.session_state.data_fim.strftime('%d/%m/%Y')}"
            elif periodo == "Mensal": per_txt = f"{st.session_state.mes_mensal}/{st.session_state.ano_mensal}"
            elif periodo == "Anual": per_txt = str(st.session_state.ano_anual)
            elif periodo == "Horário Específico":
                 data = st.session_state.get('data_horaria')
                 hora = st.session_state.get('hora_especifica')
                 if data: per_txt = f"{data.strftime('%d/%m/%Y')} às {hora}:00h (UTC)"
            st.markdown(f"**Período ({periodo}):**\n{per_txt}")

# -------------------------------------
# Renderizar a opção sobre o aplicativo
# -------------------------------------

def renderizar_pagina_sobre():
    st.title("Sobre o Clima-Cast-Crepaldi")
    st.markdown("---")
    url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/sobre.docx"
    try:
        with st.spinner("Carregando documentação..."):
            r = requests.get(url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(r.content)
                path = tmp.name
        try: pypandoc.get_pandoc_version()
        except: pypandoc.download_pandoc()
        html = pypandoc.convert_file(path, "html", format="docx", extra_args=["--embed-resources"])
        html = re.sub(r'<img src="([^"]+)"', r'<div style="display:flex;justify-content:center;margin:20px 0;"><img src="\1" style="max-width:600px;width:100%;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);"', html)
        html += "</div>" 
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e: st.error(f"Erro ao carregar sobre: {e}")
    finally: 
        if path and os.path.exists(path): os.remove(path)



