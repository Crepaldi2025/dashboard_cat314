# ==================================================================================
# ui.py — Interface do usuário do sistema Clima-Cast-Crepaldi (Corrigido)
# ==================================================================================

import streamlit as st
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import locale

# ==================================================================================
# CONFIGURAÇÃO INICIAL (DEVE VIR ANTES DE QUALQUER OUTRA CHAMADA STREAMLIT)
# ==================================================================================

st.set_page_config(
    page_title="Clima-Cast-Crepaldi",
    #page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Protege contra erro de locale no Streamlit Cloud
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "C") # Fallback
    except Exception:
        pass # Se tudo falhar, usa o padrão

# ==================================================================================
# FUNÇÕES PRINCIPAIS
# ==================================================================================

def configurar_pagina():
#   """Configura o título e separador inicial."""
#   st.title("Clima-Cast-Crepaldi") # Descomentado em main.py
    st.markdown("---")

# ----------------------------------------------------------------------------------
# CORREÇÃO P2: Lógica de Estado
# Esta função é a chave para o P2. Ela limpa o 'gatilho' e os 'resultados'.
# Quando um filtro é alterado, a análise anterior é invalidada.
# ----------------------------------------------------------------------------------
def reset_analysis_state():
    """Callback para limpar o estado dos resultados sempre que um filtro é alterado."""
    keys_to_clear = [
        'analysis_triggered',   # O gatilho para rodar a análise
        'analysis_results',     # Onde os resultados (mapas, dfs) são guardados
        'drawn_geometry'        # Limpa o polígono desenhado
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # st.rerun() # Opcional, mas pode ser bom para limpar a UI
    

def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    """Cria a barra lateral com os filtros."""
    with st.sidebar:
        st.header("Painel de Controle")

        # 1. NAVEGAÇÃO
        st.radio(
            "Navegação",
            ["Mapas", "Séries Temporais", "Sobre o Aplicativo"],
            label_visibility="collapsed",
            key='nav_option',
            on_change=reset_analysis_state # Limpa a análise ao trocar de aba
        )
        st.markdown("---")
        opcao_selecionada = st.session_state.get('nav_option', 'Mapas')

        if opcao_selecionada in ["Mapas", "Séries Temporais"]:
            st.markdown("<p style='text-align: center;'>Selecione os filtros abaixo para gerar os dados.</p>", unsafe_allow_html=True)
            
            # 2. BASE DE DADOS
            st.subheader("1. Base de Dados")
            st.selectbox("Selecione a Base de Dados", ["ERA5-LAND"], key='base_de_dados', on_change=reset_analysis_state)
            st.divider()

            # 3. VARIÁVEL
            st.subheader("2. Variável Meteorológica")
            st.selectbox("Selecione a Variável", ["Temperatura do Ar (2m)", "Precipitação Total", "Velocidade do Vento (10m)"], key='variavel', on_change=reset_analysis_state)
            st.divider()

            # 4. LOCALIZAÇÃO
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
                    # Garante que dados_geo[uf_selecionada] existe
                    lista_municipios = ["Selecione..."] + dados_geo.get(uf_selecionada, [])
                st.selectbox("Selecione o Município", lista_municipios, key='municipio', on_change=reset_analysis_state)
            elif tipo_localizacao == "Círculo (Lat/Lon/Raio)":
                st.number_input("Latitude", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                st.number_input("Longitude", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
            elif tipo_localizacao == "Polígono":
                # A lógica de desenho agora fica em main.py
                st.info("Acesse a aba 'Mapas' para desenhar seu polígono de interesse.")
                if st.session_state.get('drawn_geometry'):
                    st.success("✅ Polígono desenhado e capturado.")
            st.divider()

            # 5. PERÍODO
            st.subheader("4. Período de Análise")
            
            if opcao_selecionada == "Mapas":
                st.selectbox("Selecione o tipo de período", ["Personalizado", "Mensal", "Anual"], key='tipo_periodo', on_change=reset_analysis_state)
            else:
                # Séries temporais são sempre personalizadas
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_periodo = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1979, -1)) # ERA5 começa em 1981, mas 1979 é seguro

            st.session_state.date_error = False
            if tipo_periodo == "Personalizado":
                hoje = datetime.now()
                # Datas padrão mais sensatas (ex: último mês)
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

            # 6. TIPO DE MAPA (Se aplicável)
            if opcao_selecionada == "Mapas":
                st.subheader("5. Tipo de Mapa")
                st.radio("Selecione o formato", ["Interativo", "Estático"], key='map_type', horizontal=True, on_change=reset_analysis_state)
                st.divider()

            # ----------------------------------------------------------------------
            # CORREÇÃO P7: Botão de Análise (Lógica de "disabled")
            # ----------------------------------------------------------------------
            disable_button = st.session_state.get('date_error', False)
            tooltip_message = "Clique para gerar a análise"

            if tipo_localizacao == "Polígono":
                if not st.session_state.get('drawn_geometry'):
                    disable_button = True
                    tooltip_message = "Por favor, desenhe um polígono no mapa principal primeiro."
                if opcao_selecionada != "Mapas":
                     st.warning("O desenho de polígono só está disponível na aba 'Mapas'.")
                     disable_button = True

            if st.button("Gerar Análise", 
                          type="primary", 
                          use_container_width=True, 
                          disabled=disable_button,
                          help=tooltip_message):
                
                st.session_state.analysis_triggered = True
                st.rerun()

        
        return opcao_selecionada


def renderizar_pagina_principal(opcao_navegacao):
    """Exibe o conteúdo da página principal com o logo."""
    agora = datetime.now()
    data_hora_formatada = agora.strftime("%d/%m/%Y, %H:%M:%S")

    col1, col2 = st.columns([3, 1])
    with col1:
        logo_col, title_col = st.columns([1, 5])
        with logo_col:
            st.image("logo.png", width=70) # Assume que 'logo.png' está na pasta raiz
        with title_col:
            st.title(f"Clima-Cast-Crepaldi: {opcao_navegacao}")

    with col2:
        st.write("")
        st.markdown(f"<p style='text-align: right; color: grey;'>{data_hora_formatada}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("Configure sua análise no **Painel de Controle** à esquerda e clique em **Gerar Análise** para exibir os resultados aqui.")


def renderizar_resumo_selecao():
    """Mostra um resumo dos filtros selecionados."""
    # Envolve em um expander para não poluir a tela
    with st.expander("Resumo dos Filtros Utilizados", expanded=False):
        col_resumo1, col_resumo2 = st.columns(2)
        
        # Bloco de try...except para evitar falhas se o estado for limpo
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
            # Ocorre se o estado for limpo (ex: reset_analysis_state)
            st.warning("Filtros foram redefinidos. Por favor, selecione novamente.")


# ----------------------------------------------------------------------------------
# CORREÇÃO P6 (Código Morto):
# A função 'renderizar_validacao_mapa' foi removida.
# Ela não era chamada e seu fluxo foi substituído pelo novo P2/P7.
# ----------------------------------------------------------------------------------


def renderizar_pagina_sobre():
    # ------------------------------------------------------------------------------
    # CORREÇÃO P6/Bug: O código solto (imports, funções) foi removido daqui
    # e movido/deletado corretamente.
    # ------------------------------------------------------------------------------

    # Texto introdutório
    st.markdown("""
    O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido no âmbito da disciplina  
    **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**, do curso de **Ciências Atmosféricas da Universidade Federal de Itajubá (UNIFEI)**.  
    Seu propósito é **integrar dados meteorológicos de reanálises globais** e disponibilizá-los em uma plataforma visual, dinâmica e acessível, 
    favorecendo tanto a **análise científica** quanto o **uso didático**.
    """)

    # Objetivo
    st.markdown("<div class='subtitulo'> Objetivo</div>", unsafe_allow_html=True)
    st.markdown("""
    O sistema tem como principal objetivo **proporcionar uma interface intuitiva e interativa** para consulta, análise e visualização 
    de dados meteorológicos históricos dos municípios brasileiros, utilizando a base **ERA5-Land**, disponibilizada pelo  
    **European Centre for Medium-Range Weather Forecasts (ECMWF)** por meio da plataforma **Google Earth Engine (GEE)**.

    Além disso, o aplicativo busca:
    - Apoiar o aprendizado prático em técnicas de análise e visualização de dados meteorológicos;
    - Facilitar a **análise espaço-temporal** de variáveis como temperatura, precipitação e vento;
    - Demonstrar a **aplicabilidade de ferramentas computacionais ** na climatologia operacional.
    """)

    # Metodologia
    st.markdown("<div class='subtitulo'> Metodologia e Funcionamento</div>", unsafe_allow_html=True)
    st.markdown("""
    O dashboard permite ao usuário selecionar:
    - A **variável meteorológica** de interesse (*temperatura, precipitação ou vento*);
    - O **tipo de área de estudo** (*Estado, Município, Círculo ou Polígono*);
    - O **intervalo temporal** (*personalizado, mensal ou anual*).

    Após a seleção, o sistema acessa os dados do **ERA5-Land via GEE**, aplica a **agregação estatística apropriada** (média ou soma) 
    e exibe os resultados em diferentes formas:
    - **Mapas interativos** com *geemap* e *folium*;
    - **Mapas estáticos** com *matplotlib*;
    - **Séries temporais interativas** com *plotly.express*.

    Os resultados podem ser **exportados** em formatos **CSV**, **XLSX** e **PNG**, permitindo o reuso em relatórios e análises externas.
    """)

    # Tecnologias
    st.markdown("<div class='subtitulo'> Tecnologias Utilizadas</div>", unsafe_allow_html=True)
    st.markdown("""
    | Categoria | Ferramenta / Tecnologia | Função |
    |------------|-------------------------|---------|
    | **Linguagem de Programação** | Python | Desenvolvimento principal e integração entre módulos |
    | **Framework de Interface** | Streamlit | Criação da interface interativa (dashboard web) |
    | **Plataforma Geoespacial** | Google Earth Engine (GEE) | Acesso e processamento de dados climáticos e geográficos |
    | **Visualização** | Geemap, Folium, Streamlit-Folium, Matplotlib, Plotly | Criação de mapas e gráficos interativos |
    | **Fonte de Dados Meteorológicos** | ERA5-Land (ECMWF) | Reanálise global de alta resolução (~9 km) |
    | **Geometrias Territoriais** | Geobr | Fronteiras oficiais de estados e municípios brasileiros |
    """, unsafe_allow_html=True)

    # Fonte dos Dados
    st.markdown("<div class='subtitulo'> Fonte dos Dados</div>", unsafe_allow_html=True)
    st.markdown("""
    Os dados utilizados provêm do produto **ERA5-Land Daily Aggregated**, mantido pelo **ECMWF (European Centre for Medium-Range Weather Forecasts)** e disponibilizado no **Google Earth Engine (GEE)**.  
    Esse conjunto de dados fornece **estimativas diárias de variáveis meteorológicas de superfície** com resolução espacial de **0,1° (~9 km)**, 
    cobrindo o período de **1950 até o presente**.  
    A confiabilidade e consistência do ERA5-Land o tornam uma referência para **estudos climáticos e hidrometeorológicos**.
    """)

    # Rodapé
    st.markdown("<hr class='divisor'>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray;font-size:12px;'>Desenvolvido por Paulo C. Crepaldi – CAT314 / UNIFEI</p>", unsafe_allow_html=True)