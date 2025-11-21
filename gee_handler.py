# ==================================================================================
# gee_handler.py (v80 - Paletas de Cores Melhoradas)
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd
from datetime import date, datetime

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

# --- DEFINIÇÕES DE VARIÁVEIS E PALETAS ---
ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m", "result_band": "temperature_2m", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 35, "palette": ['#000080', '#0000FF', '#00AAFF', '#00FFFF', '#00FF00', '#AAFF00', '#FFFF00', '#FFAA00', '#FF0000', '#800000'], "caption": "Temperatura (°C)"}
    },
    "Temperatura do Ponto de Orvalho (2m)": {
        "band": "dewpoint_temperature_2m", "result_band": "dewpoint_temperature_2m", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 30, "palette": ['#000080', '#0000FF', '#00AAFF', '#00FFFF', '#00FF00', '#AAFF00', '#FFFF00', '#FFAA00', '#FF0000'], "caption": "Ponto de Orvalho (°C)"}
    },
    "Temperatura da Superfície (Skin)": {
        "band": "skin_temperature", "result_band": "skin_temperature", "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 10, "max": 50, "palette": ['#040274', '#040281', '#0502a3', '#0502b8', '#0502ce', '#0502e6', '#0602ff', '#235cb1', '#307ef3', '#269db1', '#30c8e2', '#32d3ef', '#3be285', '#3ff38f', '#86e26f', '#3ae237', '#b5e22e', '#d6e21f', '#fff705', '#ffd611', '#ffb613', '#ff8b13', '#ff6e08', '#ff500d', '#ff0000', '#de0101', '#c21301', '#a71001', '#911003'], "caption": "Temp. Superfície (°C)"}
    },
    # --- UMIDADE DO SOLO (0-0.6 m3/m3) ---
    # Paleta RdYlBu invertida (Vermelho=Seco, Azul=Úmido)
    "Umidade do Solo (0-7 cm)": {
        "band": "volumetric_soil_water_layer_1", "result_band": "volumetric_soil_water_layer_1", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0.1, "max": 0.5, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (0-7cm)"}
    },
    "Umidade do Solo (7-28 cm)": {
        "band": "volumetric_soil_water_layer_2", "result_band": "volumetric_soil_water_layer_2", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0.1, "max": 0.5, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (7-28cm)"}
    },
    "Umidade do Solo (28-100 cm)": {
        "band": "volumetric_soil_water_layer_3", "result_band": "volumetric_soil_water_layer_3", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0.1, "max": 0.5, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (28-100cm)"}
    },
    "Umidade do Solo (100-289 cm)": {
        "band": "volumetric_soil_water_layer_4", "result_band": "volumetric_soil_water_layer_4", "unit": "m³/m³", "aggregation": "mean",
        "vis_params": {"min": 0.1, "max": 0.5, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (1-3m)"}
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum", "result_band": "total_precipitation_sum", "unit": "mm", "aggregation": "sum",
        "vis_params": {"min": 0, "max": 50, "palette": ['#FFFFFF', '#C7E9C0', '#A1D99B', '#74C476', '#31A354', '#006D2C', '#08519C', '#08306B'], "caption": "Precipitação (mm)"}
    },
    "Umidade Relativa (2m)": {
        "bands": ["temperature_2m", "dewpoint_temperature_2m"], "result_band": "relative_humidity", "unit": "%", "aggregation": "mean",
        "vis_params": {"min": 20, "max": 95, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade Relativa (%)"}
    },
    "Radiação Solar Incidente": {
        "band": "surface_solar_radiation_downwards_sum", "result_band": "radiation_wm2", "unit": "W/m²", "aggregation": "mean",
        "vis_params": {"min": 50, "max": 400, "palette": ['#2c7bb6', '#abd9e9', '#ffffbf', '#fdae61', '#d7191c'], "caption": "Radiação (W/m²)"}
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'], "result_band": "wind_speed", "unit": "m/s", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 15, "palette": ['#FFFFFF', '#E6F5FF', '#CDE0F7', '#9ECAE1', '#6BAED6', '#4292C6', '#2171B5', '#08519C', '#08306B'], "caption": "Vento (m/s)"}
    }
}

FALLBACK_UF_MAP = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia',
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás',
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí',
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul',
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo',
    'SE': 'Sergipe', 'TO': 'Tocantins'
}

@st.cache_data
def get_brazilian_geopolitical_data_local() -> tuple[dict, dict]:
    arquivo = "municipios_ibge.json"
    geo_data = defaultdict(list)
    uf_name_map = {}
    try:
        if os.path.exists(arquivo):
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
    except: pass
    if not uf_name_map: uf_name_map = FALLBACK_UF_MAP
    return {uf: sorted(geo_data[uf]) for uf in sorted(geo_data)}, uf_name_map

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
            val = session_state.get('estado', '...')
            uf = val.split(' - ')[-1] if ' - ' in val else val
            gdf = _load_all_states_gdf()
            if gdf is None: return None, None
            geom = json.loads(gdf[gdf['abbrev_state'] == uf].to_json())['features'][0]['geometry']
            ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
            return ee_geom, ee.Feature(ee_geom, {'abbrev_state': uf})
        elif tipo == "Município":
            val = session_state.get('estado', '...')
            uf = val.split(' - ')[-1] if ' - ' in val else val
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

def _calc_rh(img):
    T = img.select('temperature_2m').subtract(273.15)
    Td = img.select('dewpoint_temperature_2m').subtract(273.15)
    es = T.multiply(17.625).divide(T.add(243.04)).exp().multiply(6.11)
    e = Td.multiply(17.625).divide(Td.add(243.04)).exp().multiply(6.11)
    return img.addBands(e.divide(es).multiply(100).rename('relative_humidity').min(100))

def _calc_rad(img, hourly=False):
    div = 3600 if hourly else 86400
    band = 'surface_solar_radiation_downwards' if hourly else 'surface_solar_radiation_downwards_sum'
    return img.addBands(img.select(band).divide(div).rename('radiation_wm2'))

def get_era5_image(variable: str, start_date: date, end_date: date, geometry: ee.Geometry, target_hour: int = None) -> ee.Image:
    if variable not in ERA5_VARS: return None
    config = ERA5_VARS[variable]
    is_hourly = target_hour is not None
    collection_id = 'ECMWF/ERA5_LAND/HOURLY' if is_hourly else 'ECMWF/ERA5_LAND/DAILY_AGGR'
    
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
        if is_hourly: col = col.filter(ee.Filter.calendarRange(target_hour, target_hour, 'hour'))
        if col.size().getInfo() == 0: return None

        if variable == "Velocidade do Vento (10m)":
            col = col.map(lambda img: img.addBands(img.select(bands_needed).pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])))
        elif variable == "Umidade Relativa (2m)": col = col.map(_calc_rh)
        elif variable == "Radiação Solar Incidente": col = col.map(lambda img: _calc_rad(img, is_hourly))
        
        band_agg = config['result_band']
        if is_hourly and variable == "Precipitação Total": band_agg = "total_precipitation"

        if config['aggregation'] == 'mean': img_agg = col.select(band_agg).mean()
        elif config['aggregation'] == 'sum': img_agg = col.select(band_agg).sum()
        else: img_agg = col.first().select(band_agg)

        final = img_agg.clip(geometry).float()
        if config['unit'] == "°C": final = final.subtract(273.15)
        elif config['unit'] == "mm": final = final.multiply(1000)
        if final.bandNames().size().getInfo() == 0: return None
        return final
    except Exception as e:
        st.error(f"Erro GEE: {e}")
        return None

def get_sampled_data_as_dataframe(ee_image: ee.Image, geometry: ee.Geometry, variable: str) -> pd.DataFrame:
    if not ee_image or variable not in ERA5_VARS: return pd.DataFrame()
    try:
        band_name = ee_image.bandNames().get(0).getInfo()
        sample = ee_image.select(band_name).sample(region=geometry, scale=10000, numPixels=500, geometries=True)
        feats = sample.getInfo()['features']
        data = [{'Latitude': f['geometry']['coordinates'][1], 'Longitude': f['geometry']['coordinates'][0], variable: f['properties'][band_name]} for f in feats]
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def get_time_series_data(variable: str, start_date: date, end_date: date, geometry: ee.Geometry) -> pd.DataFrame:
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
