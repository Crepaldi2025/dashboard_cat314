# ==================================================================================
# ui.py (Versão v70 - Explicações Detalhadas Restauradas)
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

# Configuração da Página
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

def reset_analysis_state():
    for key in ['analysis_triggered', 'analysis_results', 'drawn_geometry']:
        if key in st.session_state: del st.session_state[key]

def reset_analysis_results_only():
    for key in ['analysis_triggered', 'analysis_results']:
        if key in st.session_state: del st.session_state[key]
    
def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    with st.sidebar:
        # --- 1. TÍTULO ---
        st.markdown("<h2 style='text-align: center;'>🌦️ Clima-Cast-Crepaldi</h2>", unsafe_allow_html=True)
        st.markdown("---")

        # --- 2. NAVEGAÇÃO PRINCIPAL ---
        st.radio(
            "Modo de Visualização",
            ["Mapas", "Séries Temporais", "Sobre o Aplicativo"],
            label_visibility="collapsed", 
            key='nav_option',
            on_change=reset_analysis_state
        )
        
        opcao = st.session_state.get('nav_option', 'Mapas')

        if opcao in ["Mapas", "Séries Temporais"]:
            st.markdown("### ⚙️ Parâmetros da Análise")
            
            # --- 3. CONFIGURAÇÕES AVANÇADAS ---
            with st.expander("🔧 Fonte de Dados & Configurações"):
                st.selectbox(
                    "Base de Dados", 
                    ["ERA5-LAND"], 
                    key='base_de_dados', 
                    on_change=reset_analysis_state,
                    help="Reanálise climática global de alta resolução."
                )

            # --- 4. VARIÁVEL ---
            st.markdown("#### 🌡️ Variável Meteorológica")
            st.selectbox(
                "Selecione a Variável", 
                [
                    "Temperatura do Ar (2m)", 
                    "Temperatura do Ponto de Orvalho (2m)",
                    "Precipitação Total", 
                    "Umidade Relativa (2m)", 
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
                st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
            
            elif tipo_loc == "Município":
                st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
                estado_str = st.session_state.get('estado', 'Selecione...')
                
                lista_muns = ["Selecione um estado primeiro"]
                if estado_str != "Selecione...":
                     lista_muns = ["Selecione..."] + dados_geo.get(estado_str.split(' - ')[-1], [])
                
                st.selectbox("Município", lista_muns, key='municipio', on_change=reset_analysis_state)
            
            elif tipo_loc == "Círculo (Lat/Lon/Raio)":
                c1, c2 = st.columns(2)
                with c1: st.number_input("Lat", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                with c2: st.number_input("Lon", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
                
                # --- RESTAURADO: Ajuda detalhada do Círculo ---
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
                    st.success("✅ Polígono Definido", icon="🛡️")
                else: 
                    # --- RESTAURADO: Aviso visual claro ---
                    st.markdown("""
                    <div style="background-color: #e0f7fa; padding: 10px; border-radius: 5px; border-left: 5px solid #00acc1; font-size: 0.85em;">
                        <b style="color: #006064;">👉 Desenhe no Mapa Principal</b><br>
                        Utilize as ferramentas na lateral esquerda do mapa (lado direito da tela) para desenhar sua área.
                    </div>
                    """, unsafe_allow_html=True)

                # --- RESTAURADO: Guia detalhado das ferramentas ---
                with st.popover("ℹ️ Guia de Ferramentas"): 
                    st.markdown("""
                    **Função de cada ícone no mapa:**
                    
                    ⬟ **Polígono:**
                    Desenha áreas irregulares (ex: contorno de fazenda). Clique ponto a ponto para fechar.
                    
                    ⬛ **Retângulo:**
                    Clique e arraste para criar uma área quadrada/retangular.
                    
                    📝 **Editar:**
                    Permite clicar em um desenho existente e arrastar seus pontos para corrigir.
                    
                    🗑️ **Lixeira:**
                    Clique na lixeira e depois no desenho para apagá-lo.
                    """)
            
            st.divider()

            # --- 6. PERÍODO ---
            st.markdown("#### 📅 Recorte Temporal")
            
            if opcao == "Mapas": 
                st.selectbox("Tipo de Período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state, label_visibility="collapsed")
            else: 
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_per = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1949, -1))

            st.session_state.date_error = False
            
            if tipo_per == "Personalizado":
                hoje = datetime.now()
                fim_padrao = hoje.replace(day=1) - relativedelta(days=1)
                inicio_padrao = fim_padrao.replace(day=1)
                c1, c2 = st.columns(2)
                with c1: st.date_input("Início", value=inicio_padrao, key='data_inicio', on_change=reset_analysis_state, format="DD/MM/YYYY")
                with c2: st.date_input("Fim", value=fim_padrao, key='data_fim', on_change=reset_analysis_state, format="DD/MM/YYYY")
                
                if st.session_state.data_fim < st.session_state.data_inicio:
                    st.error("Data final anterior à inicial.")
                    st.session_state.date_error = True
            
            elif tipo_per == "Mensal":
                c1, c2 = st.columns(2)
                with c1: st.selectbox("Ano", lista_anos, key='ano_mensal', on_change=reset_analysis_state)
                with c2: st.selectbox("Mês", NOMES_MESES_PT, key='mes_mensal', on_change=reset_analysis_state)
            
            elif tipo_per == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            
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
                    """
                    <div style='font-size: 14px; color: #333; margin-top: 8px; line-height: 1.4;'>
                    ⚠️ <b>Atenção:</b> Confira os filtros selecionados acima antes de gerar.
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div style='font-size: 14px; color: #d32f2f; margin-top: 8px; line-height: 1.4;'>
                    ⚠️ <b>Obrigatório:</b> Preencha os campos de localização (desenho ou coordenadas) para habilitar o botão.
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            # --- 9. FOOTER ---
            st.markdown("---")
            st.markdown(
                """
                <div style='text-align: center; color: black; font-size: 14px;'>
                Desenvolvido por <b>Paulo C. Crepaldi</b><br>
                v1.0.0 | 2025
                </div>
                """, unsafe_allow_html=True
            )
        
        return opcao

def renderizar_pagina_principal(opcao):
    # CSS Refinado
    st.markdown("""
        <style>
            .block-container { padding-top: 3rem !important; padding-bottom: 5rem !important; }
            h1 { margin-top: 0rem !important; }
            .stExpander { border: 1px solid #f0f2f6; border-radius: 8px; }
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
        with tc: st.title(f"{opcao}")
    with c2:
        st.markdown(
            f"""
            <div style='
                border:1px solid #e0e0e0;
                padding:8px;
                text-align:center;
                border-radius:8px;
                background-color:rgba(255,255,255,0.7);
                font-size: 0.9rem;
            '>
                <b>🇧🇷 BRT:</b> {agora.strftime('%d/%m/%Y %H:%M')}<br>
                <span style='color:#666; font-size:0.8rem;'>🌐 UTC: {agora_utc.strftime('%d/%m/%Y %H:%M')}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    if "analysis_results" not in st.session_state and 'drawn_geometry' not in st.session_state:
        st.info("👈 **Comece aqui:** Configure sua análise no painel lateral e clique em **'🚀 Gerar Análise'**.")

def renderizar_resumo_selecao():
    with st.expander("📋 Resumo das Opções Selecionadas", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Variável:**\n{st.session_state.variavel}")
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
            st.markdown(f"**Período ({periodo}):**\n{per_txt}")

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


