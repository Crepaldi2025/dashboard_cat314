# ==================================================================================
# ui.py — Interface do Usuário do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st

# ==================================================================================
# BARRA LATERAL DE NAVEGAÇÃO
# ==================================================================================
def render_sidebar():
    """Renderiza a barra lateral de navegação principal."""
    st.sidebar.title("🌤️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("---")

    # Menu principal
    page = st.sidebar.radio(
        "Escolha a seção:",
        ["Mapas", "Séries Temporais", "Sobre"]
    )

    # Salva a página no estado da sessão
    st.session_state.page = page

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

        **Objetivo:** integrar dados meteorológicos provenientes de reanálises globais
        (como o **ERA5-Land**) e produtos de satélite do **Google Earth Engine**, 
        apresentando-os em uma plataforma **visual, dinâmica e acessível**.

        ---
        **Módulos principais:**
        - 🗺️ **Mapas** — visualização interativa e estática de variáveis climáticas;
        - 📈 **Séries Temporais** — análise e gráficos de tendência para áreas selecionadas;
        - ℹ️ **Sobre** — informações do projeto e autoria.

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
