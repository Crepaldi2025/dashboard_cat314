import streamlit as st

def configurar_pagina():
    """
    Configura o título da página, o ícone e o layout.
    Esta função é chamada uma única vez no início da execução.
    """
    st.set_page_config(
        page_title="Dashboard Meteorológico do Brasil",
        page_icon="☁️",  # Ícone de nuvem, como solicitado
        layout="wide",
        initial_sidebar_state="expanded"
    )

def renderizar_sidebar():
    """
    Cria e exibe a barra lateral com os filtros e opções para o usuário.
    """
    with st.sidebar:
        st.header("Painel de Controle")
        st.info("Selecione os filtros abaixo para gerar os mapas e séries temporais.")

        # --- Filtros de Localização (ainda não funcionais) ---
        st.subheader("📍 Localização")
        estado = st.selectbox("Selecione o Estado", ["Carregando..."])
        municipio = st.selectbox("Selecione o Município", ["Selecione um estado primeiro"])

        # --- Filtro de Data (ainda não funcional) ---
        st.subheader("📅 Período de Análise")
        data_inicio = st.date_input("Data de Início")
        data_fim = st.date_input("Data de Fim")

        # --- Filtro de Variável (ainda não funcional) ---
        st.subheader("🛰️ Variável Meteorológica")
        variavel = st.selectbox("Selecione a Variável", [
            "Temperatura do Ar (2m)",
            "Precipitação Total",
            "Velocidade do Vento (10m)"
        ])

        st.divider()

        # Botão para executar a análise
        if st.button("Gerar Análise", type="primary"):
            # Lógica a ser implementada futuramente
            st.success("Análise em andamento!")
        
        st.markdown("""
        ---
        **Desenvolvido para a disciplina CAT314.**
        """)

def renderizar_pagina_principal():
    """
    Exibe o título principal e a introdução na área de conteúdo principal.
    """
    st.title("Dashboard de Monitoramento Meteorológico para o Brasil")
    st.markdown("""
    Utilize o **Painel de Controle** na barra à esquerda para selecionar a localização, 
    o período de análise e a variável meteorológica de interesse. Os resultados
    serão exibidos nesta área principal.
    """)