# ==================================================================================
# gee_handler.py (Atualizado v76 - Novas Variáveis + Análise Horária)
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd
from datetime import date, datetime

# ==========================================================
# INICIALIZAÇÃO
# ==========================================================
def inicializar_gee():
    try:
        ee.Image.constant(0).getInfo()
    except ee.EEException:
        try:
            if "earthengine_service_account" in st.secrets:
                service_account = st.secrets["earthengine_service_account"]["client_email"]
                private_key = st.secrets["earthengine_service_account"]["private_key"]
                credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
                ee.Initialize(credentials=credentials)
                st.info("✅ Conectado ao GEE (Service Account).")
            else:
                ee.Initialize()
                st.info("✅ Conectado ao GEE (Local).")
        except Exception as e:
            st.error(f"⚠️ Falha GEE: {e}")

def initialize_gee(): return inicializar_gee()

# ==========================================================
# DEFINIÇÕES DE VARIÁVEIS (Expandido com Skin Temp e Umidade Solo)
# ==========================================================

ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m", "result_band": "temperature_2m", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 40, "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'], "caption": "Temperatura do Ar (°C)"}
    },
    "Temperatura do Ponto de Orvalho (2m)": {
        "band": "dewpoint_temperature_2m", "result_band": "dewpoint_temperature_2m", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 5, "max": 35, "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'], "caption": "Ponto de Orvalho (°C)"}
    },
    
    # --- NOVAS VARIÁVEIS ---
    "Temperatura da Superfície (Skin)": {
        "band": "skin_temperature", "result_band": "skin_temperature", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 50, "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'], "caption": "Temp. Superfície (°C)"}
    },
    "Umidade do Solo (0-7 cm)": {
        "band": "volumetric_soil_water_layer_1", "result_band": "volumetric_soil_water_layer_1", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 0.6, "palette": ['#d7191c', '#fdae61', '#ffffbf', '#abdda4', '#2b83ba'], "caption": "Umidade Solo 0-7cm"}
    },
    "Umidade do Solo (7-28 cm)": {
        "band": "volumetric_soil_water_layer_2", "result_band": "volumetric_soil_water_layer_2", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 0.6, "palette": ['#d7191c', '#fdae61', '#ffffbf', '#abdda4', '#2b83ba'], "caption": "Umidade Solo 7-28cm"}
    },
    "Umidade do Solo (28-100 cm)": {
        "band": "volumetric_soil_water_layer_3", "result_band": "volumetric_soil_water_layer_3", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 0.6, "palette": ['#d7191c', '#fdae61', '#ffffbf', '#abdda4', '#2b83ba'], "caption": "Umidade Solo 28-100cm"}
    },
    "Umidade do Solo (100-289 cm)": {
        "band": "volumetric_soil_water_layer_4", "result_band": "volumetric_soil_water_layer_4", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 0.6, "palette": ['#d7191c', '#fdae61', '#ffffbf', '#abdda4', '#2b83ba'], "caption": "Umidade Solo 1-3m"}
    },
    # -----------------------
    
    "Precipitação Total": {
        "band": "total_precipitation_sum", "result_band": "total_precipitation_sum", "unit": "mm", "aggregation": "sum",
        "vis_params": {"min": 0, "max": 50, "palette": ['#ffffd9', '#edf8b1', '#c7e9b4', '#7fcdbb', '#41b6c4', '#1d91c0', '#225ea8', '#253494', '#081d58', '#081040'], "caption": "Precipitação (mm)"}
    },
    "Umidade Relativa (2m)": {
        "bands": ["temperature_2m", "dewpoint_temperature_2m"], "result_band": "relative_humidity", "unit": "%", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 100, "palette": ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026'], "caption": "Umidade Relativa (%)"}
    },
    "Radiação Solar Incidente": {
        "band": "surface_solar_radiation_downwards_sum", "result_band": "radiation_wm2", "unit": "W/m²", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 1000, "palette": ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026'], "caption": "Radiação (W/m²)"}
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'], "result_band": "wind_speed", "unit": "m/s", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 30, "palette": ['#440154', '#482878', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6dcd59', '#b4de2c', '#fde725'], "caption": "Vento (m/s)"}
    }
}

# ==========================================================
# HELPERS GEOGRÁFICOS
# ==========================================================
@st.cache_data
def get_brazilian_geopolitical_data_local() -> tuple[dict, dict]:
    arquivo = "municipios_ibge.json"
    geo_data = defaultdict(list)
    uf_name_map = {}
    try:
        if not os.path.exists(arquivo): return {}, {}
        with open(arquivo, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, list): 
            for m in d:
                uf = m.get('microrregiao', {}).get('mesorregiao', {}).get('UF', {})
                sigla, nome, mun = uf.get('sigla'), uf.get('nome'), m.get('nome')
                if sigla and nome: uf_name_map[sigla] = nome
                if sigla and mun: geo_data[sigla].append(mun)
        elif isinstance(d, dict):
            geo_data = d.get("municipios_por_uf", {})
            uf_name_map = d.get("nomes_estados", {})
        return {uf: sorted(geo_data[uf]) for uf in sorted(geo_data)}, uf_name_map
    except: return {}, {}

@st.cache_data
def _load_all_states_gdf():
    try: return geobr.read_state()
    except: return None

@st.cache_data
def _load_municipalities_gdf(uf):
    try: return geobr.read_municipality(code_muni=uf, year=2020)
    except: return None

def get_area_of_interest_geometry(session_state) -> tuple[ee.Geometry, ee.Feature]:
    tipo = session_state.get('tipo_localizacao', 'Estado')
    try:
        if tipo == "Estado":
            uf = session_state.get('estado', '...').split(' - ')[-1]
            gdf = _load_all_states_gdf()
            if gdf is None: return None, None
            geom = json.loads(gdf[gdf['abbrev_state'] == uf].to_json())['features'][0]['geometry']
            ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
            return ee_geom, ee.Feature(ee_geom, {'abbrev_state': uf})
        elif tipo == "Município":
            uf = session_state.get('estado', '...').split(' - ')[-1]
            mun = session_state.get('municipio', '...')
            gdf = _load_municipalities_gdf(uf)
            if gdf is None: return None, None
            geom = json.loads(gdf[gdf['name_muni'] == mun].to_json())['features'][0]['geometry']
            ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
            return ee_geom, ee.Feature(ee_geom, {'name_muni': mun, 'uf': uf})
        elif tipo == "Círculo (Lat/Lon/Raio)":
            pt = ee.Geometry.Point([session_state.longitude, session_state.latitude])
            ee_geom = pt.buffer(session_state.raio * 1000)
            return ee_geom, ee.Feature(ee_geom, {'type': 'Circle'})
        elif tipo == "Polígono":
            if not session_state.get('drawn_geometry'): return None, None
            ee_geom = ee.Geometry(session_state.drawn_geometry, proj='EPSG:4326', geodesic=False)
            return ee_geom, ee.Feature(ee_geom, {'type': 'Polygon'})
    except: return None, None
    return None, None

# ==========================================================
# PROCESSAMENTO GEE (HÍBRIDO: DIÁRIO E HORÁRIO)
# ==========================================================

def _calc_rh(img):
    T = img.select('temperature_2m').subtract(273.15)
    Td = img.select('dewpoint_temperature_2m').subtract(273.15)
    es = T.multiply(17.625).divide(T.add(243.04)).exp().multiply(6.11)
    e = Td.multiply(17.625).divide(Td.add(243.04)).exp().multiply(6.11)
    return img.addBands(e.divide(es).multiply(100).rename('relative_humidity').min(100))

def _calc_rad(img, hourly=False):
    # Para W/m²: Diário divide por 86400s; Horário divide por 3600s
    div = 3600 if hourly else 86400
    band = 'surface_solar_radiation_downwards' if hourly else 'surface_solar_radiation_downwards_sum'
    return img.addBands(img.select(band).divide(div).rename('radiation_wm2'))

def get_era5_image(variable: str, start_date: date, end_date: date, geometry: ee.Geometry, target_hour: int = None) -> ee.Image:
    """
    Gera imagem do GEE. Se target_hour for definido, usa coleção HOURLY.
    """
    if variable not in ERA5_VARS: return None
    config = ERA5_VARS[variable]
    
    # Seleção de Coleção
    is_hourly = target_hour is not None
    collection_id = 'ECMWF/ERA5_LAND/HOURLY' if is_hourly else 'ECMWF/ERA5_LAND/DAILY_AGGR'
    
    # Ajuste de bandas para Hourly (nomes diferem do Daily)
    band_raw = config.get('band')
    if is_hourly:
        if variable == "Precipitação Total": band_raw = "total_precipitation"
        elif variable == "Radiação Solar Incidente": band_raw = "surface_solar_radiation_downwards"
    
    bands_needed = config.get('bands', [band_raw])
    if is_hourly:
        if variable == "Precipitação Total": bands_needed = ["total_precipitation"]
        elif variable == "Radiação Solar Incidente": bands_needed = ["surface_solar_radiation_downwards"]

    try:
        col = ee.ImageCollection(collection_id).filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        if is_hourly:
            # Filtra apenas a hora específica (0 a 23)
            col = col.filter(ee.Filter.calendarRange(target_hour, target_hour, 'hour'))
            
        if col.size().getInfo() == 0: return None

        # Cálculos Específicos
        if variable == "Velocidade do Vento (10m)":
            col = col.map(lambda img: img.addBands(img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])))
        elif variable == "Umidade Relativa (2m)":
            col = col.map(_calc_rh)
        elif variable == "Radiação Solar Incidente":
            col = col.map(lambda img: _calc_rad(img, is_hourly))
        
        # Agregação
        if config['aggregation'] == 'mean': img_agg = col.select(config['result_band']).mean()
        elif config['aggregation'] == 'sum': img_agg = col.select(config['result_band']).sum()
        else: img_agg = col.first().select(config['result_band'])

        # Conversão de Unidades e Recorte
        final = img_agg.clip(geometry).float()
        if config['unit'] == "°C": final = final.subtract(273.15)
        elif config['unit'] == "mm": final = final.multiply(1000) # Tanto hourly quanto daily vem em metros

        if final.bandNames().size().getInfo() == 0: return None
        return final
        
    except Exception as e:
        st.error(f"Erro GEE: {e}")
        return None

def get_sampled_data_as_dataframe(ee_image: ee.Image, geometry: ee.Geometry, variable: str) -> pd.DataFrame:
    if not ee_image or variable not in ERA5_VARS: return pd.DataFrame()
    band = ERA5_VARS[variable]['result_band']
    try:
        sample = ee_image.select(band).sample(region=geometry, scale=10000, numPixels=500, geometries=True)
        feats = sample.getInfo()['features']
        data = [{'Latitude': f['geometry']['coordinates'][1], 'Longitude': f['geometry']['coordinates'][0], variable: f['properties'][band]} for f in feats]
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def get_time_series_data(variable: str, start_date: date, end_date: date, geometry: ee.Geometry) -> pd.DataFrame:
    # Série temporal continua usando apenas Diário para manter consistência
    return _get_series_generic(variable, start_date, end_date, geometry)

def _get_series_generic(variable, start, end, geom):
    if variable not in ERA5_VARS: return pd.DataFrame()
    cfg = ERA5_VARS[variable]
    col_id = 'ECMWF/ERA5_LAND/DAILY_AGGR'
    bands = cfg.get('bands', cfg.get('band'))
    
    try:
        col = ee.ImageCollection(col_id).filterDate(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')).select(bands)
        if col.size().getInfo() == 0: return pd.DataFrame()
        
        if variable == "Velocidade do Vento (10m)":
            col = col.map(lambda img: img.addBands(img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(cfg['result_band'])))
        elif variable == "Umidade Relativa (2m)": col = col.map(_calc_rh)
        elif variable == "Radiação Solar Incidente": col = col.map(lambda img: _calc_rad(img, False))
        else: col = col.map(lambda img: img.rename(cfg['result_band']))
        
        def ext(img):
            val = img.select(cfg['result_band']).reduceRegion(ee.Reducer.mean(), geom, 9000, bestEffort=True, maxPixels=1e9).get(cfg['result_band'])
            val = ee.Number(val)
            if cfg['unit'] == "°C": val = val.subtract(273.15)
            elif cfg['unit'] == "mm": val = val.multiply(1000)
            return img.set('date', img.date().format('YYYY-MM-dd')).set('value', val)
            
        series = col.map(ext)
        dates = series.aggregate_array('date').getInfo()
        vals = series.aggregate_array('value').getInfo()
        if not dates or not vals: return pd.DataFrame()
        
        df = pd.DataFrame({'date': dates, 'value': vals})
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df.dropna().sort_values('date')
    except: return pd.DataFrame()
