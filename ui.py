# ==================================================================================
# ui.py — Interface do usuário do sistema Clima-Cast-Crepaldi
# ==================================================================================

import streamlit as st
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import locale

# ==================================================================================
# CONFIGURAÇÃO INICIAL
# ==================================================================================

st.set_page_config(
    page_title="Clima-Cast-Crepaldi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Protege contra erro de locale no Streamlit Cloud
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    locale.setlocale(locale.LC_TIME, "C")

# ==================================================================================
# FUNÇÕES PRINCIPAIS
# ==================================================================================

def configurar_pagina():
    """Configura o título e separador inicial."""
    st.markdown("---")


def reset_analysis_state():
    """Callback para limpar o estado dos resultados sempre que um filtro é alterado."""
    keys_to_clear = ['area_validada', 'show_confirmation_map', 'analysis_triggered', 'drawn_geometry']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


# ==================================================================================
# SIDEBAR — corrigida para funcionar com ou sem parâmetros
# ==================================================================================
def renderizar_sidebar(dados_geo=None, mapa_nomes_uf=None):
    """
    Cria a barra lateral com os filtros.
    Se os dados não forem fornecidos, carrega sob demanda via gee_handler.
    """
    if dados_geo is None or mapa_nomes_uf is None:
        from gee_handler import get_brazilian_geopolitical_data_local
        dados_geo, mapa_nomes_uf = get_brazilian_geopolitical_data_local()

    with st.sidebar:
        st.header("Painel de Controle")

        st.radio(
            "Navegação",
            ["Mapas", "Séries Temporais", "Sobre o Aplicativo"],
            label_visibility="collapsed",
            key='nav_option',
            on_change=reset_analysis_state
        )

        st.markdown("---")
        opcao_selecionada = st.session_state.get('nav_option', 'Mapas')

        if opcao_selecionada in ["Mapas", "Séries Temporais"]:
            st.markdown("<p style='text-align: center;'>Selecione os filtros abaixo para gerar os dados.</p>", unsafe_allow_html=True)
            
            st.subheader("1. Base de Dados")
            st.selectbox("Selecione a Base de Dados", ["ERA5-LAND"], key='base_de_dados', on_change=reset_analysis_state)
            st.divider()

            st.subheader("2. Variável Meteorológica")
            st.selectbox("Selecione a Variável", 
                         ["Temperatura do Ar (2m)", "Precipitação Total", "Velocidade do Vento (10m)"], 
                         key='variavel', on_change=reset_analysis_state)
            st.divider()

            st.subheader("3. Localização")
            st.selectbox("Selecione o tipo de área de interesse", 
                         ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"], 
                         key='tipo_localizacao', on_change=reset_analysis_state)
            
            tipo_localizacao = st.session_state.get('tipo_localizacao', 'Estado')
            lista_estados_formatada = ["Selecione..."] + [f"{mapa_nomes_uf[uf]} - {uf}" for uf in sorted(mapa_nomes_uf)]

            if tipo_localizacao == "Estado":
                st.selectbox("Selecione o Estado", lista_estados_formatada, key='estado', on_change=reset_analysis_state)
            elif tipo_localizacao == "Município":
                st.selectbox("Selecione o Estado", lista_estados_formatada, key='estado', on_change=reset_analysis_state)
                estado_selecionado_str = st.session_state.get('estado', 'Selecione...')
                lista_municipios = ["Selecione um estado primeiro"]
                if estado_selecionado_str and estado_selecionado_str != "Selecione...":
                    uf_selecionada = estado_selecionado_str.split(' - ')[-1]
                    lista_municipios = ["Selecione..."] + dados_geo.get(uf_selecionada, [])
                st.selectbox("Selecione o Município", lista_municipios, key='municipio', on_change=reset_analysis_state)
            elif tipo_localizacao == "Círculo (Lat/Lon/Raio)":
                st.number_input("Latitude", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                st.number_input("Longitude", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
            elif tipo_localizacao == "Polígono":
                pass

            st.divider()

            st.subheader("4. Período de Análise")
            if opcao_selecionada == "Mapas":
                st.selectbox("Selecione o tipo de período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state)
            else:
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_periodo = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1979, -1))

            st.session_state.date_error = False
            if tipo_periodo == "Personalizado":
                hoje = datetime.now()
                data_padrao_fim = hoje - relativedelta(months=4)
                data_padrao_inicio = data_padrao_fim - relativedelta(days=7)
                col1, col2 = st.columns(2)
                with col1:
                    st.date_input("Data de Início", value=data_padrao_inicio, key='data_inicio', on_change=reset_analysis_state)
                with col2:
                    st.date_input("Data de Fim", value=data_padrao_fim, key='data_fim', on_change=reset_analysis_state)
                if st.session_state.data_fim < st.session_state.data_inicio:
                    st.error("Atenção: A data final é anterior à data inicial.")
                    st.session_state.date_error = True
            elif tipo_periodo == "Mensal":
                st.selectbox("Ano", lista_anos, key='ano_mensal', on_change=reset_analysis_state)
                nomes_meses = [calendar.month_name[i].capitalize() for i in range(1, 13)]
                st.selectbox("Mês", nomes_meses, key='mes_mensal', on_change=reset_analysis_state)
            elif tipo_periodo == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            st.divider()

            if opcao_selecionada == "Mapas":
                st.subheader("5. Tipo de Mapa")
                st.radio("Selecione o formato", ["Interativo", "Estático"], key='map_type', horizontal=True, on_change=reset_analysis_state)
                st.divider()

            if st.button("Gerar Análise", type="primary", use_container_width=True, disabled=st.session_state.get('date_error', False)):
                st.session_state['analysis_triggered'] = True
                st.rerun()
        
        return opcao_selecionada


# ==================================================================================
# PÁGINAS PRINCIPAIS
# ==================================================================================

def renderizar_pagina_principal(opcao_navegacao):
    """Exibe o conteúdo da página principal com o logo."""
    agora = datetime.now()
    data_hora_formatada = agora.strftime("%d/%m/%Y, %H:%M:%S")

    col1, col2 = st.columns([3, 1])
    with col1:
        logo_col, title_col = st.columns([1, 5])
        with logo_col:
            st.image("logo.png", width=70)
        with title_col:
            st.title(f"Clima-Cast-Crepaldi: {opcao_navegacao}")

    with col2:
        st.write("")
        st.markdown(f"<p style='text-align: right; color: grey;'>{data_hora_formatada}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("Configure sua análise no **Painel de Controle** à esquerda e clique em **Gerar Análise** para exibir os resultados aqui.")


def renderizar_resumo_selecao():
    """Mostra um resumo dos filtros selecionados."""
    st.subheader("🔎 Filtros Escolhidos para Análise")
    col_resumo1, col_resumo2 = st.columns(2)
    with col_resumo1:
        st.markdown(f"**Base de Dados:** `{st.session_state.base_de_dados}`")
        st.markdown(f"**Variável:** `{st.session_state.variavel}`")
        st.markdown(f"**Tipo de Localização:** `{st.session_state.tipo_localizacao}`")
        if st.session_state.tipo_localizacao == "Estado":
            st.markdown(f"**Estado:** `{st.session_state.estado}`")
        elif st.session_state.tipo_localizacao == "Município":
            st.markdown(f"**Estado:** `{st.session_state.estado}`")
            st.markdown(f"**Município:** `{st.session_state.municipio}`")
        elif st.session_state.tipo_localizacao == "Círculo (Lat/Lon/Raio)":
            st.markdown(f"**Centro:** `Lat: {st.session_state.latitude}, Lon: {st.session_state.longitude}`")
            st.markdown(f"**Raio:** `{st.session_state.raio} km`")
        elif st.session_state.tipo_localizacao == "Polígono":
            st.markdown(f"**Área:** `Desenhada no mapa`")
    with col_resumo2:
        st.markdown(f"**Tipo de Período:** `{st.session_state.tipo_periodo}`")
        if st.session_state.tipo_periodo == "Personalizado":
            data_inicio_fmt = st.session_state.data_inicio.strftime('%d/%m/%Y')
            data_fim_fmt = st.session_state.data_fim.strftime('%d/%m/%Y')
            st.markdown(f"**Data de Início:** `{data_inicio_fmt}`")
            st.markdown(f"**Data de Fim:** `{data_fim_fmt}`")
        elif st.session_state.tipo_periodo == "Mensal":
            st.markdown(f"**Período:** `{st.session_state.mes_mensal} de {st.session_state.ano_mensal}`")
        elif st.session_state.tipo_periodo == "Anual":
            st.markdown(f"**Período:** `Ano de {st.session_state.ano_anual}`")
        if st.session_state.get('nav_option') == "Mapas":
            st.markdown(f"**Tipo de Mapa:** `{st.session_state.map_type}`")
    st.info("Por favor, confira suas seleções. A busca pelos dados será iniciada com base nestes parâmetros.")


def renderizar_validacao_mapa():
    """Exibe a mensagem de conferência e o botão para validar a área."""
    st.info("Confira a área de interesse no mapa acima. Se estiver correto, clique em 'Validar Área' para continuar.")
    disable_validation = False
    
    if st.session_state.tipo_localizacao == "Polígono" and 'drawn_geometry' not in st.session_state:
        st.warning("Por favor, desenhe um polígono no mapa para continuar.")
        disable_validation = True

    if st.button("Validar Área", type="primary", use_container_width=True, disabled=disable_validation):
        st.session_state['area_validada'] = True
        st.session_state['show_confirmation_map'] = False
        st.rerun()


def renderizar_pagina_sobre():
    """Página institucional e informativa sobre o aplicativo."""
    st.markdown("""
    O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido na disciplina  
    **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**, do curso de **Ciências Atmosféricas da UNIFEI**.  
    Seu propósito é **integrar dados meteorológicos de reanálises globais** e disponibilizá-los em uma plataforma visual e acessível.
    """)
