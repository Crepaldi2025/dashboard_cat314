# ==================================================================================
# ui.py — (Corrigido v27)
# ==================================================================================

import streamlit as st
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import locale
import docx
import os

# ==================================================================================
# CONFIGURAÇÃO INICIAL (Idêntica)
# ==================================================================================
st.set_page_config(
    page_title="Clima-Cast-Crepaldi",
    layout="wide",
    initial_sidebar_state="expanded"
)
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "C") # Fallback
    except Exception:
        pass 

# ==================================================================================
# FUNÇÕES AUXILIARES (Modificada)
# ==================================================================================

# --- INÍCIO DA CORREÇÃO v27 (Erro 'NoneType' / Página em Branco) ---
@st.cache_data
def _carregar_texto_docx(file_path):
    """
    Função auxiliar para ler um arquivo .docx e retornar seu texto.
    (v27) - Versão simplificada e robusta que apenas extrai o texto.
    """
    if not os.path.exists(file_path):
        return None 

    try:
        doc = docx.Document(file_path)
        full_text = []
        
        # Lógica simplificada: Apenas pega o texto de cada parágrafo.
        # Isso é muito mais seguro e não vai quebrar em parágrafos vazios.
        for para in doc.paragraphs:
            full_text.append(para.text)
                
        # Junta os parágrafos com quebra de linha dupla (formatação Markdown)
        return "\n\n".join(full_text)
    except Exception as e:
        # Se falhar (ex: arquivo corrompido), mostra o erro.
        st.error(f"Erro ao ler o arquivo {file_path}: {e}")
        return None
# --- FIM DA CORREÇÃO v27 ---


# ==================================================================================
# FUNÇÕES PRINCIPAIS (Restante idêntico)
# ==================================================================================
def configurar_pagina():
    st.markdown("---")

def reset_analysis_state():
    keys_to_clear = [
        'analysis_triggered',   
        'analysis_results',     
        'drawn_geometry'        
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    

def renderizar_sidebar(dados_geo, mapa_nomes_uf):
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
            st.selectbox("Selecione a Variável", ["Temperatura do Ar (2m)", "Precipitação Total", "Velocidade do Vento (10m)"], key='variavel', on_change=reset_analysis_state)
            st.divider()

            st.subheader("3. Localização")
            st.selectbox("Selecione o tipo de área de interesse", 
                         ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"], 
                         key='tipo_localizacao', 
                         on_change=reset_analysis_state)
            
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
                if st.session_state.get('drawn_geometry'):
                    st.success("✅ Polígono desenhado e capturado.")
                elif opcao_selecionada == "Mapas":
                    st.info("Use as ferramentas no mapa principal para desenhar sua área.")
                else: 
                    st.info("Mude para a aba 'Mapas' para desenhar seu polígono.")
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
                data_padrao_fim = hoje.replace(day=1) - relativedelta(days=1)
                data_padrao_inicio = data_padrao_fim.replace(day=1)
                
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

            disable_button = st.session_state.get('date_error', False)
            tooltip_message = "Clique para gerar a análise"

            if tipo_localizacao == "Polígono":
                if not st.session_state.get('drawn_geometry'):
                    disable_button = True
                    tooltip_message = "Por favor, desenhe um polígono no mapa principal primeiro."
                if opcao_selecionada != "Mapas":
                     disable_button = True
                     tooltip_message = "O desenho de polígono só funciona na aba 'Mapas'."


            if st.button("Gerar Análise", 
                          type="primary", 
                          use_container_width=True, 
                          disabled=disable_button,
                          help=tooltip_message):
                
                st.session_state.analysis_triggered = True
                st.rerun()

        
        return opcao_selecionada


def renderizar_pagina_principal(opcao_navegacao):
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
    with st.expander("Resumo dos Filtros Utilizados", expanded=False):
        col_resumo1, col_resumo2 = st.columns(2)
        
        try:
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
        except AttributeError:
            st.warning("Filtros foram redefinidos. Por favor, selecione novamente.")


def renderizar_pagina_sobre():
    # --- INÍCIO DA CORREÇÃO v27 (Leitura do DOCX) ---
    texto_sobre = _carregar_texto_docx("sobre.docx")
    
    if texto_sobre is None:
        st.warning("Arquivo `sobre.docx` não encontrado. Exibindo texto padrão.")
        st.markdown("""
        **Objetivo**
        
        O sistema tem como principal objetivo proporcionar uma interface intuitiva e interativa para consulta, análise e visualização 
        de dados meteorológicos históricos dos municípios brasileiros...
        
        *(Por favor, crie um arquivo chamado 'sobre.docx' na mesma pasta do 'main.py' com o conteúdo desta página.)*
        """)
    else:
        # A mágica acontece aqui: st.markdown() vai renderizar o texto
        # (que já está formatado como Markdown no seu .docx)
        st.markdown(texto_sobre, unsafe_allow_html=True)
    # --- FIM DA CORREÇÃO v27 ---

    st.markdown("<hr class='divisor'>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray;font-size:12px;'>Desenvolvido por Paulo C. Crepaldi – CAT3B14 / UNIFEI</p>", unsafe_allow_html=True)
