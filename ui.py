# ==================================================================================
# ui.py — Interface do usuário para o Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import datetime
import utils

# ==================================================================================
# Sidebar principal
# ==================================================================================
def render_sidebar():
    """Renderiza a barra lateral completa para controle da aplicação."""
    st.sidebar.title("🌦️ Clima-Cast-Crepaldi")
    st.sidebar.markdown("Selecione os parâmetros abaixo para gerar a análise.")
    st.sidebar.markdown("---")

    tipo_loc = st.sidebar.selectbox(
        "📍 Tipo de localização",
        ["Estado", "Município", "Círculo", "Polígono"]
    )
    st.session_state.tipo_localizacao = tipo_loc

    # -------------------------------------------------------
    # Estado
    # -------------------------------------------------------
    if tipo_loc == "Estado":
        estados = utils.listar_estados_brasil()
        uf_sigla = st.sidebar.selectbox("UF", estados)
        st.session_state.uf_sigla = uf_sigla

    # -------------------------------------------------------
    # Município
    # -------------------------------------------------------
    elif tipo_loc == "Município":
        estados = utils.listar_estados_brasil()
        uf_sigla = st.sidebar.selectbox("UF", estados)
        municipios = utils.listar_municipios_por_estado(uf_sigla)
        municipio_nome = st.sidebar.selectbox("Município", municipios)
        st.session_state.uf_sigla = uf_sigla
        st.session_state.municipio_nome = municipio_nome

    # -------------------------------------------------------
    # Círculo
    # -------------------------------------------------------
    elif tipo_loc == "Círculo":
        st.sidebar.markdown("Defina o **centro** e o **raio (km)**:")
        latitude = st.sidebar.number_input("Latitude (°)", value=-23.0, step=0.1)
        longitude = st.sidebar.number_input("Longitude (°)", value=-46.0, step=0.1)
        raio_km = st.sidebar.number_input("Raio (km)", value=50.0, step=1.0)
        st.session_state.latitude = latitude
        st.session_state.longitude = longitude
        st.session_state.raio_km = raio_km

    # -------------------------------------------------------
    # Polígono
    # -------------------------------------------------------
    elif tipo_loc == "Polígono":
        st.sidebar.info("🟦 O polígono deve ser desenhado no mapa principal.")

    st.sidebar.markdown("---")

    # -------------------------------------------------------
    # Variável meteorológica
    # -------------------------------------------------------
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

    st.sidebar.markdown("---")
    st.sidebar.caption("🗓️ Período de análise")

    start_date = st.sidebar.date_input("Data inicial", datetime.date(2024, 1, 1))
    end_date = st.sidebar.date_input("Data final", datetime.date(2024, 12, 31))

    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    st.sidebar.markdown("---")

    # -------------------------------------------------------
    # Botões
    # -------------------------------------------------------
    if st.sidebar.button("🚀 Gerar Análise"):
        st.session_state.analysis_triggered = True
        st.rerun()

    if st.sidebar.button("🧹 Limpar resultados"):
        reset_analysis_state()
        st.rerun()


# ==================================================================================
# Funções auxiliares
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
        "drawn_geometry",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
