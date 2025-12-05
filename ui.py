# ==================================================================================
# ui.py
# ==================================================================================
import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
import locale
import os
import requests
import pypandoc
import tempfile

# Configuração Inicial
st.set_page_config(page_title="Clima-Cast", layout="wide", page_icon="🌦️")

# Tenta configurar locale
try: locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except: pass 

# Funções Auxiliares de Estado
def reset_analysis_state():
    """Limpa cache geral."""
    for k in ['analysis_triggered', 'analysis_results', 'skewt_results']:
        if k in st.session_state: del st.session_state[k]

def reset_analysis_results_only():
    """Limpa apenas resultados de mapas."""
    for k in ['analysis_triggered', 'analysis_results']:
        if k in st.session_state: del st.session_state[k]

# --- SIDEBAR ---
def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    with st.sidebar:
        st.header("🌦️ Clima-Cast")
        st.divider()
        
        # Menu Principal
        mode = st.radio(
            "Modo de Visualização", 
            ["Mapas", "Séries Temporais", "Skew-T", "Sobre"], 
            label_visibility="collapsed", 
            key='nav_option', 
            on_change=reset_analysis_state
        )
        
        # --- SKEW-T ---
        if mode == "Skew-T":
            st.subheader("🌪️ Diagrama Skew-T")
            st.info("Sondagem atmosférica via ERA5 (Histórico) ou GFS (Recente).")
            
            st.divider()
            c1, c2 = st.columns(2)
            c1.number_input("Latitude", value=-23.55, format="%.4f", key='skew_lat', on_change=reset_analysis_state)
            c2.number_input("Longitude", value=-46.63, format="%.4f", key='skew_lon', on_change=reset_analysis_state)
            
            st.divider()
            # Data padrão: Hoje
            now = datetime.now()
            st.date_input("Data", value=now, max_value=now, key='skew_date', format="DD/MM/YYYY", on_change=reset_analysis_state)
            st.slider("Hora (UTC)", 0, 23, 12, key='skew_hour', on_change=reset_analysis_state)
            
            st.caption("Nota: Datas antigas podem levar alguns segundos para baixar do arquivo ERA5.")
            
            st.divider()
            st.button("🚀 Gerar Skew-T", type="primary", use_container_width=True, on_click=lambda: st.session_state.update(analysis_triggered=True))

        # --- MAPAS / SÉRIES ---
        elif mode in ["Mapas", "Séries Temporais"]:
            st.subheader("⚙️ Configuração")
            st.selectbox("Base de Dados", ["ERA5-LAND"], key='base_de_dados', on_change=reset_analysis_state)
            st.selectbox("Variável", [
                "Temperatura do Ar (2m)", "Precipitação Total", 
                "Umidade Relativa (2m)", "Velocidade do Vento (10m)", 
                "Radiação Solar Incidente"
            ], key='variavel', on_change=reset_analysis_state)
            
            st.divider()
            st.selectbox("Recorte", ["Estado", "Município", "Polígono"], key='tipo_localizacao', on_change=reset_analysis_state)
            
            tipo = st.session_state.tipo_localizacao
            ufs = sorted(list(mapa_nomes_uf.keys()))
            
            if tipo == "Estado":
                st.selectbox("UF", ufs, key='estado', on_change=reset_analysis_state)
            elif tipo == "Município":
                st.selectbox("UF", ufs, key='estado', on_change=reset_analysis_state)
                uf_sel = st.session_state.get('estado')
                muns = dados_geo.get(uf_sel, []) if uf_sel else []
                st.selectbox("Município", ["Selecione..."] + muns, key='municipio', on_change=reset_analysis_state)
            elif tipo == "Polígono":
                if st.session_state.get('drawn_geometry'): st.success("✅ Área definida")
                else: st.info("✏️ Desenhe no mapa")

            st.divider()
            st.selectbox("Período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state)
            
            if st.session_state.tipo_periodo == "Personalizado":
                c1, c2 = st.columns(2)
                c1.date_input("Início", key='data_inicio', on_change=reset_analysis_state)
                c2.date_input("Fim", key='data_fim', on_change=reset_analysis_state)
            
            if mode == "Mapas":
                st.divider()
                st.radio("Visualização", ["Interativo", "Estático"], key='map_type', horizontal=True)

            st.divider()
            st.button("🚀 Gerar Análise", type="primary", use_container_width=True, on_click=lambda: st.session_state.update(analysis_triggered=True))

        return mode

# --- PÁGINA PRINCIPAL ---
def renderizar_pagina_principal(mode):
    st.title(mode)
    st.markdown("---")
    
    # Se não houver nada processado, mostra dica
    if not any(k in st.session_state for k in ['analysis_results', 'skewt_results', 'drawn_geometry']):
        st.info("👈 Utilize o menu lateral para configurar sua análise.")

# --- RESUMO ---
def renderizar_resumo_selecao(current_mode):
    if current_mode == "Skew-T":
        with st.expander("📋 Resumo (Skew-T)", expanded=True):
            lat = st.session_state.get('skew_lat')
            lon = st.session_state.get('skew_lon')
            dt = st.session_state.get('skew_date')
            hr = st.session_state.get('skew_hour')
            if dt:
                st.markdown(f"**Local:** {lat}, {lon} | **Data:** {dt.strftime('%d/%m/%Y')} | **Hora:** {hr}h UTC")
    
    elif current_mode in ["Mapas", "Séries Temporais"] and "variavel" in st.session_state:
        with st.expander(f"📋 Resumo ({current_mode})", expanded=True):
            st.markdown(f"**Variável:** {st.session_state.variavel}")
            st.markdown(f"**Local:** {st.session_state.tipo_localizacao}")

# --- SOBRE ---
def renderizar_pagina_sobre():
    st.title("Sobre o Projeto")
    st.markdown("---")
    st.write("Versão 1.0 | Clima-Cast Crepaldi")
    st.info("Este aplicativo utiliza dados do Google Earth Engine e Open-Meteo (ERA5).")
