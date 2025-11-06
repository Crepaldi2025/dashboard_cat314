# ==================================================================================
# gee_handler.py — Integração com o Google Earth Engine (GEE)
# ==================================================================================
import streamlit as st
import ee
import geobr
import json
import os
import pandas as pd
from collections import defaultdict
from functools import lru_cache

# ==================================================================================
# INICIALIZAÇÃO DO GEE
# ==================================================================================
def inicializar_gee():
    """Inicializa o Google Earth Engine (local ou via conta de serviço)."""
    try:
        if "earthengine_service_account" in st.secrets:
            service_account = st.secrets["earthengine_service_account"]["client_email"]
            private_key = st.secrets["earthengine_service_account"]["private_key"]
            credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
            ee.Initialize(credentials)
            st.info("✅ Conectado ao Google Earth Engine via Service Account.")
        else:
            ee.Initialize()
            st.info("✅ Conectado ao Google Earth Engine localmente.")
    except Exception as e:
        st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")

# Compatibilidade com main.py
def initialize_gee():
    return inicializar_gee()

# ==================================================================================
# DADOS GERAIS DO ERA5-LAND
# ==================================================================================
ERA5_VARS = {
    "Temperatura do ar (°C)": {
        "band": "temperature_2m",
        "result_band": "temperature_2m",
        "unit": "°C",
        "aggregation": "mean",
        "vis_params": {
            "min": 0, "max": 40,
            "palette": ["#000080", "#0000FF", "#00FFFF", "#00FF00",
                        "#FFFF00", "#FFA500", "#FF0000", "#800000"]
        }
    },
    "Precipitação (mm)": {
        "band": "total_precipitation_sum",
        "result_band": "total_precipitation_sum",
        "unit": "mm",
        "aggregation": "sum",
        "vis_params": {
            "min": 0, "max": 500,
            "palette": ["#FFFFFF", "#00FFFF", "#0000FF",
                        "#00FF00", "#FFFF00", "#FF0000"]
        }
    },
    "Umidade do solo (%)": {
        "band": "volumetric_soil_water_layer_1",
        "result_band": "volumetric_soil_water_layer_1",
        "unit": "%",
        "aggregation": "mean",
        "vis_params": {
            "min": 0, "max": 100,
            "palette": ["#f7fcf0", "#ccebc5", "#7bccc4",
                        "#2b8cbe", "#08589e"]
        }
    },
}

# ==================================================================================
# GEEOMETRIA: ESTADO / MUNICÍPIO / CÍRCULO / POLÍGONO
# ==================================================================================
def get_area_of_interest_geometry(session_state):
    """Obtém a geometria da área de interesse com base na seleção do usuário."""
    tipo_loc = session_state.get("tipo_localizacao")

    # === Estado ===
    if tipo_loc == "Estado":
        uf_sigla = session_state.get("uf_sigla")
        if not uf_sigla:
            st.warning("Nenhum estado selecionado.")
            return None, None
        try:
            estados = geobr.read_state()
            estado_gdf = estados[estados["abbrev_state"] == uf_sigla]
            if estado_gdf.empty:
                st.warning("Estado não encontrado.")
                return None, None
            geom = json.loads(estado_gdf.to_json())["features"][0]["geometry"]
            ee_geom = ee.Geometry(geom, proj="EPSG:4326", geodesic=False)
            feature = ee.Feature(ee_geom, {"abbrev_state": uf_sigla})
            return ee_geom, feature
        except Exception as e:
            st.error(f"Erro ao obter geometria do estado: {e}")
            return None, None

    # === Município ===
    elif tipo_loc == "Município":
        uf_sigla = session_state.get("uf_sigla")
        municipio_nome = session_state.get("municipio_nome")
        if not uf_sigla or not municipio_nome:
            st.warning("Selecione um estado e um município válidos.")
            return None, None
        try:
            with st.spinner(f"Carregando geometria de {municipio_nome} ({uf_sigla})..."):
                municipios = geobr.read_municipality(code_muni=uf_sigla, year=2020)
            muni_gdf = municipios[municipios["name_muni"] == municipio_nome]
            if muni_gdf.empty:
                st.warning("Município não encontrado.")
                return None, None
            geom = json.loads(muni_gdf.to_json())["features"][0]["geometry"]
            ee_geom = ee.Geometry(geom, proj="EPSG:4326", geodesic=False)
            feature = ee.Feature(ee_geom, {"name_muni": municipio_nome, "abbrev_state": uf_sigla})
            return ee_geom, feature
        except Exception as e:
            st.error(f"Erro ao buscar geometria do município: {e}")
            return None, None

    # === Círculo ===
    elif tipo_loc == "Círculo":
        try:
            latitude = session_state.get("latitude")
            longitude = session_state.get("longitude")
            raio_km = session_state.get("raio")
            if latitude is None or longitude is None or raio_km is None:
                st.warning("Defina latitude, longitude e raio para o círculo.")
                return None, None
            centro = ee.Geometry.Point([longitude, latitude])
            ee_geom = centro.buffer(raio_km * 1000)
            feature = ee.Feature(ee_geom, {
                "latitude": latitude,
                "longitude": longitude,
                "raio_km": raio_km
            })
            return ee_geom, feature
        except Exception as e:
            st.error(f"Erro ao criar geometria circular: {e}")
            return None, None

    # === Polígono ===
    elif tipo_loc == "Polígono":
        if "drawn_geometry" not in session_state:
            st.warning("Nenhum polígono desenhado foi detectado.")
            return None, None
        try:
            polygon_geojson = session_state.drawn_geometry
            ee_geom = ee.Geometry(polygon_geojson, proj="EPSG:4326", geodesic=False)
            feature = ee.Feature(ee_geom)
            return ee_geom, feature
        except Exception as e:
            st.error(f"Erro ao processar geometria do polígono: {e}")
            return None, None

    else:
        st.warning("Tipo de localização não reconhecido.")
        return None, None

# ==================================================================================
# GERAÇÃO DE IMAGEM — ERA5-LAND
# ==================================================================================
def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e processa imagem ERA5-Land diária para a geometria."""
    if variable not in ERA5_VARS:
        return None
    config = ERA5_VARS[variable]
    band = config["band"]

    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(band)
    )

    if collection.size().getInfo() == 0:
        st.warning("Nenhum dado ERA5-Land encontrado para o período selecionado.")
        return None

    if config["aggregation"] == "mean":
        img = collection.mean()
    elif config["aggregation"] == "sum":
        img = collection.sum()
    else:
        img = collection.first()

    img = img.clip(geometry).float()
    if config["unit"] == "°C":
        img = img.subtract(273.15)
    elif config["unit"] == "mm":
        img = img.multiply(1000)

    return img

# ==================================================================================
# EXTRAÇÃO DE SÉRIE TEMPORAL
# ==================================================================================
def get_time_series_data(variable, start_date, end_date, geometry):
    """Extrai a série temporal média da variável ERA5-Land sobre a área selecionada."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    band = config["band"]

    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select(band)
        .map(lambda img: img.clip(geometry))
    )

    if collection.size().getInfo() == 0:
        st.warning("Nenhum dado encontrado para o período.")
        return pd.DataFrame()

    def extract(image):
        value = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=9000,
            bestEffort=True,
            maxPixels=1e9
        ).get(band)

        if config["unit"] == "°C":
            value = ee.Number(value).subtract(273.15)
        elif config["unit"] == "mm":
            value = ee.Number(value).multiply(1000)

        return image.set("date", image.date().format("YYYY-MM-dd")).set("value", value)

    series = collection.map(extract)
    dates = series.aggregate_array("date").getInfo()
    values = series.aggregate_array("value").getInfo()

    if not dates or not values:
        return pd.DataFrame()

    df = pd.DataFrame({"date": dates, "value": values})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date")

    return df

# ==================================================================================
# === FIM ===
# ==================================================================================
