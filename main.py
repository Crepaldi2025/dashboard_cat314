# ==================================================================================
# utils.py — Funções auxiliares para interface e dados geográficos
# ==================================================================================
import streamlit as st
import geobr

# ==================================================================================
# LISTAR ESTADOS
# ==================================================================================
@st.cache_data
def listar_estados_brasil():
    """Retorna lista de siglas dos estados brasileiros (ordenada)."""
    try:
        estados_gdf = geobr.read_state()
        siglas = sorted(estados_gdf["abbrev_state"].unique().tolist())
        return siglas
    except Exception as e:
        st.error(f"Erro ao carregar lista de estados: {e}")
        return []

# ==================================================================================
# LISTAR MUNICÍPIOS POR UF
# ==================================================================================
@st.cache_data
def listar_municipios_por_estado(uf_sigla):
    """Retorna lista de municípios do estado informado."""
    try:
        municipios_gdf = geobr.read_municipality(code_muni=uf_sigla, year=2020)
        nomes = sorted(municipios_gdf["name_muni"].unique().tolist())
        return nomes
    except Exception as e:
        st.error(f"Erro ao carregar municípios de {uf_sigla}: {e}")
        return []
