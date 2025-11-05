# ==================================================================================
# ui.py — Clima-Cast-Crepaldi (versão estável restaurada)
# ==================================================================================
import streamlit as st
from datetime import date

# --------------------------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# --------------------------------------------------------------------------
def configurar_pagina():
    """Define título, layout e tema da página Streamlit."""
    st.set_page_config(
        page_title="Clima-Cast-Crepaldi",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("🌦️ Clima-Cast-Crepaldi")
    st.markdown("---")

# --------------------------------------------------------------------------
# SIDEBAR — Menu de navegação e filtros
# --------------------------------------------------------------------------
def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    """Renderiza a barra lateral principal."""
    st.sidebar.header("🧭 Navegação")

    menu = st.sidebar.radio(
        "Escolha a visualização:",
        ["Mapas", "Séries Temporais", "Sobre o Aplicativo"]
    )
    st.session_state.nav_option = menu

    if menu != "Sobre o Aplicativo":
        st.sidebar.header("🎯 Área de Interesse")

        tipo_loc = st.sidebar.selectbox(
            "Tipo de Localização:",
            ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"],
            key="tipo_localizacao"
        )

        if tipo_loc == "Estado":
            uf_siglas = sorted(list(mapa_nomes_uf.keys()))
            uf_opcoes = [f"{mapa_nomes_uf[sigla]} - {sigla}" for sigla in uf_siglas]
            st.session_state.estado = st.sidebar.selectbox("Estado:", uf_opcoes)

        elif tipo_loc == "Município":
            uf_siglas = sorted(list(mapa_nomes_uf.keys()))
            uf_opcoes = [f"{mapa_nomes_uf[sigla]} - {sigla}" for sigla in uf_siglas]
            st.session_state.estado = st.sidebar.selectbox("Estado:", uf_opcoes)
            uf_sigla = st.session_state.estado.split(" - ")[-1]
            lista_municipios = dados_geo.get(uf_sigla, [])
            st.session_state.municipio = st.sidebar.selectbox("Município:", lista_municipios)

        elif tipo_loc == "Círculo (Lat/Lon/Raio)":
            st.session_state.latitude = st.sidebar.number_input("Latitude:", -90.0, 90.0, -23.0, step=0.1)
            st.session_state.longitude = st.sidebar.number_input("Longitude:", -180.0, 180.0, -46.0, step=0.1)
            st.session_state.raio = st.sidebar.number_input("Raio (km):", 1, 500, 50)

        elif tipo_loc == "Polígono":
            st.sidebar.info("Desenhe o polígono diretamente no mapa principal.")

        st.sidebar.header("📆 Período de Análise")
        tipo_periodo = st.sidebar.selectbox("Tipo de Período:", ["Mensal", "Anual"], key="tipo_periodo")

        if tipo_periodo == "Mensal":
            ano = st.sidebar.number_input("Ano:", 1981, date.today().year, date.today().year)
            mes = st.sidebar.selectbox(
                "Mês:",
                ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            )
            st.session_state.ano, st.session_state.mes = ano, mes
        else:
            ano_ini = st.sidebar.number_input("Ano Inicial:", 1981, date.today().year - 1, date.today().year - 1)
            ano_fim = st.sidebar.number_input("Ano Final:", 1981, date.today().year, date.today().year)
            st.session_state.ano_inicio, st.session_state.ano_fim = ano_ini, ano_fim

        st.sidebar.header("🌡️ Variável Climática")
        st.session_state.variavel = st.sidebar.selectbox(
            "Selecione a variável:",
            ["Temperatura do Ar (2m)", "Precipitação Total", "Velocidade do Vento (10m)"]
        )

        if menu == "Mapas":
            st.sidebar.header("🗺️ Tipo de Mapa")
            st.session_state.map_type = st.sidebar.radio(
                "Tipo de mapa:",
                ["Estático", "Interativo"]
            )

        if st.sidebar.button("Gerar Análise 🚀"):
            st.session_state.analysis_triggered = True

    return menu

# --------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# --------------------------------------------------------------------------
def renderizar_pagina_principal(opcao_menu):
    """Renderiza o conteúdo principal."""
    if opcao_menu == "Mapas":
        st.markdown("### 🗺️ Módulo de Mapas Climáticos")
        st.info("Selecione o tipo de localização e variável no menu lateral e clique em **Gerar Análise**.")
    elif opcao_menu == "Séries Temporais":
        st.markdown("### 📈 Módulo de Séries Temporais")
        st.info("Selecione o tipo de localização e variável no menu lateral e clique em **Gerar Análise**.")

# --------------------------------------------------------------------------
# PÁGINA SOBRE O APLICATIVO
# --------------------------------------------------------------------------
def renderizar_pagina_sobre():
    """Exibe informações sobre o aplicativo."""
    st.title("ℹ️ Sobre o Clima-Cast-Crepaldi")
    st.markdown("""
    O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido no âmbito da disciplina
    **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)** do curso de
    **Ciências Atmosféricas (UNIFEI)**.
    
    Ele permite consultar e visualizar dados do **ERA5-Land (ECMWF)** diretamente via
    **Google Earth Engine (GEE)**, oferecendo análises em diferentes escalas e modos:
    
    - 🌎 Mapas Estáticos e Interativos  
    - 📈 Séries Temporais de Variáveis Meteorológicas  
    - 💾 Exportação de resultados (mapas, tabelas, séries)  
    
    **Autor:** Paulo C. Crepaldi  
    **Orientador:** Prof. Enrique Vieira Mattos  
    **Instituição:** Universidade Federal de Itajubá (UNIFEI)
    """)

# --------------------------------------------------------------------------
# RESUMO DA SELEÇÃO
# --------------------------------------------------------------------------
def renderizar_resumo_selecao():
    """Mostra um resumo das seleções antes de processar os dados."""
    st.markdown("#### 📋 Resumo das Seleções")
    tipo = st.session_state.get("tipo_localizacao", "")
    var = st.session_state.get("variavel", "")
    st.write(f"**Tipo de Localização:** {tipo}")
    st.write(f"**Variável Selecionada:** {var}")

# --------------------------------------------------------------------------
# VALIDAÇÃO DE MAPA (para círculo/polígono)
# --------------------------------------------------------------------------
def renderizar_validacao_mapa():
    """Botão de validação após desenhar ou definir círculo."""
    if st.button("✅ Validar Área"):
        st.session_state.area_validada = True
        st.session_state.show_confirmation_map = False
        st.rerun()
