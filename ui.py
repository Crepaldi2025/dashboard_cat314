# ==================================================================================
# ui.py (Atualizado v57 - Texto Informativo Melhorado)
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

st.set_page_config(page_title="Clima-Cast-Crepaldi", layout="wide", initial_sidebar_state="expanded")

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

def reset_analysis_state():
    for key in ['analysis_triggered', 'analysis_results', 'drawn_geometry']:
        if key in st.session_state: del st.session_state[key]

def reset_analysis_results_only():
    for key in ['analysis_triggered', 'analysis_results']:
        if key in st.session_state: del st.session_state[key]
    
def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    with st.sidebar:
        st.header("Painel de Controle")
        st.radio("Navegação", ["Mapas", "Séries Temporais", "Sobre o Aplicativo"], label_visibility="collapsed", key='nav_option', on_change=reset_analysis_state)
        st.markdown("---")
        opcao = st.session_state.get('nav_option', 'Mapas')

        if opcao in ["Mapas", "Séries Temporais"]:
            st.markdown("<p style='text-align: center;'>Selecione os filtros abaixo para gerar os dados.</p>", unsafe_allow_html=True)
            
            st.subheader("1. Base de Dados")
            st.selectbox("Selecione a Base de Dados", ["ERA5-LAND"], key='base_de_dados', on_change=reset_analysis_state)
            st.divider()

            st.subheader("2. Variável Meteorológica")
            st.selectbox("Selecione a Variável", 
                         [
                             "Temperatura do Ar (2m)", 
                             "Temperatura do Ponto de Orvalho (2m)",
                             "Precipitação Total", 
                             "Umidade Relativa (2m)", 
                             "Velocidade do Vento (10m)", 
                             "Radiação Solar Incidente"
                         ], 
                         key='variavel', 
                         on_change=reset_analysis_state)
            st.divider()

            st.subheader("3. Localização")
            st.selectbox("Selecione o tipo de área de interesse", ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"], key='tipo_localizacao', on_change=reset_analysis_state) 
            
            tipo_loc = st.session_state.get('tipo_localizacao', 'Estado')
            lista_ufs = ["Selecione..."] + [f"{mapa_nomes_uf[uf]} - {uf}" for uf in sorted(mapa_nomes_uf)]

            if tipo_loc == "Estado":
                st.selectbox("Selecione o Estado", lista_ufs, key='estado', on_change=reset_analysis_state)
            elif tipo_loc == "Município":
                st.selectbox("Selecione o Estado", lista_ufs, key='estado', on_change=reset_analysis_state)
                estado_str = st.session_state.get('estado', 'Selecione...')
                lista_muns = ["Selecione..."] + dados_geo.get(estado_str.split(' - ')[-1], []) if estado_str != "Selecione..." else ["Selecione um estado primeiro"]
                st.selectbox("Selecione o Município", lista_muns, key='municipio', on_change=reset_analysis_state)
            
            elif tipo_loc == "Círculo (Lat/Lon/Raio)":
                st.number_input("Latitude", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                st.number_input("Longitude", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
                
                with st.popover("ℹ️ Ajuda: Definindo o Círculo"):
                    st.markdown("""
                    **Como preencher as coordenadas:**
                    
                    * **Latitude:** Coordenada em **graus decimais**. 
                        * *Para o Brasil:* Use valores negativos (Hemisfério Sul). Ex: `-22.42`.
                    * **Longitude:** Coordenada em **graus decimais**.
                        * *Para o Brasil:* Use valores negativos (Oeste de Greenwich). Ex: `-45.46`.
                    * **Raio (km):** Distância do centro até a borda da área de análise.
                    
                    💡 **Dica:** Abra o Google Maps, clique com o botão direito no local desejado e copie os números que aparecem no topo (ex: `-22.42, -45.46`).
                    """)
            
            elif tipo_loc == "Polígono":
                if st.session_state.get('drawn_geometry'): 
                    st.success("✅ Polígono capturado com sucesso!")
                else: 
                    st.markdown("""
                    <div style="background-color: #e0f7fa; padding: 10px; border-radius: 5px; border-left: 5px solid #00acc1;">
                        <h4 style="margin:0; color: #006064;">👉 Desenhe no Mapa</h4>
                        <p style="font-size: 0.9em; margin-top: 5px;">
                        Utilize as ferramentas na <b>lateral esquerda do mapa principal</b> para desenhar sua área.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                with st.popover("ℹ️ Ajuda: Ferramentas de Desenho"): 
                    st.markdown("""
                    **Guia das Ferramentas:**
                    ⬟ **Polígono:** Formas livres.
                    ⬛ **Retângulo:** Áreas quadradas.
                    📝 **Editar:** Ajustar pontos.
                    🗑️ **Lixeira:** Apagar desenho.
                    """)
            
            st.divider()

            st.subheader("4. Período de Análise")
            if opcao == "Mapas": st.selectbox("Selecione o tipo de período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state)
            else: st.session_state.tipo_periodo = "Personalizado"
            
            tipo_per = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1949, -1))

            st.session_state.date_error = False
            if tipo_per == "Personalizado":
                hoje = datetime.now()
                fim_padrao = hoje.replace(day=1) - relativedelta(days=1)
                inicio_padrao = fim_padrao.replace(day=1)
                c1, c2 = st.columns(2)
                with c1: st.date_input("Início", value=inicio_padrao, key='data_inicio', on_change=reset_analysis_state)
                with c2: st.date_input("Fim", value=fim_padrao, key='data_fim', on_change=reset_analysis_state)
                if st.session_state.data_fim < st.session_state.data_inicio:
                    st.error("Data final anterior à inicial.")
                    st.session_state.date_error = True
            elif tipo_per == "Mensal":
                st.selectbox("Ano", lista_anos, key='ano_mensal', on_change=reset_analysis_state)
                st.selectbox("Mês", NOMES_MESES_PT, key='mes_mensal', on_change=reset_analysis_state)
            elif tipo_per == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            
            st.divider()

            if opcao == "Mapas":
                st.subheader("5. Tipo de Mapa")
                st.radio("Formato", ["Interativo", "Estático"], key='map_type', horizontal=True, on_change=reset_analysis_results_only)
                st.divider()

            disable = st.session_state.get('date_error', False)
            if tipo_loc == "Polígono" and not st.session_state.get('drawn_geometry'): disable = True
            elif tipo_loc == "Círculo (Lat/Lon/Raio)" and not (st.session_state.get('latitude') and st.session_state.get('longitude')): disable = True

            if st.button("Gerar Análise", type="primary", use_container_width=True, disabled=disable):
                st.session_state.analysis_triggered = True
                st.rerun()
            
            st.warning("⚠️ **Importante:** Confira todas as opções acima (Variável, Local e Data) antes de gerar a análise.")
        
        return opcao

def renderizar_pagina_principal(opcao):
    # CSS PARA REMOVER ESPAÇO EM BRANCO SUPERIOR
    st.markdown("""
        <style>
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
            }
            h1 {
                padding-top: 0rem !important;
                margin-top: 0rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_br)
    agora_utc = datetime.now(pytz.utc)
    
    c1, c2 = st.columns([3, 1.5])
    with c1:
        lc, tc = st.columns([1, 5])
        with lc: 
            if os.path.exists("logo.png"): st.image("logo.png", width=70)
            else: st.write("🌐")
        with tc: st.title(f"Clima-Cast: {opcao}")
    with c2:
        st.markdown(f"<div style='border:1px solid #ccc;padding:5px;text-align:center;border-radius:5px;'><b>🇧🇷 BRT:</b> {agora.strftime('%d/%m/%Y %H:%M')}<br><small>🌐 UTC: {agora_utc.strftime('%d/%m/%Y %H:%M')}</small></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    if "analysis_results" not in st.session_state and 'drawn_geometry' not in st.session_state:
        # --- ATUALIZAÇÃO AQUI: Texto mais claro ---
        st.markdown("Configure sua análise no **Painel de Controle** à esquerda e clique em **Gerar Análise** para exibir os resultados aqui.")

def renderizar_resumo_selecao():
    with st.expander("📋 Resumo das Opções Selecionadas", expanded=True):
        st.write(f"**Variável:** {st.session_state.variavel}")
        
        tipo = st.session_state.tipo_localizacao
        st.write(f"**Tipo de Localização:** {tipo}")
        
        if tipo == "Estado":
            st.write(f"**Estado:** {st.session_state.estado}")
        elif tipo == "Município":
            st.write(f"**Município:** {st.session_state.municipio} ({st.session_state.estado})")
        elif tipo == "Círculo (Lat/Lon/Raio)":
            st.write(f"**Centro:** {st.session_state.latitude}, {st.session_state.longitude}")
            st.write(f"**Raio:** {st.session_state.raio} km")
        elif tipo == "Polígono":
             st.write("**Área:** Polígono desenhado manualmente")
             
        periodo = st.session_state.tipo_periodo
        st.write(f"**Período ({periodo}):**")
        if periodo == "Personalizado":
            st.write(f"De {st.session_state.data_inicio.strftime('%d/%m/%Y')} até {st.session_state.data_fim.strftime('%d/%m/%Y')}")
        elif periodo == "Mensal":
             st.write(f"{st.session_state.mes_mensal} de {st.session_state.ano_mensal}")
        elif periodo == "Anual":
             st.write(f"Ano de {st.session_state.ano_anual}")

def renderizar_pagina_sobre():
    st.title("Sobre o Clima-Cast-Crepaldi")
    st.markdown("---")
    url = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/sobre.docx"
    try:
        with st.spinner("Carregando..."):
            r = requests.get(url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(r.content)
                path = tmp.name
        try: pypandoc.get_pandoc_version()
        except: pypandoc.download_pandoc()
        html = pypandoc.convert_file(path, "html", format="docx", extra_args=["--embed-resources"])
        html = re.sub(r'<img src="([^"]+)"', r'<p style="text-align:center;"><img src="\1" style="max-width:500px;width:100%;"', html)
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e: st.error(f"Erro: {e}")
    finally: 
        if path and os.path.exists(path): os.remove(path)
