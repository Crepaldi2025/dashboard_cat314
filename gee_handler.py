# gee_handler.py
import streamlit as st
import json
from collections import defaultdict
import ee
import json
import os
import streamlit as st

def get_brazilian_geopolitical_data_local():
    """Carrega os dados locais de estados e municípios do Brasil.
    Retorna dois dicionários: {UF: [municípios]} e {UF: nome_completo}.
    """
    dados_geo = {}
    mapa_nomes_uf = {}
    arquivo = "municipios_ibge.json"

    try:
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                dados_geo = data.get("municipios_por_uf", {})
                mapa_nomes_uf = data.get("nomes_estados", {})
        else:
            st.warning("Arquivo 'municipios_ibge.json' não encontrado. Sidebar limitada.")
    except Exception as e:
        st.error(f"Falha ao carregar dados geográficos: {e}")

    return dados_geo, mapa_nomes_uf

def inicializar_gee():
        
    """
    Inicializa o Google Earth Engine.
    - Local: usa credenciais do 'earthengine authenticate'
    - Streamlit Cloud: usa Service Account configurada em st.secrets
    """
    try:
        # Verifica se está no Streamlit Cloud (há segredos configurados)
        if "earthengine_service_account" in st.secrets:
            service_account = st.secrets["earthengine_service_account"]["client_email"]
            private_key = st.secrets["earthengine_service_account"]["private_key"]

            # Cria credenciais usando a conta de serviço
            credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
            ee.Initialize(credentials)
            
        else:
            # Executa localmente com credenciais já autenticadas
            ee.Initialize()
            st.info("✅ Conectado ao Google Earth Engine com credenciais locais.")
    except Exception as e:
        st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")

# ==========================================================
# Alias para compatibilidade com main.py
# ==========================================================
def initialize_gee():
    """Compatibilidade: redireciona para inicializar_gee()"""
    return inicializar_gee()

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
    st.write("📍 Tipo da geometria:", type(_geometry), _geometry.getInfo().get('type', 'desconhecido'))

    
    """Extrai a série temporal de uma variável do ERA5-Land para a geometria informada."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    bands_to_select = config.get("bands", config.get("band"))

    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(bands_to_select)
    )
    collection = collection.map(lambda img: img.clip(_geometry))
    st.write("✅ Aplicado clip à geometria:", _geometry.getInfo().get('type', 'N/A'))


    if collection.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return pd.DataFrame()

    # --- cálculo especial para o vento (mantido do seu código)
    if variable == "Velocidade do Vento (10m)":
        def calculate_wind_speed(image):
            wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return image.addBands(wind_speed)
        collection = collection.map(calculate_wind_speed)

    # --- média diária na área
    def extract_value(image):
        val = image.select(config["result_band"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=_geometry,
            scale=10000,
            bestEffort=True,
            maxPixels=1e9
        ).get(config["result_band"])

        # --- conversões de unidade
        final_val = ee.Number(val)
        if config["unit"] == "°C":
            final_val = final_val.subtract(273.15)
        elif config["unit"] == "mm":
            final_val = final_val.multiply(1000)

        return image.set("date", image.date().format("YYYY-MM-dd")).set("value", final_val)

    # --- aplica função
    series = collection.map(extract_value)

    # --- coleta resultados seguros
    try:
        data = series.aggregate_array("date").getInfo()
        values = series.aggregate_array("value").getInfo()
    except Exception as e:
        st.error(f"Falha ao recuperar dados da série: {e}")
        return pd.DataFrame()

    # --- cria DataFrame limpo
    if not data or not values:
        st.warning("Não foi possível extrair valores válidos do ERA5-Land para a área selecionada.")
        return pd.DataFrame()

    df = pd.DataFrame({"date": data, "value": values})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date")

    return df




# ==========================================================
# Compatibilidade com o main.py antigo
# ==========================================================
def get_gee_data(dataset, band, start_date, end_date, feature):
    """Mantém compatibilidade com versões antigas do main.py."""
    try:
        geometry = feature.geometry()
        # Determina a variável automaticamente (com base no nome da banda)
        if band == "temperature_2m":
            variable = "Temperatura do Ar (2m)"
        elif band == "total_precipitation_sum":
            variable = "Precipitação Total"
        elif band in ["u_component_of_wind_10m", "v_component_of_wind_10m"]:
            variable = "Velocidade do Vento (10m)"
        else:
            variable = "Temperatura do Ar (2m)"  # padrão de segurança
        return get_era5_image(variable, start_date, end_date, geometry)
    except Exception as e:
        st.error(f"⚠️ Falha ao processar dados do GEE: {e}")
        return None
    

    return df







