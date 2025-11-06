# ==================================================================================
# ui.py — Interface do usuário para o Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import datetime

# ==================================================================================
# Sidebar principal
# ==================================================================================

def render_sidebar():
    """Exibe a barra lateral de controle do aplicativo."""
    st.sidebar.title("🌦️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("Selecione as opções abaixo para gerar a análise.")

    tipo_localizacao = st.sidebar.selectbox(
        "Tipo de localização",
        ["Estado", "Município", "Círculo", "Polígono"]
    )
    st.session_state.tipo_localizacao = tipo_localizacao

    variavel = st.sidebar.selectbox(
        "Variável meteorológica",
        ["Temperatura do ar (°C)", "Precipitação (mm)", "Umidade do solo (%)"]
    )
    st.session_state.variavel = variavel

    start_date = st.sidebar.date_input("Data inicial", datetime.date(2024, 1, 1))
    end_date = st.sidebar.date_input("Data final", datetime.date(2024, 12, 31))
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    st.sidebar.markdown("---")

    # === Atualização: botão para gerar análise ===
    if st.sidebar.button("🚀 Gerar Análise"):
        st.session_state.analysis_triggered = True
        st.rerun()

    # === Atualização: botão seguro para limpar resultados ===
    if st.sidebar.button("🧹 Limpar resultados"):
        reset_analysis_state()
        st.rerun()

# ==================================================================================
# Função auxiliar — parâmetros principais
# ==================================================================================

def obter_parametros_principais():
    """Retorna variável, datas de início e fim selecionadas."""
    return (
        st.session_state.get("variavel"),
        st.session_state.get("start_date"),
        st.session_state.get("end_date"),
    )

# ==================================================================================
# === Atualização: função de limpeza controlada do estado ===
# ==================================================================================

def reset_analysis_state():
    """Limpa variáveis do session_state de forma segura."""
    keys_to_clear = [
        "analysis_triggered",
        "ee_image_result",
        "df_timeseries_result",
        "static_map_urls",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
