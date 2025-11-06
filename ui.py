# ==================================================================================
# ui.py — Interface do usuário para o Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import datetime
import utils

# ==================================================================================
# SIDEBAR PRINCIPAL
# ==================================================================================

def render_sidebar():
    """Renderiza a barra lateral com controles interativos."""
    st.sidebar.title("🌦️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("Selecione as opções abaixo para gerar a análise.")
    st.sidebar.markdown("---")

    # === Tipo de localização ===
    tipo_localizacao = st.sidebar.selectbox(
        "📍 Tipo de localização",
        ["Estado", "Município", "Círculo", "Polígono"]
    )
    st.session_state.tipo_localizacao = tipo_localizacao

    # ================================================================
    # OPÇÃO 1 — ESTADO
    # ================================================================
    if tipo_localizacao == "Estado":
        estados = utils.listar_estados_brasil()
        uf_sigla = st.sidebar.selectbox("UF", estados)
        st.session_state.uf_sigla = uf_sigla

    # ================================================================
    # OPÇÃO 2 — MUNICÍPIO
    # ================================================================
    elif tipo_localizacao == "Município":
        estados = utils.listar_estados_brasil()
        uf_sigla = st.sidebar.selectbox("UF", estados)
        municipios = utils.listar_municipios_por_estado(uf_sigla)
        municipio_nome = st.sidebar.selectbox("Município", municipios)
        st.session_state.uf_sigla = uf_sigla
        st.session_state.municipio_nome = municipio_nome

    # ================================================================
    # OPÇÃO 3 — CÍRCULO
    # ================================================================
    elif tipo_localizacao == "Círculo":
        st.sidebar.markdown("Defina o **centro** e o **raio** (em km):")
        latitude = st.sidebar.number_input("Latitude (°)", value=-23.0, step=0.1)
        longitude = st.sidebar.number_input("Longitude (°)", value=-46.0, step=0.1)
        raio_km = st.sidebar.number_input("Raio (km)", value=50.0, step=1.0)
        st.session_state.latitude = latitude
        st.session_state.longitude = longitude
        st.session_state.raio_km = raio_km

    # ================================================================
    # OPÇÃO 4 — POLÍGONO
    # ================================================================
    elif tipo_localizacao == "Polígono":
        st.sidebar.info("🟦 O polígono deve ser desenhado no mapa principal.")
        st.session_state.tipo_localizacao = "Polígono"

    st.sidebar.markdown("---")

    # ================================================================
    # VARIÁVEL METEOROLÓGICA
    # ================================================================
    variavel = st.sidebar.selectbox(
        "🌡️ Variável meteorológica",
        [
            "Temperatura do ar (°C)",
            "Precipitação (mm)",
            "Umidade do solo (%)",
            "Velocidade do vento (m/s)"
        ]
    )
    st.session_state.variavel = variavel

    # ================================================================
    # PERÍODO DE ANÁLISE
    # ================================================================
    st.sidebar.markdown("---")
    st.sidebar.caption("🗓️ Período de análise")

    start_date = st.sidebar.date_input(
        "Data inicial", value=datetime.date(2024, 1, 1)
    )
    end_date = st.sidebar.date_input(
        "Data final", value=datetime.date(2024, 12, 31)
    )

    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    st.sidebar.markdown("---")

    # ================================================================
    # BOTÕES DE CONTROLE
    # ================================================================
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🚀 Gerar Análise"):
            st.session_state.analysis_triggered = True
            st.rerun()
    with col2:
        if st.button("🧹 Limpar resultados"):
            reset_analysis_state()
            st.rerun()


# ==================================================================================
# FUNÇÕES AUXILIARES
# ==================================================================================

def obter_parametros_principais():
    """Retorna variável, datas de início e fim selecionadas."""
    return (
        st.session_state.get("variavel"),
        st.session_state.get("start_date"),
        st.session_state.get("end_date"),
    )


def reset_analysis_state():
    """Limpa variáveis do session_state de forma segura."""
    keys_to_clear = [
        "analysis_triggered",
        "ee_image_result",
        "df_timeseries_result",
        "static_map_urls",
        "uf_sigla",
        "municipio_nome",
        "latitude",
        "longitude",
        "raio_km",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
