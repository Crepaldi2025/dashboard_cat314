# ==================================================================================
# ui.py — (Versão Completa e Corrigida v48)
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

# ==================================================================================
# CONFIGURAÇÃO INICIAL
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
# FUNÇÕES AUXILIARES
# ==================================================================================

# Lista manual de meses para garantir o português (v38)
NOMES_MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

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
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n\n".join(full_text)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo {file_path}: {e}")
        return None

def reset_analysis_state():
    """
    Callback DESTRUTIVO: Limpa TUDO, incluindo a geometria desenhada.
    Usado quando o usuário muda a Variável, Localização ou Período.
    """
    keys_to_clear = [
        'analysis_triggered',   
        'analysis_results',     
        'drawn_geometry'        
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# (Correção v41)
def reset_analysis_results_only():
    """
    Callback "LEVE": Limpa APENAS os resultados, mantendo a geometria.
    Usado ao trocar o Tipo de Mapa (Interativo/Estático).
    """
    keys_to_clear = [
        'analysis_triggered',   
        'analysis_results',     
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
# ==================================================================================
# RENDERIZAÇÃO DOS COMPONENTES PRINCIPAIS
# ==================================================================================

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
            st.selectbox("Selecione a Variável", 
                         ["Temperatura do Ar (2m)", "Precipitação Total", "Umidade Relativa (2m)", "Velocidade do Vento (10m)", "Radiação Solar Incidente"], 
                         key='variavel', 
                         on_change=reset_analysis_state)
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
                
                with st.popover("ℹ️ Ajuda: Círculo (Lat/Lon/Raio)"):
                    st.markdown("""
                    **Como usar:**
                    1.  **Latitude:** Insira a latitude do ponto central (em graus decimais).
                    2.  **Longitude:** Insira a longitude do ponto central (em graus decimais).
                    3.  **Raio (km):** Defina o raio em quilômetros ao redor do ponto central.
                    """)

            elif tipo_localizacao == "Polígono":
                if st.session_state.get('drawn_geometry'):
                    st.success("✅ Polígono desenhado e capturado.")
                else: 
                    # Mensagem genérica que funciona para ambas as abas (v47)
                    st.info("O mapa de desenho aparecerá na tela principal.")

                with st.popover("ℹ️ Ajuda: Polígono"):
                    st.markdown("""
                    **Como usar:**
                    1.  Use as ferramentas de desenho (⬟ ou ■) no canto esquerdo do mapa.
                    """)
            
            st.divider()

            st.subheader("4. Período de Análise")
            
            if opcao_selecionada == "Mapas":
                st.selectbox("Selecione o tipo de período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state)
            else:
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_periodo = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1949, -1)) # (v35)

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
                st.selectbox("Mês", NOMES_MESES_PT, key='mes_mensal', on_change=reset_analysis_state) # (v38)
            
            elif tipo_periodo == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            
            st.divider()

            if opcao_selecionada == "Mapas":
                st.subheader("5. Tipo de Mapa")
                st.radio("Selecione o formato", 
                         ["Interativo", "Estático"], 
                         key='map_type', 
                         horizontal=True, 
                         on_change=reset_analysis_results_only # (v41)
                )
                st.divider()

            disable_button = st.session_state.get('date_error', False)
            tooltip_message = "Clique para gerar a análise"

            if tipo_localizacao == "Polígono":
                if not st.session_state.get('drawn_geometry'):
                    disable_button = True
                    tooltip_message = "Por favor, desenhe um polígono no mapa principal primeiro."
                # Restrição de aba removida (v47)
            
            elif tipo_localizacao == "Círculo (Lat/Lon/Raio)":
                if not (st.session_state.get('latitude') is not None and 
                        st.session_state.get('longitude') is not None and 
                        st.session_state.get('raio', 0) > 0):
                    disable_button = True
                    tooltip_message = "Por favor, insira valores válidos para Latitude, Longitude e Raio (> 0)."


            if st.button("Gerar Análise", 
                          type="primary", 
                          use_container_width=True, 
                          disabled=disable_button,
                          help=tooltip_message):
                
                st.session_state.analysis_triggered = True
                st.rerun()

        
        return opcao_selecionada

# ==================================================================================
# (O restante do arquivo: renderizar_pagina_principal, 
#  renderizar_resumo_selecao, renderizar_pagina_sobre é idêntico)
# ==================================================================================

def renderizar_pagina_principal(opcao_navegacao):
    # 1. Configurar os fusos horários
    fuso_utc = pytz.utc
    fuso_br = pytz.timezone('America/Sao_Paulo')
    
    agora_utc = datetime.now(fuso_utc)
    agora_br = agora_utc.astimezone(fuso_br)
    
    # 2. Formatar as strings
    fmt = "%d/%m/%Y %H:%M"
    str_br = agora_br.strftime(fmt)
    str_utc = agora_utc.strftime(fmt)

    # 3. Layout das colunas
    col1, col2 = st.columns([3, 1.5]) # Aumentei um pouco a col2 para caber a caixa
    
    with col1:
        logo_col, title_col = st.columns([1, 5])
        with logo_col:
            # Verifica se a imagem existe para não dar erro
            if os.path.exists("logo.png"):
                st.image("logo.png", width=70)
            else:
                st.write("🌐") # Placeholder se não tiver logo
        with title_col:
            st.title(f"Clima-Cast: {opcao_navegacao}")

    with col2:
        # 4. Criar a caixa HTML com as duas datas
        # O style define: borda cinza, cantos arredondados, padding e alinhamento
        html_box = f"""
        <div style='
            border: 1px solid #e6e6e6; 
            border-radius: 5px; 
            padding: 8px; 
            text-align: center; 
            font-family: sans-serif;
            background-color: rgba(255, 255, 255, 0.1);
        '>
            <div><b>🇧🇷 BRT:</b> {str_br}</div>
            <div style='color: grey; font-size: 0.9em;'><b>🌐 UTC:</b> {str_utc}</div>
        </div>
        """
        st.markdown(html_box, unsafe_allow_html=True)
    
    st.markdown("---")
    if "analysis_results" not in st.session_state and 'drawn_geometry' not in st.session_state:
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

import re

def renderizar_pagina_sobre():
    """
    Exibe o conteúdo do arquivo sobre.docx hospedado no GitHub,
    convertendo-o em HTML com as imagens embutidas (Base64), centralizadas
    e com tamanho controlado.
    """

    st.title("Sobre o Clima-Cast-Crepaldi")
    st.markdown("---")

    url_docx = "https://raw.githubusercontent.com/Crepaldi2025/dashboard_cat314/main/sobre.docx"
    temp_path = None
    
    try:
        # 1️⃣ Download temporário do arquivo DOCX
        with st.spinner("Carregando documento..."):
            response = requests.get(url_docx)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                tmp_docx.write(response.content)
                temp_path = tmp_docx.name

        # 2️⃣ Garantir que o Pandoc está disponível
        try:
            pypandoc.get_pandoc_version()
        except OSError:
            with st.spinner("🔧 Configurando o renderizador de documentos (Pandoc)..."):
                pypandoc.download_pandoc()

        # 3️⃣ Converter DOCX → HTML com imagens embutidas (Base64)
        html = pypandoc.convert_file(
            source_file=temp_path,
            to="html",
            format="docx",
            extra_args=[
                "--embed-resources"   # Converte imagens para Base64
            ]
        )

        html = re.sub(
            r'<img src="([^"]+)" alt="([^"]*)"[^>]*>', 
            # Em seguida, recria a tag <img> com nosso próprio style:
            # 1. Envolve em um <p> para centralizar.
            # 2. Define a largura máxima (max-width) para 700px.
            # 3. Define a largura (width) para 100% (para ser responsiva).
            # 4. Define a altura (height) para 'auto' (para manter a proporção).
            r"""
            <p style="text-align:center;">
                <img src="\1" alt="\2" style="max-width: 500px; width: 100%; height: auto;">
            </p>
            """,
            html
        )
        # =====================================================================

        # 5️⃣ Exibir conteúdo renderizado
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Erro ao carregar o arquivo sobre.docx: {e}")

    finally:
        # Limpa o arquivo temporário se ele foi criado
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass



