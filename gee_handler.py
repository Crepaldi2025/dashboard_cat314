# ==================================================================================
# gee_handler.py — Clima-Cast-Crepaldi (versão estável restaurada)
# ==================================================================================

import streamlit as st
import json
from collections import defaultdict
import ee
import geobr
import pandas as pd

# ============================================================
# Inicialização robusta do Google Earth Engine
# ============================================================

PROJECT_ID = "gee-crepaldi-2025b"

def inicializar_gee():
    """
    Inicializa o Google Earth Engine.
    1) Tenta autenticação local (earthengine authenticate)
    2) Se falhar, tenta Service Account (Streamlit Cloud)
    """
    try:
        ee.Initialize(project=PROJECT_ID)
        return "local"
    except Exception:
        try:
            creds = dict(st.secrets["earthengine_service_account"])
            credentials = ee.ServiceAccountCredentials(
                creds["client_email"], key_data=json.dumps(creds)
            )
            ee.Initialize(credentials, project=PROJECT_ID)
            return "service_account"
        except Exception as e:
            st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")
            return None

# ============================================================
# Variáveis do ERA5-LAND
# ============================================================

ERA5_VARS = {
    "Temperatura do Ar (2m)": {
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
            "palette": [
                "#FFFFFF", "#00FFFF", "#0000FF", "#00FF00",
                "#FFFF00", "#FF0000"
            ]
        }
    },
    "Velocidade do Vento (10m)": {
        "bands": ["u_component_of_wind_10m", "v_component_of_wind_10m"],
        "result_band": "wind_speed",
        "unit": "m/s",
        "aggregation": "mean",
        "vis_params": {
            "min": 0,
            "max": 30,
            "palette": [
                "#FFFFFF", "#B0E0E6", "#4682B4",
                "#DAA520", "#FF4500", "#8B0000"
            ]
        }
    },
}

# ============================================================
# Dados geopolíticos locais (cacheados)
# ============================================================

@st.cache_data
def get_brazilian_geopolitical_data_local():
    """Lê o JSON local de municípios e organiza por UF."""
    try:
        with open("municipios_ibge.json", "r", encoding="utf-8") as f:
            municipios_data = json.load(f)

        geo_data = defaultdict(list)
        uf_name_map = {}

        for municipio in municipios_data:
            microrregiao = municipio.get("microrregiao")
            if not microrregiao:
                continue
            mesorregiao = microrregiao.get("mesorregiao", {})
            uf_data = mesorregiao.get("UF", {})
            uf_sigla = uf_data.get("sigla")
            uf_nome = uf_data.get("nome")
            nome_municipio = municipio.get("nome")

            if uf_sigla and uf_nome:
                uf_name_map[uf_sigla] = uf_nome
            if uf_sigla and nome_municipio:
                geo_data[uf_sigla].append(nome_municipio)

        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data.keys())}
        return sorted_geo_data, uf_name_map

    except Exception as e:
        st.error(f"Erro ao processar arquivo de municípios: {e}")
        return {}, {}

# ============================================================
# Geometrias (Estado, Município, Círculo, Polígono)
# ============================================================

def get_area_of_interest_geometry(session_state):
    """Obtém a geometria da área de interesse."""
    tipo = session_state.get("tipo_localizacao")

    if tipo == "Estado":
        estado_str = session_state.get("estado", "Selecione...")
        if estado_str == "Selecione...":
            return None, None
        uf_sigla = estado_str.split(" - ")[-1]
        estados = geobr.read_state()
        gdf = estados[estados["abbrev_state"] == uf_sigla]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"abbrev_state": uf_sigla})
        return geom, feat

    elif tipo == "Município":
        estado_str = session_state.get("estado", "Selecione...")
        municipio_nome = session_state.get("municipio", "Selecione...")
        if estado_str == "Selecione..." or municipio_nome == "Selecione...":
            st.warning("Selecione um estado e um município válidos.")
            return None, None
        uf_sigla = estado_str.split(" - ")[-1]
        municipios = geobr.read_municipality(code_muni=uf_sigla, year=2020)
        gdf = municipios[municipios["name_muni"] == municipio_nome]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"name_muni": municipio_nome, "abbrev_state": uf_sigla})
        return geom, feat

    elif tipo == "Círculo (Lat/Lon/Raio)":
        try:
            lat = session_state.latitude
            lon = session_state.longitude
            raio_km = session_state.raio
            ponto = ee.Geometry.Point([lon, lat])
            geom = ponto.buffer(raio_km * 1000)
            feat = ee.Feature(geom, {"latitude": lat, "longitude": lon, "raio_km": raio_km})
            return geom, feat
        except Exception as e:
            st.error(f"Erro ao criar círculo: {e}")
            return None, None

    elif tipo == "Polígono":
        if "drawn_geometry" not in session_state:
            st.warning("Nenhum polígono desenhado.")
            return None, None
        try:
            geom = ee.Geometry(session_state.drawn_geometry, proj="EPSG:4326", geodesic=False)
            feat = ee.Feature(geom)
            return geom, feat
        except Exception as e:
            st.error(f"Erro ao processar polígono: {e}")
            return None, None

    return None, None

# ============================================================
# ERA5-LAND — Mapas
# ============================================================

def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e processa dados do ERA5-LAND para mapas."""
    config = ERA5_VARS.get(variable)
    if not config:
        return None

    bands = config.get("bands", config.get("band"))
    ic = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(bands)

    if ic.size().getInfo() == 0:
        st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
        return None

    if variable == "Velocidade do Vento (10m)":
        def calc_ws(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return img.addBands(ws)
        ic = ic.map(calc_ws)

    agg = config["aggregation"]
    if agg == "mean":
        agg_img = ic.select(config["result_band"]).mean()
    elif agg == "sum":
        agg_img = ic.select(config["result_band"]).sum()
    else:
        agg_img = ic.select(config["result_band"]).first()

    img = agg_img.clip(geometry).float()
    if config["unit"] == "°C":
        img = img.subtract(273.15)
    elif config["unit"] == "mm":
        img = img.multiply(1000)
    return img

# ============================================================
# Tabela de dados amostrados (mapa)
# ============================================================

def get_sampled_data_as_dataframe(img, geom, variable):
    """Amostra a imagem e retorna um DataFrame."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()
    config = ERA5_VARS[variable]
    band = config["result_band"]
    unit = config["unit"]

    sample = img.select(band).sample(
        region=geom, scale=10000, numPixels=500, geometries=True
    )
    features = sample.getInfo().get("features", [])
    data = []
    for f in features:
        val = f["properties"].get(band)
        if val is not None:
            coords = f["geometry"]["coordinates"]
            data.append({
                "Longitude": coords[0],
                "Latitude": coords[1],
                f"{variable.split(' (')[0]} ({unit})": val
            })
    return pd.DataFrame(data)

# ============================================================
# ERA5-LAND — Séries Temporais (média diária)
# ============================================================

def get_time_series_data(variable, start_date, end_date, geometry):
    """Extrai a série temporal diária (média espacial)."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()
    config = ERA5_VARS[variable]
    bands = config.get("bands", config.get("band"))

    ic = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(bands)

    if variable == "Velocidade do Vento (10m)":
        def calc_ws(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return img.addBands(ws)
        ic = ic.map(calc_ws)

    def extract(img):
        val = img.select(config["result_band"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000
        ).get(config["result_band"])
        v = ee.Number(val)
        if config["unit"] == "°C":
            v = v.subtract(273.15)
        elif config["unit"] == "mm":
            v = v.multiply(1000)
        return img.set("date", img.date().format("YYYY-MM-dd")).set("value", v)

    ts = ic.map(extract)
    lst = ts.reduceColumns(
        ee.Reducer.toList(2), ["date", "value"]
    ).get("list").getInfo()

    if not lst:
        st.warning("Não foi possível extrair a série temporal.")
        return pd.DataFrame()

    df = pd.DataFrame(lst, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")
