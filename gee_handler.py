# gee_handler.py
import streamlit as st
import json
from collections import defaultdict
import ee
import geobr
import pandas as pd

ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m", "result_band": "temperature_2m", "unit": "°C", "aggregation": "mean",
        "vis_params": { "min": 0, "max": 40, "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FFA500', '#FF0000', '#800000'] }
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum", "result_band": "total_precipitation_sum", "unit": "mm", "aggregation": "sum",
        "vis_params": { "min": 0, "max": 500, "palette": ['#FFFFFF', '#00FFFF', '#0000FF', '#00FF00', '#FFFF00', '#FF0000'] }
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'], "result_band": "wind_speed", "unit": "m/s", "aggregation": "mean",
        "vis_params": { "min": 0, "max": 30, "palette": ['#FFFFFF', '#B0E0E6', '#4682B4', '#DAA520', '#FF4500', '#8B0000'] }
    }
}

@st.cache_data
def get_brazilian_geopolitical_data_local():
    """Busca os dados de estados e municípios do Brasil a partir de um arquivo JSON local."""
    try:
        with open('municipios_ibge.json', 'r', encoding='utf-8') as f:
            municipios_data = json.load(f)
        geo_data = defaultdict(list)
        uf_name_map = {}
        for municipio in municipios_data:
            microrregiao = municipio.get('microrregiao')
            if microrregiao:
                mesorregiao = microrregiao.get('mesorregiao')
                if mesorregiao:
                    uf_data = mesorregiao.get('UF')
                    if uf_data:
                        uf_sigla = uf_data.get('sigla')
                        uf_nome = uf_data.get('nome')
                        if uf_sigla and uf_nome and uf_sigla not in uf_name_map:
                            uf_name_map[uf_sigla] = uf_nome
                        nome_municipio = municipio.get('nome')
                        if uf_sigla and nome_municipio:
                            geo_data[uf_sigla].append(nome_municipio)
        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data.keys())}
        return sorted_geo_data, uf_name_map
    except Exception as e:
        st.error(f"Erro ao processar arquivo de municípios: {e}")
        return {}, {}

def get_area_of_interest_geometry(session_state):
    """
    Obtém a geometria da área de interesse (Estado, Município, Círculo ou Polígono).
    """
    tipo_loc = session_state.tipo_localizacao
    
    if tipo_loc == "Estado":
        estado_selecionado_str = session_state.estado
        if estado_selecionado_str == "Selecione...": return None, None
        uf_sigla = estado_selecionado_str.split(' - ')[-1]
        try:
            todos_estados_gdf = geobr.read_state()
            estado_gdf = todos_estados_gdf[todos_estados_gdf['abbrev_state'] == uf_sigla]
            if estado_gdf.empty: return None, None
            estado_geojson = json.loads(estado_gdf.to_json())['features'][0]['geometry']
            ee_geometry = ee.Geometry(estado_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {'abbrev_state': uf_sigla})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Ocorreu um erro ao buscar a geometria do estado: {e}")
            return None, None

    elif tipo_loc == "Município":
        estado_selecionado_str = session_state.get('estado', 'Selecione...')
        municipio_nome = session_state.get('municipio', 'Selecione...')
        if estado_selecionado_str == "Selecione..." or municipio_nome == "Selecione...":
            st.warning("Por favor, selecione um estado e um município válidos.")
            return None, None
        uf_sigla = estado_selecionado_str.split(' - ')[-1]
        try:
            with st.spinner(f"Buscando geometria para {municipio_nome}, {uf_sigla}..."):
                municipios_do_estado_gdf = geobr.read_municipality(code_muni=uf_sigla, year=2020)
            municipio_gdf = municipios_do_estado_gdf[municipios_do_estado_gdf['name_muni'] == municipio_nome]
            if municipio_gdf.empty: return None, None
            municipio_geojson = json.loads(municipio_gdf.to_json())['features'][0]['geometry']
            ee_geometry = ee.Geometry(municipio_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {'name_muni': municipio_nome, 'abbrev_state': uf_sigla})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Ocorreu um erro ao buscar a geometria do município: {e}")
            return None, None

    elif tipo_loc == "Círculo (Lat/Lon/Raio)":
        try:
            latitude = session_state.latitude
            longitude = session_state.longitude
            raio_km = session_state.raio
            ponto_central = ee.Geometry.Point([longitude, latitude])
            raio_em_metros = raio_km * 1000
            ee_geometry = ponto_central.buffer(raio_em_metros)
            ee_feature = ee.Feature(ee_geometry, {'latitude': latitude, 'longitude': longitude, 'raio_km': raio_km})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Ocorreu um erro ao criar a geometria do círculo: {e}")
            return None, None
            
    elif tipo_loc == "Polígono":
        if 'drawn_geometry' not in session_state:
            st.warning("Nenhum polígono foi capturado do mapa.")
            return None, None
        try:
            polygon_geojson = session_state.drawn_geometry
            ee_geometry = ee.Geometry(polygon_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry)
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar a geometria do polígono desenhado: {e}")
            return None, None
    
    return None, None

def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e processa os dados do ERA5 para mapas."""
    if variable not in ERA5_VARS: return None
    config = ERA5_VARS[variable]
    bands_to_select = config.get('bands', config.get('band'))
    image_collection = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')).select(bands_to_select)
    
    if image_collection.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return None

    if variable == "Velocidade do Vento (10m)":
        def calculate_wind_speed(image):
            wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
            return image.addBands(wind_speed)
        image_collection = image_collection.map(calculate_wind_speed)
        
    if config['aggregation'] == 'mean':
        aggregated_image = image_collection.select(config['result_band']).mean()
    elif config['aggregation'] == 'sum':
        aggregated_image = image_collection.select(config['result_band']).sum()
    else:
        aggregated_image = None
        
    if aggregated_image:
        final_image = aggregated_image.clip(geometry).float()
        if config['unit'] == "°C": final_image = final_image.subtract(273.15)
        if config['unit'] == "mm": final_image = final_image.multiply(1000)
        if final_image.bandNames().size().getInfo() == 0: return None
        return final_image
    return None

@st.cache_data
def get_sampled_data_as_dataframe(_ee_image, _geometry, variable):
    """Amostra a imagem do GEE e retorna os dados como um DataFrame para tabela."""
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    band_name = config['result_band']
    unit = config['unit']
    
    sample = _ee_image.select(band_name).sample(region=_geometry, scale=10000, numPixels=500, geometries=True)
    features = sample.getInfo().get('features', [])
    if not features: return pd.DataFrame()

    data = []
    for feature in features:
        value = feature['properties'].get(band_name)
        if value is not None:
            coords = feature['geometry']['coordinates']
            data.append({
                'Longitude': coords[0],
                'Latitude': coords[1],
                f'{variable.split(" (")[0]} ({unit})': value
            })
    return pd.DataFrame(data)

@st.cache_data
def get_time_series_data(variable, start_date, end_date, _geometry):
    """Extrai a série temporal de uma variável para uma dada geometria."""
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    
    bands_to_select = config.get('bands', config.get('band'))
    image_collection = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')).select(bands_to_select)

    if image_collection.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return pd.DataFrame()

    if variable == "Velocidade do Vento (10m)":
        def calculate_wind_speed(image):
            wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
            return image.addBands(wind_speed)
        image_collection = image_collection.map(calculate_wind_speed)

    def extract_value(image):
        mean_value = image.select(config['result_band']).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=_geometry,
            scale=10000
        ).get(config['result_band'])
        
        final_value = ee.Number(mean_value)
        if config['unit'] == "°C":
            final_value = final_value.subtract(273.15)
        elif config['unit'] == "mm":
            final_value = final_value.multiply(1000)
            
        return image.set('date', image.date().format('YYYY-MM-dd')).set('value', final_value)

    time_series = image_collection.map(extract_value)
    
    data = time_series.reduceColumns(ee.Reducer.toList(2), ['date', 'value']).getInfo()['list']
    
    if not data:
        st.warning("Não foi possível extrair a série temporal.")
        return pd.DataFrame()
        
    df = pd.DataFrame(data, columns=['date', 'value'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').dropna()
    
    return df