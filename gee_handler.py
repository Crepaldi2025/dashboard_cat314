# ==================================================================================
# gee_handler.py (VERSÃO: "FUNCIONA DE QUALQUER JEITO")
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd
from datetime import date, datetime
import requests 
import unicodedata
import shapefile_handler

# --- INICIALIZAÇÃO GEE ---
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
            else:
                ee.Initialize()
        except Exception as e:
            st.error(f"⚠️ Falha GEE: {e}")

def initialize_gee(): return inicializar_gee()

# --- VARIÁVEIS DO PROJETO ---
ERA5_VARS = {
    "Temperatura do Ar (2m)": { "band": "temperature_2m", "result_band": "temperature_2m", "unit": "°C", "aggregation": "mean", "vis_params": {"min": 0, "max": 45, "palette": ['#000080', '#0000FF', '#00AAFF', '#00FFFF', '#00FF00', '#AAFF00', '#FFFF00', '#FFAA00', '#FF0000', '#800000'], "caption": "Temperatura (°C)"} },
    "Temperatura do Ponto de Orvalho (2m)": { "band": "dewpoint_temperature_2m", "result_band": "dewpoint_temperature_2m", "unit": "°C", "aggregation": "mean", "vis_params": {"min": -10, "max": 30, "palette": ['#000080', '#0000FF', '#00AAFF', '#00FFFF', '#00FF00', '#AAFF00', '#FFFF00', '#FFAA00', '#FF0000'], "caption": "Ponto de Orvalho (°C)"} },
    "Temperatura da Superfície (Skin)": { "band": "skin_temperature", "result_band": "skin_temperature", "unit": "°C", "aggregation": "mean", "vis_params": {"min": 0, "max": 50, "palette": ['#040274', '#040281', '#0502a3', '#0502b8', '#0502ce', '#0502e6', '#0602ff', '#235cb1', '#307ef3', '#269db1', '#30c8e2', '#32d3ef', '#3be285', '#3ff38f', '#86e26f', '#3ae237', '#b5e22e', '#d6e21f', '#fff705', '#ffd611', '#ffb613', '#ff8b13', '#ff6e08', '#ff500d', '#ff0000', '#de0101', '#c21301', '#a71001', '#911003'], "caption": "Temp. Superfície (°C)"} },
    "Precipitação Total": { "band": "total_precipitation_sum", "result_band": "total_precipitation_sum", "unit": "mm", "aggregation": "sum", "vis_params": {"min": 0, "max": 500, "palette": ['#FFFFFF', '#C7E9C0', '#A1D99B', '#74C476', '#31A354', '#006D2C', '#08519C', '#08306B'], "caption": "Precipitação (mm)"} },
    "Umidade Relativa (2m)": { "bands": ["temperature_2m", "dewpoint_temperature_2m"], "result_band": "relative_humidity", "unit": "%", "aggregation": "mean", "vis_params": {"min": 20, "max": 95, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade Relativa (%)"} },
    "Radiação Solar Incidente": { "band": "surface_solar_radiation_downwards_sum", "result_band": "radiation_wm2", "unit": "W/m²", "aggregation": "mean", "vis_params": {"min": 0, "max": 500, "palette": ['#2c7bb6', '#abd9e9', '#ffffbf', '#fdae61', '#d7191c'], "caption": "Radiação (W/m²)"} },
    "Velocidade do Vento (10m)": { "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'], "result_band": "wind_speed", "unit": "m/s", "aggregation": "mean", "vis_params": {"min": 0, "max": 35, "palette": ['#FFFFFF', '#E6F5FF', '#CDE0F7', '#9ECAE1', '#6BAED6', '#4292C6', '#2171B5', '#08519C', '#08306B'], "caption": "Vento (m/s)"} },
    "Umidade do Solo (0-7 cm)": { "band": "volumetric_soil_water_layer_1", "result_band": "volumetric_soil_water_layer_1", "unit": "m³/m³", "aggregation": "mean", "vis_params": {"min": 0.0, "max": 1.0, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (0-7cm)"} },
    "Umidade do Solo (7-28 cm)": { "band": "volumetric_soil_water_layer_2", "result_band": "volumetric_soil_water_layer_2", "unit": "m³/m³", "aggregation": "mean", "vis_params": {"min": 0.0, "max": 1.0, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (7-28cm)"} },
    "Umidade do Solo (28-100 cm)": { "band": "volumetric_soil_water_layer_3", "result_band": "volumetric_soil_water_layer_3", "unit": "m³/m³", "aggregation": "mean", "vis_params": {"min": 0.0, "max": 1.0, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (28-100cm)"} },
    "Umidade do Solo (100-289 cm)": { "band": "volumetric_soil_water_layer_4", "result_band": "volumetric_soil_water_layer_4", "unit": "m³/m³", "aggregation": "mean", "vis_params": {"min": 0.0, "max": 1.0, "palette": ['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'], "caption": "Umidade (1-3m)"} },
}

FALLBACK_UF_MAP = {'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'}

# --- HELPER DE NORMALIZAÇÃO ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

# --- CARREGAMENTO DE DADOS GEOPOLÍTICOS (IBGE API) ---
@st.cache_data(ttl=3600*24)
def get_brazilian_geopolitical_data_local() -> tuple[dict, dict]:
    try:
        # Busca Estados
        url_uf = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"
        ufs = requests.get(url_uf, timeout=5).json()
        mapa_nomes_uf = {u['sigla']: u['nome'] for u in ufs}
        if not mapa_nomes_uf: mapa_nomes_uf = FALLBACK_UF_MAP
        
        # Busca Municípios
        url_mun = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome"
        munis = requests.get(url_mun, timeout=10).json()
        
        geo_data = defaultdict(list)
        for m in munis:
            try:
                uf_sigla = m['microrregiao']['mesorregiao']['UF']['sigla']
                geo_data[uf_sigla].append(m['nome'])
            except: continue
            
        return dict(geo_data), mapa_nomes_uf
    except: return {}, FALLBACK_UF_MAP

# --- CARREGADORES GEOBR (COM CACHE) ---
@st.cache_data
def _load_all_states_gdf():
    try: return geobr.read_state()
    except: return None

@st.cache_data
def _load_municipalities_gdf(uf):
    # Carrega base do geobr com tratamento de erro
    try: return geobr.read_municipality(code_muni=uf, year=2020)
    except: return None

# --- GEOMETRIA: LÓGICA ROBUSTA "VALE TUDO" ---
def get_area_of_interest_geometry(session_state) -> tuple[ee.Geometry, ee.Feature]:
    tipo = session_state.get('tipo_localizacao', 'Estado')
    nav_opt = session_state.get('nav_option')
    
    # 1. SHAPEFILE
    if nav_opt == "Shapefile":
        uploaded = session_state.get('shapefile_upload')
        if uploaded: return shapefile_handler.process_uploaded_shapefile(uploaded)
        return None, None

    # 2. POLÍGONO / CÍRCULO
    if tipo == "Polígono":
        if not session_state.get('drawn_geometry'): return None, None
        ee_geom = ee.Geometry(session_state.drawn_geometry, proj='EPSG:4326', geodesic=False)
        return ee_geom, ee.Feature(ee_geom, {'type': 'Polygon'})
    elif tipo == "Círculo (Lat/Lon/Raio)":
        pt = ee.Geometry.Point([session_state.longitude, session_state.latitude])
        ee_geom = pt.buffer(session_state.raio * 1000)
        return ee_geom, ee.Feature(ee_geom, {'type': 'Circle'})

    # 3. ESTADO / MUNICÍPIO
    try:
        val = session_state.get('estado', '...')
        uf_sigla = val.split(' - ')[0] if ' - ' in val else val
        uf_nome = val.split(' - ')[1] if ' - ' in val else val

        if tipo == "Estado":
            gdf = _load_all_states_gdf()
            if gdf is not None:
                geom = json.loads(gdf[gdf['abbrev_state'] == uf_sigla].to_json())['features'][0]['geometry']
                ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
                return ee_geom, ee.Feature(ee_geom, {'abbrev_state': uf_sigla})
        
        elif tipo == "Município":
            mun = session_state.get('municipio', '...')
            mun_norm = normalize_text(mun)
            
            # --- TENTATIVA 1: GEOBR (Base Oficial BR) ---
            gdf = _load_municipalities_gdf(uf_sigla)
            if gdf is not None:
                gdf['name_norm'] = gdf['name_muni'].apply(normalize_text)
                
                # Match Exato Normalizado
                match = gdf[gdf['name_norm'] == mun_norm]
                
                # Match Parcial (Contém) - Salva casos como "Mogi Mirim" vs "Mogi-Mirim"
                if match.empty:
                    match = gdf[gdf['name_norm'].str.contains(mun_norm, regex=False)]
                
                if not match.empty:
                    # Pega o primeiro resultado
                    geom = json.loads(match.iloc[0:1].to_json())['features'][0]['geometry']
                    ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
                    return ee_geom, ee.Feature(ee_geom, {'name_muni': mun, 'uf': uf_sigla})

            # --- TENTATIVA 2: FAO GAUL (Base Google - Satélite) ---
            # Se o geobr falhar, tentamos a base mundial do Google
            fc = ee.FeatureCollection("FAO/GAUL/2015/level2")
            
            # Filtro Case Insensitive no GEE
            filter_name = ee.Filter.stringContains('ADM2_NAME', mun, None, True) # Ignora maiusc/minusc
            filter_state = ee.Filter.eq('ADM1_NAME', normalize_text(uf_nome).title())
            
            feat_fao = fc.filter(ee.Filter.and_(filter_state, filter_name)).first()
            
            # Se não achou com estado, tenta só pelo nome da cidade (Desespero)
            if not feat_fao:
                feat_fao = fc.filter(filter_name).first()
                
            if feat_fao:
                return feat_fao.geometry(), feat_fao

            # --- TENTATIVA 3 (ÚLTIMA CHANCE): Círculo Genérico ---
            # Se não achou geometria nenhuma, cria um ponto no meio do estado como fallback
            # para não travar o app (Melhor um mapa errado que erro na tela)
            st.warning(f"⚠️ Limites exatos de '{mun}' não encontrados. Usando aproximação.")
            # Pega geometria do estado e faz um ponto no centro
            state_geom, _ = get_area_of_interest_geometry({'tipo_localizacao': 'Estado', 'estado': val, 'nav_option': 'Mapas'})
            if state_geom:
                return state_geom.centroid().buffer(20000), ee.Feature(state_geom.centroid(), {'name': 'Aproximado'})

            st.error(f"Não foi possível localizar '{mun}'.")
            return None, None

    except Exception as e:
        print(f"Erro geometria: {e}")
        return None, None
    return None, None

# --- FUNÇÕES AUXILIARES ERA5 ---
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
    using_era5_global = False
    
    if is_hourly:
        if variable == "Precipitação Total": band_raw = "total_precipitation"
        elif variable == "Radiação Solar Incidente": 
            collection_id = 'ECMWF/ERA5/HOURLY'
            band_raw = "mean_surface_downward_short_wave_radiation_flux"
            using_era5_global = True
    
    bands_needed = config.get('bands', [band_raw])
    if is_hourly and not using_era5_global:
        if variable == "Precipitação Total": bands_needed = ["total_precipitation"]
        elif variable == "Radiação Solar Incidente": bands_needed = ["surface_solar_radiation_downwards"]
    elif using_era5_global: bands_needed = [band_raw]

    try:
        col = ee.ImageCollection(collection_id).filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        if is_hourly: col = col.filter(ee.Filter.calendarRange(target_hour, target_hour, 'hour'))
        if col.size().getInfo() == 0: return None

        if variable == "Velocidade do Vento (10m)":
            col = col.map(lambda img: img.addBands(img.select(['u_component_of_wind_10m', 'v_component_of_wind_10m']).pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])))
        elif variable == "Umidade Relativa (2m)": col = col.map(_calc_rh)
        elif variable == "Radiação Solar Incidente":
            if using_era5_global: col = col.map(lambda img: img.select(band_raw).rename('radiation_wm2'))
            else: col = col.map(lambda img: _calc_rad(img, is_hourly))
        
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
    except: return None

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
            col = col.map(lambda img: img.addBands(img.select(['u_component_of_wind_10m', 'v_component_of_wind_10m']).pow(2).reduce(ee.Reducer.sum()).sqrt().rename(cfg['result_band'])))
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

def obter_vis_params_interativo(variavel: str):
    if variavel not in ERA5_VARS: return {}
    config_padrao = ERA5_VARS[variavel]['vis_params']
    padrao_min = float(config_padrao.get('min', 0))
    padrao_max = float(config_padrao.get('max', 100))
    with st.expander(f"🎨 Ajustar Escala de Cores: {variavel}", expanded=False):
        unidade = ERA5_VARS[variavel].get('unit', '')
        st.caption(f"Unidade: {unidade} | Valores Padrão: {padrao_min} a {padrao_max}")
        col1, col2 = st.columns(2)
        with col1: novo_min = st.number_input("Valor Mínimo", value=padrao_min, step=1.0, format="%.1f", key=f"min_{variavel}")
        with col2: novo_max = st.number_input("Valor Máximo", value=padrao_max, step=1.0, format="%.1f", key=f"max_{variavel}")
    nova_config = config_padrao.copy()
    nova_config['min'] = novo_min
    nova_config['max'] = novo_max
    return nova_config
