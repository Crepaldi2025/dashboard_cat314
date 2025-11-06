# ==================================================================================
# utils.py — Funções utilitárias do sistema Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import geobr
import datetime
import pandas as pd
import ee

# ==================================================================================
# FUNÇÕES DE LOCALIZAÇÃO GEOGRÁFICA
# ==================================================================================

@st.cache_data
def listar_estados_brasil():
    """Retorna lista de siglas de estados brasileiros (ordenada)."""
    try:
        estados_gdf = geobr.read_state()
        siglas = sorted(estados_gdf["abbrev_state"].unique().tolist())
        return siglas
    except Exception as e:
        st.error(f"Erro ao carregar lista de estados: {e}")
        return []

@st.cache_data
def listar_municipios_por_estado(uf_sigla):
    """Retorna lista de municípios de um determinado estado."""
    try:
        municipios_gdf = geobr.read_municipality(code_muni=uf_sigla, year=2020)
        nomes = sorted(municipios_gdf["name_muni"].unique().tolist())
        return nomes
    except Exception as e:
        st.error(f"Erro ao carregar municípios de {uf_sigla}: {e}")
        return []

# ==================================================================================
# FUNÇÕES DE SUPORTE AO GOOGLE EARTH ENGINE
# ==================================================================================

def ee_initialize():
    """Inicializa o Earth Engine, se ainda não estiver inicializado."""
    try:
        ee.Initialize()
    except Exception:
        try:
            ee.Authenticate()
            ee.Initialize()
        except Exception as e:
            st.error(f"Falha ao inicializar o Google Earth Engine: {e}")

# ==================================================================================
# CONVERSÕES E AJUSTES DE DADOS
# ==================================================================================

def converter_data_para_str(data):
    """Converte datetime/date em string compatível com GEE (YYYY-MM-DD)."""
    if isinstance(data, datetime.date):
        return data.strftime("%Y-%m-%d")
    return str(data)

def filtrar_periodo(df, start_date, end_date, coluna="data"):
    """Filtra um DataFrame entre duas datas."""
    try:
        df[coluna] = pd.to_datetime(df[coluna])
        mask = (df[coluna] >= pd.to_datetime(start_date)) & (df[coluna] <= pd.to_datetime(end_date))
        return df.loc[mask]
    except Exception as e:
        st.warning(f"Erro ao filtrar período: {e}")
        return df

# ==================================================================================
# CONFIGURAÇÕES DE VARIÁVEIS METEOROLÓGICAS
# ==================================================================================

ERA5_VARS = {
    "Temperatura do ar (°C)": {
        "band": "temperature_2m",
        "vis_params": {"min": 0, "max": 40, "palette": ["#313695", "#74add1", "#fed976", "#f46d43", "#a50026"]},
        "unit": "°C",
    },
    "Precipitação (mm)": {
        "band": "total_precipitation_sum",
        "vis_params": {"min": 0, "max": 300, "palette": ["#FFFFFF", "#ADD8E6", "#0000FF", "#800080"]},
        "unit": "mm",
    },
    "Umidade do solo (%)": {
        "band": "volumetric_soil_water_layer_1",
        "vis_params": {"min": 0, "max": 100, "palette": ["#f7fcf0", "#00441b"]},
        "unit": "%",
    },
    "Velocidade do vento (m/s)": {
        "band": "wind_speed",
        "vis_params": {"min": 0, "max": 30, "palette": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]},
        "unit": "m/s",
    },
}

def get_variable_config(variavel):
    """Retorna as configurações de uma variável meteorológica do ERA5-Land."""
    return ERA5_VARS.get(variavel, None)

# ==================================================================================
# GEOMETRIA AUXILIAR
# ==================================================================================

def criar_circulo(lat, lon, raio_km):
    """Cria uma geometria circular (buffer) em torno de um ponto."""
    try:
        ponto = ee.Geometry.Point([lon, lat])
        circulo = ponto.buffer(raio_km * 1000)
        return circulo
    except Exception as e:
        st.error(f"Erro ao criar círculo: {e}")
        return None

# ==================================================================================
# FORMATAÇÃO E EXIBIÇÃO
# ==================================================================================

def formatar_titulo(variavel, nome_local, data_inicial, data_final):
    """Gera título formatado para gráficos e mapas."""
    try:
        return f"{variavel} — {nome_local} ({data_inicial} a {data_final})"
    except Exception:
        return variavel

# ==================================================================================
# VERIFICAÇÃO DE AMBIENTE
# ==================================================================================

def verificar_ambiente():
    """Exibe mensagem útil para depuração (local x Streamlit Cloud)."""
    import platform
    st.sidebar.info(
        f"🖥️ Ambiente: {platform.system()} — Python {platform.python_version()}"
    )
