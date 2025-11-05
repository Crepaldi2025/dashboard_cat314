# ==================================================================================
# ui.py — Interface do Usuário do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st

# ==================================================================================
# BARRA LATERAL COMPLETA
# ==================================================================================
def render_sidebar():
    """Renderiza a barra lateral com todas as opções de navegação e filtros."""
    st.sidebar.title("🌤️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("---")

    # ------------------------------------------------------------
    # 1. Menu principal (nível 1)
    # ------------------------------------------------------------
    main_page = st.sidebar.radio(
        "Selecione o módulo:",
        ["Mapas", "Séries Temporais", "Sobre"]
    )
    st.session_state.page = main_page

    st.sidebar.markdown("---")

    # ------------------------------------------------------------
    # 2. Subopções para MAPAS
    # ------------------------------------------------------------
    if main_page == "Mapas":
        st.sidebar.subheader("🗺️ Configurações de Mapas")

        st.session_state.tipo_area = st.sidebar.selectbox(
            "Tipo de área:",
            ["Município", "Estado", "Polígono", "Círculo"]
        )

        st.session_state.tipo_variavel = st.sidebar.selectbox(
            "Variável meteorológica:",
            ["Precipitação", "Temperatura Média", "Temperatura Máxima", "Temperatura Mínima", "Umidade do Solo"]
        )

        st.session_state.tipo_periodo = st.sidebar.selectbox(
            "Período de análise:",
            ["Mensal", "Sazonal", "Anual", "Personalizado"]
        )

        if st.session_state.tipo_periodo == "Personalizado":
            st.sidebar.date_input("Data inicial:")
            st.sidebar.date_input("Data final:")

        st.sidebar.markdown("---")
        st.sidebar.info("Após ajustar as opções, retorne à aba principal para gerar os mapas.")

    # ------------------------------------------------------------
    # 3. Subopções para SÉRIES TEMPORAIS
    # ------------------------------------------------------------
    elif main_page == "Séries Temporais":
        st.sidebar.subheader("📈 Configurações de Séries Temporais")

        st.session_state.tipo_area = st.sidebar.selectbox(
            "Tipo de área:",
            ["Município", "Estado", "Polígono", "Círculo"]
        )

        st.session_state.tipo_variavel = st.sidebar.selectbox(
            "Variável meteorológica:",
            ["Precipitação", "Temperatura Média", "Temperatura Máxima", "Temperatura Mínima", "Umidade do Solo"]
        )

        st.session_state.periodo_series = st.sidebar.selectbox(
            "Escala temporal:",
            ["Diário", "Mensal", "Sazonal", "Anual"]
        )

        st.sidebar.markdown("---")
        st.sidebar.info("As séries são calculadas com base na área e variável selecionadas.")

    # ------------------------------------------------------------
    # 4. Página SOBRE (sem subopções)
    # ------------------------------------------------------------
    elif main_page == "Sobre":
        pass

    st.sidebar.markdown("---")
    st.sidebar.caption("Desenvolvido por **P. C. Crepaldi** — Disciplina CAT314 / UNIFEI")

# ==================================================================================
# PÁGINA “SOBRE”
# ==================================================================================
def render_about_page():
    """Exibe o conteúdo da página 'Sobre o Aplicativo'."""
    st.title("🌤️ Sobre o Clima-Cast-Crepaldi")
    st.markdown("---")

    st.markdown(
        """
        O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido na disciplina
        **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**,
        do curso de **Ciências Atmosféricas da Universidade Federal de Itajubá (UNIFEI)**.

        ---
        **Módulos principais:**
        - 🗺️ *Mapas*: visualização interativa e estática de variáveis climáticas;
        - 📈 *Séries Temporais*: análise estatística e tendências;
        - ℹ️ *Sobre*: informações institucionais e autoria.

        ---
        **Orientador:** Prof. Enrique Vieira Mattos  
        **Desenvolvedor:** Paulo César Crepaldi  
        **Instituição:** Instituto de Recursos Naturais – UNIFEI  
        **Ano:** 2025
        """
    )

    st.info("Versão atual: *v2.0 — compatível com o Streamlit Cloud*")

    st.markdown("---")
    st.markdown(
        """
        🔗 **Repositório GitHub:**  
        [github.com/Crepaldi2025/dashboard_cat314](https://github.com/Crepaldi2025/dashboard_cat314)
        """
    )
