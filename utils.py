# ==================================================================================
# utils.py — Funções utilitárias para o sistema Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import json
import os
from functools import lru_cache

# ==================================================================================
# FUNÇÕES DE LOCALIZAÇÃO GEOGRÁFICA
# ==================================================================================
@st.cache_data
def carregar_dados_geograficos():
    """Carrega o arquivo JSON com os estados e municípios (IBGE local)."""
    arquivo = "municipios_ibge.json"
    if not os.path.exists(arquivo):
        st.error("Arquivo 'municipios_ibge.json' não encontrado.")
        return {}, {}
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("municipios_por_uf", {}), data.get("nomes_estados", {})
    except Exception as e:
        st.error(f"Erro ao ler o arquivo de municípios: {e}")
        return {}, {}

def listar_estados_brasil():
    """Retorna uma lista de estados brasileiros formatada como 'Nome - UF'."""
    _, nomes_estados = carregar_dados_geograficos()
    return [f"{nome} - {uf}" for uf, nome in sorted(nomes_estados.items())]

def listar_municipios_por_estado(uf_sigla):
    """Retorna a lista de municípios de uma dada UF."""
    municipios_por_uf, _ = carregar_dados_geograficos()
    return sorted(municipios_por_uf.get(uf_sigla, []))

# ==================================================================================
# CONFIGURAÇÃO DAS VARIÁVEIS DO ERA5-LAND
# ==================================================================================
@lru_cache(maxsize=None)
def get_variable_config(variable):
    """Retorna o dicionário de configuração de visualização de cada variável."""
    ERA5_VARS = {
        "Temperatura do ar (°C)": {
            "band": "temperature_2m",
            "result_band": "temperature_2m",
            "unit": "°C",
            "aggregation": "mean",
            "vis_params": {
                "min": 0,
                "max": 40,
                "palette": [
                    "#000080", "#0000FF", "#00FFFF", "#00FF00",
                    "#FFFF00", "#FFA500", "#FF0000", "#800000"
                ]
            },
        },
        "Precipitação (mm)": {
            "band": "total_precipitation_sum",
            "result_band": "total_precipitation_sum",
            "unit": "mm",
            "aggregation": "sum",
            "vis_params": {
                "min": 0,
                "max": 500,
                "palette": [
                    "#FFFFFF", "#00FFFF", "#0000FF",
                    "#00FF00", "#FFFF00", "#FF0000"
                ],
            },
        },
        "Umidade do solo (%)": {
            "band": "volumetric_soil_water_layer_1",
            "result_band": "volumetric_soil_water_layer_1",
            "unit": "%",
            "aggregation": "mean",
            "vis_params": {
                "min": 0,
                "max": 100,
                "palette": [
                    "#f7fcf0", "#ccebc5", "#7bccc4",
                    "#2b8cbe", "#08589e"
                ],
            },
        },
    }

    return ERA5_VARS.get(variable, {})

# ==================================================================================
# AUXILIARES GERAIS
# ==================================================================================
def validar_datas(start_date, end_date):
    """Valida intervalo de datas e emite alerta se inválido."""
    if start_date > end_date:
        st.error("A data inicial deve ser anterior à data final.")
        return False
    return True

def get_geo_params_from_state(session_state):
    """Extrai parâmetros simples da área de interesse para cache."""
    return {
        "tipo": session_state.get("tipo_localizacao"),
        "uf": session_state.get("uf_sigla"),
        "municipio": session_state.get("municipio_nome"),
        "latitude": session_state.get("latitude"),
        "longitude": session_state.get("longitude"),
        "raio_km": session_state.get("raio"),
    }

# ==================================================================================
# === FIM ===
# ==================================================================================
