# ==================================================================================
# gee_handler.py (Atualizado para Ponto de Orvalho)
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
            "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'],
            "caption": "Temperatura do Ar (°C)"
        }
    },
    # --- NOVO: Temperatura do Ponto de Orvalho ---
    "Temperatura do Ponto de Orvalho (2m)": {
        "band": "dewpoint_temperature_2m", 
        "result_band": "dewpoint_temperature_2m", 
        "unit": "°C", 
        "aggregation": "mean",
        "vis_params": { 
            "min": 5, 
            "max": 35, 
            "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'],
            "caption": "Ponto de Orvalho (°C)" # Usado para forçar legenda correta
        }
    },
    # ---------------------------------------------
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
# CARREGAMENTO DE DADOS GEOGRÁFICOS
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
# PROCESSAMENTO DE GEOMETRIA
# ==========================================================

def get_area_of_interest_geometry(session_state) -> tuple[ee.Geometry, ee.Feature]:
    tipo_loc = session_state.get('tipo_localizacao', 'Estado')
    
    try:
        if tipo_loc == "Estado":
            estado_str = session_state.get('estado', 'Selecione...')
            if estado_str == "Selecione...": return None, None
            uf = estado_str.split(' - ')[-1]
            
            todos = _load_all_states_gdf() 
            if todos is None: return None, None
            
            st_gdf = todos[todos['abbrev_state'] == uf]
            if st_gdf.empty: return None, None
            
            geom = json.loads(st_gdf.to_json())['features'][0]['geometry']
            ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
            ee_feat = ee.Feature(ee_geom, {'abbrev_state': uf})
            return ee_geom, ee_feat

        elif tipo_loc == "Município":
            estado_str = session_state.get('estado', 'Selecione...')
            mun_nome = session_state.get('municipio', 'Selecione...')
            if estado_str == "Selecione..." or mun_nome == "Selecione...": return None, None
            
            uf = estado_str.split(' - ')[-1]
            mun_gdf = _load_municipalities_gdf(uf)
            if mun_gdf is None: return None, None

            row = mun_gdf[mun_gdf['name_muni'] == mun_nome]
            if row.empty: return None, None
            
            geom = json.loads(row.to_json())['features'][0]['geometry']
            ee_geom = ee.Geometry(geom, proj='EPSG:4326', geodesic=False)
            ee_feat = ee.Feature(ee_geom, {'name_muni': mun_nome, 'uf': uf})
            return ee_geom, ee_feat

        elif tipo_loc == "Círculo (Lat/Lon/Raio)":
            lat = session_state.latitude
            lon = session_state.longitude
            raio = session_state.raio
            pt = ee.Geometry.Point([lon, lat])
            ee_geom = pt.buffer(raio * 1000)
            ee_feat = ee.Feature(ee_geom, {'lat': lat, 'lon': lon, 'raio': raio})
            return ee_geom, ee_feat
                
        elif tipo_loc == "Polígono":
            if 'drawn_geometry' not in session_state or not session_state.drawn_geometry:
                return None, None
            geom_json = session_state.drawn_geometry
            ee_geom = ee.Geometry(geom_json, proj='EPSG:4326', geodesic=False)
            return ee_geom, ee.Feature(ee_geom)
    
    except Exception as e:
        st.error(f"Erro na geometria: {e}")
        return None, None

    return None, None

# ==========================================================
# PROCESSAMENTO DE DADOS GEE
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

def get_era5_image(variable: str, start_date: date, end_date: date, geometry: ee.Geometry) -> ee.Image:
    if variable not in ERA5_VARS: return None
    config = ERA5_VARS[variable]
    bands_to_select = config.get('bands', config.get('band'))
    
    try:
        col = (
            ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .select(bands_to_select)
        )
        
        if col.size().getInfo() == 0:
            st.warning("Sem dados para o período.")
            return None

        if variable == "Velocidade do Vento (10m)":
            def calc_wind(img):
                ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
                return img.addBands(ws)
            col = col.map(calc_wind)
        elif variable == "Umidade Relativa (2m)":
            col = col.map(_calculate_rh)
        elif variable == "Radiação Solar Incidente":
            col = col.map(_calculate_radiation)
            
        if config['aggregation'] == 'mean':
            img_agg = col.select(config['result_band']).mean()
        elif config['aggregation'] == 'sum':
            img_agg = col.select(config['result_band']).sum()
        else:
            img_agg = None
            
        if img_agg:
            final = img_agg.clip(geometry).float()
            if config['unit'] == "°C": final = final.subtract(273.15)
            if config['unit'] == "mm": final = final.multiply(1000)
            
            if final.bandNames().size().getInfo() == 0: return None
            return final
        return None
    except Exception as e:
        st.error(f"Erro GEE: {e}")
        return None

def get_sampled_data_as_dataframe(ee_image: ee.Image, geometry: ee.Geometry, variable: str) -> pd.DataFrame:
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    band = config['result_band']
    unit = config['unit']
    
    try:
        sample = ee_image.select(band).sample(region=geometry, scale=10000, numPixels=500, geometries=True)
        feats = sample.getInfo().get('features', [])
        if not feats: return pd.DataFrame()

        data = []
        for f in feats:
            val = f['properties'].get(band)
            if val is not None:
                c = f['geometry']['coordinates']
                data.append({'Longitude': c[0], 'Latitude': c[1], f'{variable.split(" (")[0]} ({unit})': val})
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def get_time_series_data(variable: str, start_date: date, end_date: date, geometry: ee.Geometry) -> pd.DataFrame:
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    bands_to_select = config.get("bands", config.get("band"))

    try:
        col = (
            ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .select(bands_to_select)
        )
        
        if col.size().getInfo() == 0: return pd.DataFrame()

        band_name = config["result_band"] 
        
        if variable == "Velocidade do Vento (10m)":
            def calc_wind(img):
                ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
                return img.addBands(ws)
            col = col.map(calc_wind)
        elif variable == "Umidade Relativa (2m)":
            col = col.map(_calculate_rh)
        elif variable == "Radiação Solar Incidente":
            col = col.map(_calculate_radiation)
        else:
            col = col.map(lambda img: img.rename(band_name))
            
        def extract(img):
            stats = img.select(band_name).reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=9000, bestEffort=True, maxPixels=1e9)
            val = ee.Number(stats.get(band_name))
            if config["unit"] == "°C": val = val.subtract(273.15)
            elif config["unit"] == "mm": val = val.multiply(1000)
            return img.set("date", img.date().format("YYYY-MM-dd")).set("value", val)

        series = col.map(extract)
        dates = series.aggregate_array("date").getInfo()
        vals = series.aggregate_array("value").getInfo()

        if not dates or not vals: return pd.DataFrame()

        df = pd.DataFrame({"date": dates, "value": vals})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna().sort_values("date")
    
    except Exception:
        return pd.DataFrame()
