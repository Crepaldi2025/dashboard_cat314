# ==================================================================================
# ui.py — Interface do Usuário do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st

# ==================================================================================
# BARRA LATERAL DE NAVEGAÇÃO
# ==================================================================================
def render_sidebar():
    """Renderiza a barra lateral de navegação do aplicativo."""
    st.sidebar.title("🌤️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("---")

    # Menu de navegação
    page = st.sidebar.radio(
        "Selecione a página:",
        ["Análise Completa", "Sobre"]
    )

    # Guarda a página selecionada no estado da sessão
    st.session_state.page = page

    st.sidebar.markdown("---")
    st.sidebar.caption("Desenvolvido por **P. C. Crepaldi** — Disciplina CAT314 / UNIFEI")

# ==================================================================================
# PÁGINA “SOBRE O APLICATIVO”
# ==================================================================================
def render_about_page():
    """Exibe o conteúdo da página 'Sobre o Aplicativo'."""
    st.title("🌤️ Sobre o Clima-Cast-Crepaldi")
    st.markdown("---")

    st.markdown(
        """
        O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido no âmbito da disciplina
        **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**,
        do curso de **Ciências Atmosféricas da Universidade Federal de Itajubá (UNIFEI)**.

        **Objetivo:** integrar dados meteorológicos provenientes de reanálises globais
        (como o **ERA5-Land**) e produtos de satélite do **Google Earth Engine**, 
        disponibilizando-os em uma plataforma **visual, dinâmica e acessível** para
        análises de variáveis atmosféricas em diferentes escalas.

        ---
        **Principais funcionalidades:**
        - Visualização interativa de mapas (precipitação, temperatura, vento etc.);
        - Seleção de áreas por município, círculo ou polígono;
        - Cálculo e exibição de estatísticas temporais;
        - Exportação de gráficos e tabelas.

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
        🔗 **Repositório no GitHub:**  
        [github.com/Crepaldi2025/dashboard_cat314](https://github.com/Crepaldi2025/dashboard_cat314)
        """
    )
