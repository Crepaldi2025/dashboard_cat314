# ==================================================================================
# gee_handler.py — Módulo de acesso e processamento de dados do Google Earth Engine
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd

# ==================================================================================
# INICIALIZAÇÃO DO GOOGLE EARTH ENGINE
# ==================================================================================
def inicializar_gee():
    """
    Inicializa o Google Earth Engine.
    - Local: usa credenciais do 'earthengine authenticate'
    - Streamlit Cloud: usa Service Account configurada em st.secrets
    """
    try:
        if "earthengine_service_account" in st.secrets:
            service_account = st.secrets["earthengine_service_account"]["client_email"]
            private_key = st.secrets["earthengine_service_account"]["private_key"]
            credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
            ee.Initialize(credentials)
        else:
            ee.Initialize()
            st.info("✅ Conectado ao Google Earth Engine com credenciais locais.")
    except Exception as e:
        st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")

def initialize_gee():
    """Compatibilidade: redireciona para inicializar_gee()"""
    return inicializar_gee()

# ==================================================================================
# VARIÁVEIS DISPONÍVEIS DO ERA5-LAND
# ==================================================================================
ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m",
        "result_band": "temperature_2m",
        "unit": "°C",
        "aggregation": "mean",
        "vis_params": {"min": 0, "max": 40,
                       "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00',
                                   '#FFFF00', '#FFA500', '#FF0000', '#800000']}
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum",
        "result_band": "total_precipitation_sum",
        "unit": "mm",
        "aggregation": "sum",
        "vis_params": {"min": 0, "max": 500,
                       "palette": ['#FFFFFF', '#00FFFF', '#0000FF', '#00FF00',
                                   '#FFFF00', '#FF0000']}
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'],
        "result_band": "wind_speed",
        "unit": "m/s",
        "aggregation": "mean",
        "vis_params": {"min": 0, "max": 30,
                       "palette": ['#FFFFFF', '#B0E0E6', '#4682B4',
                                   '#DAA520', '#FF4500', '#8B0000']}
    }
}

# ==================================================================================
# GEOMETRIA — ÁREA DE INTERESSE
# ==================================================================================
def get_area_of_interest_geometry(session_state):
    """
    Obtém a geometria da área de interesse (Estado, Município, Círculo ou Polígono).
    Compatível com o ui.py atualizado.
    """
    tipo_loc = session_state.tipo_localizacao

    # ==============================================================
    # ESTADO
    # ==============================================================
    if tipo_loc == "Estado":
        uf_sigla = session_state.get("uf_sigla", None)
        if not uf_sigla:
            st.warning("Selecione um estado válido.")
            return None, None
        try:
            todos_estados_gdf = geobr.read_state()
            estado_gdf = todos_estados_gdf[todos_estados_gdf["abbrev_state"] == uf_sigla]
            if estado_gdf.empty:
                return None, None
            estado_geojson = json.loads(estado_gdf.to_json())["features"][0]["geometry"]
            ee_geometry = ee.Geometry(estado_geojson, proj="EPSG:4326", geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {"abbrev_state": uf_sigla})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Erro ao buscar geometria do estado: {e}")
            return None, None

    # ==============================================================
    # MUNICÍPIO
    # ==============================================================
    elif tipo_loc == "Município":
        uf_sigla = session_state.get("uf_sigla", None)
        municipio_nome = session_state.get("municipio_nome", None)
        if not uf_sigla or not municipio_nome:
            st.warning("Selecione um estado e um município válidos.")
            return None, None
        try:
            with st.spinner(f"Buscando geometria para {municipio_nome}, {uf_sigla}..."):
                municipios_do_estado_gdf = geobr.read_municipality(code_muni=uf_sigla, year=2020)
            municipio_gdf = municipios_do_estado_gdf[municipios_do_estado_gdf["name_muni"] == municipio_nome]
            if municipio_gdf.empty:
                return None, None
            municipio_geojson = json.loads(municipio_gdf.to_json())["features"][0]["geometry"]
            ee_geometry = ee.Geometry(municipio_geojson, proj="EPSG:4326", geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {"name_muni": municipio_nome, "abbrev_state": uf_sigla})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Erro ao buscar geometria do município: {e}")
            return None, None

    # ==============================================================
    # CÍRCULO
    # ==============================================================
    elif tipo_loc == "Círculo":
        try:
            latitude = session_state.latitude
            longitude = session_state.longitude
            raio_km = session_state.raio_km
            ponto_central = ee.Geometry.Point([longitude, latitude])
            ee_geometry = ponto_central.buffer(raio_km * 1000)
            ee_feature = ee.Feature(ee_geometry, {"latitude": latitude, "longitude": longitude, "raio_km": raio_km})
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Erro ao criar geometria do círculo: {e}")
            return None, None

    # ==============================================================
    # POLÍGONO
    # ==============================================================
    elif tipo_loc == "Polígono":
        if "drawn_geometry" not in session_state:
            st.warning("Nenhum polígono foi desenhado no mapa.")
            return None, None
        try:
            polygon_geojson = session_state.drawn_geometry
            ee_geometry = ee.Geometry(polygon_geojson, proj="EPSG:4326", geodesic=False)
            ee_feature = ee.Feature(ee_geometry)
            return ee_geometry, ee_feature
        except Exception as e:
            st.error(f"Erro ao processar geometria do polígono: {e}")
            return None, None

    return None, None

# ==================================================================================
# DADOS ERA5 — IMAGEM
# ==================================================================================
def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e processa os dados do ERA5-Land para mapas."""
    if variable not in ERA5_VARS:
        return None

    config = ERA5_VARS[variable]
    bands_to_select = config.get("bands", config.get("band"))

    image_collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(bands_to_select)
    )

    if image_collection.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return None

    # Correção para o vento (módulo de u/v)
    if variable == "Velocidade do Vento (10m)":
        def calculate_wind_speed(image):
            wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return image.addBands(wind_speed)
        image_collection = image_collection.map(calculate_wind_speed)

    # Agregação
    if config["aggregation"] == "mean":
        aggregated_image = image_collection.select(config["result_band"]).mean()
    elif config["aggregation"] == "sum":
        aggregated_image = image_collection.select(config["result_band"]).sum()
    else:
        aggregated_image = None

    if aggregated_image:
        final_image = aggregated_image.clip(geometry).float()
        if config["unit"] == "°C":
            final_image = final_image.subtract(273.15)
        if config["unit"] == "mm":
            final_image = final_image.multiply(1000)
        return final_image
    return None

# ==================================================================================
# DADOS ERA5 — SÉRIE TEMPORAL
# ==================================================================================
def get_time_series_data(variable, start_date, end_date, _geometry):
    """Extrai a série temporal do ERA5-Land restrita à geometria selecionada."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    bands_to_select = config.get("bands", config.get("band"))

    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(bands_to_select)
        .map(lambda img: img.clip(_geometry))
    )

    if collection.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return pd.DataFrame()

    if variable == "Velocidade do Vento (10m)":
        def calculate_wind_speed(image):
            wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename("wind_speed")
            return image.addBands(wind_speed)
        collection = collection.map(calculate_wind_speed)
    else:
        collection = collection.map(lambda img: img.rename(config["result_band"]))

    def extract_value(image):
        region = ee.Feature(_geometry).geometry()
        mean_value = image.select(config["result_band"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=9000,
            bestEffort=True,
            maxPixels=1e9
        ).get(config["result_band"])

        value = ee.Number(mean_value)
        if config["unit"] == "°C":
            value = value.subtract(273.15)
        elif config["unit"] == "mm":
            value = value.multiply(1000)

        return image.set("date", image.date().format("YYYY-MM-dd")).set("value", value)

    series = collection.map(extract_value)
    data = series.aggregate_array("date").getInfo()
    values = series.aggregate_array("value").getInfo()

    if not data or not values:
        st.warning("Não foi possível extrair dados para a área selecionada.")
        return pd.DataFrame()

    df = pd.DataFrame({"date": data, "value": values})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date")

    return df
