# ==================================================================================
# gee_handler.py — (Versão Completa e Corrigida v57)
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd
from datetime import date 

# ==========================================================
# INICIALIZAÇÃO E AUTENTICAÇÃO
# ==========================================================
def inicializar_gee():
    """
    Inicializa a API do Google Earth Engine.
    """
    try:
        ee.Image.constant(0).getInfo()
    except ee.EEException:
        try:
            if "earthengine_service_account" in st.secrets:
                service_account = st.secrets["earthengine_service_account"]["client_email"]
                private_key = st.secrets["earthengine_service_account"]["private_key"]
                credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
                ee.Initialize(credentials=credentials)
                st.info("✅ Conectado ao Google Earth Engine (Service Account).")
            else:
                ee.Initialize()
                st.info("✅ Conectado ao Google Earth Engine (Credenciais Locais).")
        except Exception as e:
            st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")
            st.warning("O aplicativo não funcionará sem a conexão GEE.")

def initialize_gee():
    """Alias de compatibilidade."""
    return inicializar_gee()

# ==========================================================
# DEFINIÇÕES DE VARIÁVEIS
# ==========================================================

ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m", 
        "result_band": "temperature_2m", 
        "unit": "°C", 
        "aggregation": "mean",
        "vis_params": { 
            "min": 0, 
            "max": 40, 
            "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'] 
        }
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum", 
        "result_band": "total_precipitation_sum", 
        "unit": "mm", 
        "aggregation": "sum",
        "vis_params": { 
            "min": 0, 
            "max": 500,
            "palette": ['#ffffd9', '#edf8b1', '#c7e9b4', '#7fcdbb', '#41b6c4', '#1d91c0', '#225ea8', '#253494', '#081d58', '#081040']
        }
    },
    # --- CORREÇÃO AQUI: O nome da banda estava invertido ---
    "Temperatura do Ponto de Orvalho (2m)": {
        "band": "dewpoint_temperature_2m", # Corrigido de 'dewpoint_2m_temperature'
        "result_band": "dewpoint_temperature_2m", # Corrigido
        "unit": "°C", 
        "scale_factor": 1.0, 
        "offset": -273.15, 
        "aggregation": "mean",
        "vis_params": { 
            "min": 5, 
            "max": 35, 
            "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'] 
        }
    },
    # -------------------------------------------------------
    "Umidade Relativa (2m)": {
        "bands": ["temperature_2m", "dewpoint_temperature_2m"], 
        "result_band": "relative_humidity", 
        "unit": "%", 
        "aggregation": "mean", 
        "vis_params": { 
            "min": 0, 
            "max": 100, 
            "palette": ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026']
        }
    },
    "Radiação Solar Incidente": {
        "band": "surface_solar_radiation_downwards_sum", 
        "result_band": "radiation_wm2", 
        "unit": "W/m²", 
        "aggregation": "mean", 
        "vis_params": { 
            "min": 0, 
            "max": 1000, 
            "palette": ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026']
        }
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'], 
        "result_band": "wind_speed", 
        "unit": "m/s", 
        "aggregation": "mean",
        "vis_params": { 
            "min": 0, 
            "max": 30,
            "palette": ['#440154', '#482878', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6dcd59', '#b4de2c', '#fde725']
        }
    }
}

# ==========================================================
# CARREGAMENTO DE DADOS GEOGRÁFICOS (Helpers)
# ==========================================================

@st.cache_data
def get_brazilian_geopolitical_data_local() -> tuple[dict, dict]:
    arquivo = "municipios_ibge.json"
    geo_data = defaultdict(list)
    uf_name_map = {}

    try:
        if not os.path.exists(arquivo):
            return {}, {}
        with open(arquivo, 'r', encoding='utf-8') as f:
            municipios_data = json.load(f)
        
        if isinstance(municipios_data, list): 
            for municipio in municipios_data:
                microrregiao = municipio.get('microrregiao')
                if microrregiao:
                    mesorregiao = microrregiao.get('mesorregiao')
                    if mesorregiao:
                        uf_data = mesorregiao.get('UF')
                        if uf_data:
                            uf_sigla = uf_data.get('sigla')
                            uf_nome = uf_data.get('nome')
                            if uf_sigla and uf_nome: uf_name_map[uf_sigla] = uf_nome
                            nome = municipio.get('nome')
                            if uf_sigla and nome: geo_data[uf_sigla].append(nome)
        elif isinstance(municipios_data, dict):
            geo_data = municipios_data.get("municipios_por_uf", {})
            uf_name_map = municipios_data.get("nomes_estados", {})

        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data.keys())}
        return sorted_geo_data, uf_name_map

    except Exception:
        return {}, {}

@st.cache_data
def _load_all_states_gdf():
    try: return geobr.read_state()
    except Exception: return None

@st.cache_data
def _load_municipalities_gdf(uf_sigla: str):
    try: return geobr.read_municipality(code_muni=uf_sigla, year=2020)
    except Exception: return None

# ==========================================================
# FUNÇÕES DE INTERFACE COM O MAIN.PY
# ==========================================================

def get_brazil_state(uf_sigla):
    """Retorna FeatureCollection e nome do estado."""
    todos = _load_all_states_gdf()
    if todos is None: return None, None
    st_gdf = todos[todos['abbrev_state'] == uf_sigla]
    if st_gdf.empty: return None, None
    
    json_geom = json.loads(st_gdf.to_json())['features'][0]['geometry']
    ee_geom = ee.Geometry(json_geom)
    ee_feat = ee.Feature(ee_geom, {'abbrev_state': uf_sigla})
    return ee.FeatureCollection([ee_feat]), f"Estado de {uf_sigla}"

def get_brazil_municipality(uf_sigla, municipio_nome):
    """Retorna FeatureCollection e nome do município."""
    mun_gdf = _load_municipalities_gdf(uf_sigla)
    if mun_gdf is None: return None, None
    
    row = mun_gdf[mun_gdf['name_muni'] == municipio_nome]
    if row.empty: return None, None
    
    json_geom = json.loads(row.to_json())['features'][0]['geometry']
    ee_geom = ee.Geometry(json_geom)
    ee_feat = ee.Feature(ee_geom, {'name_muni': municipio_nome, 'uf': uf_sigla})
    return ee.FeatureCollection([ee_feat]), f"{municipio_nome} - {uf_sigla}"

def convert_geojson_to_ee(geojson_dict):
    """Converte GeoJSON de desenho para FeatureCollection."""
    if not geojson_dict: return None
    geom = ee.Geometry(geojson_dict)
    return ee.FeatureCollection([ee.Feature(geom)])

def get_variable_params(variavel_nome):
    """Retorna parâmetros da variável para o main.py."""
    if variavel_nome not in ERA5_VARS:
        # Tenta encontrar correspondência parcial se falhar
        for k in ERA5_VARS.keys():
            if variavel_nome in k:
                variavel_nome = k
                break
        else:
            return None, None, None

    conf = ERA5_VARS[variavel_nome]
    # Dataset ID é fixo, 'band' aqui usamos como a chave para get_gee_image
    return "ECMWF/ERA5_LAND/DAILY_AGGR", variavel_nome, conf['unit']

def get_gee_time_series_function(variavel_nome):
    if variavel_nome in ERA5_VARS:
        return ERA5_VARS[variavel_nome].get('aggregation', 'mean')
    return 'mean'

def get_area_of_interest_geometry(session_state):
    """Helper legado/backup para obter geometria do session_state."""
    tipo = session_state.get('tipo_localizacao')
    if tipo == "Estado":
        uf = session_state.get('estado', '').split(' - ')[-1]
        fc, _ = get_brazil_state(uf)
        if fc: return fc.geometry(), fc.first()
    elif tipo == "Município":
        uf = session_state.get('estado', '').split(' - ')[-1]
        mun = session_state.get('municipio')
        fc, _ = get_brazil_municipality(uf, mun)
        if fc: return fc.geometry(), fc.first()
    elif tipo == "Círculo (Lat/Lon/Raio)":
        lat = session_state.get('latitude')
        lon = session_state.get('longitude')
        raio = session_state.get('raio')
        pt = ee.Geometry.Point([lon, lat])
        buff = pt.buffer(raio * 1000)
        return buff, ee.Feature(buff)
    return None, None

# ==========================================================
# PROCESSAMENTO PRINCIPAL
# ==========================================================

def _calculate_rh(image):
    T = image.select('temperature_2m').subtract(273.15) 
    Td = image.select('dewpoint_temperature_2m').subtract(273.15)
    es = T.multiply(17.625).divide(T.add(243.04)).exp().multiply(6.11)
    e = Td.multiply(17.625).divide(Td.add(243.04)).exp().multiply(6.11)
    rh = e.divide(es).multiply(100).rename('relative_humidity')
    return image.addBands(rh.min(ee.Image.constant(100)))

def _calculate_radiation(image):
    w_m2 = image.select('surface_solar_radiation_downwards_sum').divide(86400).rename('radiation_wm2')
    return image.addBands(w_m2)

def get_gee_image(dataset, variable_key, start_date, end_date):
    """
    Wrapper principal chamado pelo main.py para obter a imagem visualizável.
    variable_key: é a chave do dicionário ERA5_VARS (ex: "Temperatura do Ar (2m)")
    """
    if variable_key not in ERA5_VARS: return None, None
    config = ERA5_VARS[variable_key]
    
    bands_to_select = config.get('bands', config.get('band'))
    
    image_collection = (
        ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
        .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        .select(bands_to_select)
    )
    
    # Cálculos específicos
    if "Vento" in variable_key:
        def calc_wind(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
            return img.addBands(ws)
        image_collection = image_collection.map(calc_wind)
    elif "Umidade" in variable_key:
        image_collection = image_collection.map(_calculate_rh)
    elif "Radiação" in variable_key:
        image_collection = image_collection.map(_calculate_radiation)

    # Agregação Temporal
    result_band = config['result_band']
    if config['aggregation'] == 'sum':
        img_agg = image_collection.select(result_band).sum()
    else:
        img_agg = image_collection.select(result_band).mean()

    # Conversão de Unidade
    final_image = img_agg
    if config['unit'] == "°C": 
        final_image = final_image.subtract(273.15)
    elif config['unit'] == "mm": 
        final_image = final_image.multiply(1000)
    
    # Retorna imagem e parâmetros de visualização
    vis = config.get('vis_params', {}).copy()
    vis['variable_label'] = variable_key
    
    return final_image, vis

def extract_time_series_for_feature(dataset, band, start_date, end_date, feature, aggregate_func):
    """Wrapper para extrair série temporal."""
    # 'band' aqui vem como o nome da variável (variable_key)
    return get_time_series_data(band, start_date, end_date, feature.geometry())

def get_time_series_data(variable_key, start_date, end_date, geometry):
    if variable_key not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable_key]
    
    bands_to_select = config.get("bands", config.get("band"))
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(bands_to_select)
    )

    if "Vento" in variable_key:
        def calc_wind(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
            return img.addBands(ws)
        collection = collection.map(calc_wind)
    elif "Umidade" in variable_key:
        collection = collection.map(_calculate_rh)
    elif "Radiação" in variable_key:
        collection = collection.map(_calculate_radiation)
    else:
        collection = collection.map(lambda img: img.rename(config["result_band"]))

    band_name = config["result_band"]
    
    def extract_val(image):
        val = image.select(band_name).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=9000, 
            bestEffort=True,
            maxPixels=1e9
        ).get(band_name)
        
        val_num = ee.Number(val)
        if config["unit"] == "°C": val_num = val_num.subtract(273.15)
        elif config["unit"] == "mm": val_num = val_num.multiply(1000)
            
        return image.set("date", image.date().format("YYYY-MM-dd")).set("value", val_num)

    series = collection.map(extract_val)
    
    # Recupera dados (client-side)
    dates = series.aggregate_array("date").getInfo()
    values = series.aggregate_array("value").getInfo()
    
    if not dates or not values: return pd.DataFrame()
    
    df = pd.DataFrame({"date": dates, "value": values})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors='coerce')
    return df.dropna().sort_values("date")
