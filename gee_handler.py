# ==================================================================================
# gee_handler.py — Clima-Cast-Crepaldi (versão estável antes do P95)
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import geobr
import pandas as pd

PROJECT_ID = "gee-crepaldi-2025b"

# ------------------------------------------------------------------------------
# Inicialização do GEE
# ------------------------------------------------------------------------------
def inicializar_gee():
    """Inicializa o Earth Engine (modo local ou service account)."""
    try:
        ee.Initialize(project=PROJECT_ID)
        return "local"
    except Exception:
        try:
            creds_dict = dict(st.secrets["earthengine_service_account"])
            credentials = ee.ServiceAccountCredentials(
                creds_dict["client_email"],
                key_data=json.dumps(creds_dict)
            )
            ee.Initialize(credentials, project=PROJECT_ID)
            return "service_account"
        except Exception as e:
            st.error(f"⚠️ Falha ao conectar com o Google Earth Engine: {e}")
            return None

# ------------------------------------------------------------------------------
# Configuração das variáveis ERA5-LAND
# ------------------------------------------------------------------------------
ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m",
        "result_band": "temperature_2m",
        "unit": "°C",
        "aggregation": "mean",
        "vis_params": {
            "min": 0, "max": 40,
            "palette": [
                "#000080", "#0000FF", "#00FFFF",
                "#00FF00", "#FFFF00", "#FFA500",
                "#FF0000", "#800000"
            ]
        }
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum",
        "result_band": "total_precipitation_sum",
        "unit": "mm",
        "aggregation": "sum",
        "vis_params": {
            "min": 0, "max": 500,
            "palette": [
                "#FFFFFF", "#00FFFF", "#0000FF",
                "#00FF00", "#FFFF00", "#FF0000"
            ]
        }
    },
    "Velocidade do Vento (10m)": {
        "bands": ["u_component_of_wind_10m", "v_component_of_wind_10m"],
        "result_band": "wind_speed",
        "unit": "m/s",
        "aggregation": "mean",
        "vis_params": {
            "min": 0, "max": 30,
            "palette": [
                "#FFFFFF", "#B0E0E6", "#4682B4",
                "#DAA520", "#FF4500", "#8B0000"
            ]
        }
    }
}

# ------------------------------------------------------------------------------
# Dados geopolíticos (cache)
# ------------------------------------------------------------------------------
@st.cache_data
def get_brazilian_geopolitical_data_local():
    """Carrega os dados geográficos locais (estados e municípios)."""
    try:
        with open("municipios_ibge.json", "r", encoding="utf-8") as f:
            municipios_data = json.load(f)

        geo_data = defaultdict(list)
        uf_name_map = {}
        for municipio in municipios_data:
            microrregiao = municipio.get("microrregiao")
            if microrregiao:
                mesorregiao = microrregiao.get("mesorregiao", {})
                uf_data = mesorregiao.get("UF", {})
                uf_sigla = uf_data.get("sigla")
                uf_nome = uf_data.get("nome")
                nome_municipio = municipio.get("nome")
                if uf_sigla and uf_nome:
                    uf_name_map[uf_sigla] = uf_nome
                if uf_sigla and nome_municipio:
                    geo_data[uf_sigla].append(nome_municipio)

        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data)}
        return sorted_geo_data, uf_name_map
    except Exception as e:
        st.error(f"Erro ao processar arquivo de municípios: {e}")
        return {}, {}

# ------------------------------------------------------------------------------
# Geometrias de interesse
# ------------------------------------------------------------------------------
def get_area_of_interest_geometry(session_state):
    """Obtém a geometria da área de interesse."""
    tipo_loc = session_state.tipo_localizacao

    if tipo_loc == "Estado":
        uf_sigla = session_state.estado.split(" - ")[-1]
        estados = geobr.read_state()
        gdf = estados[estados["abbrev_state"] == uf_sigla]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"abbrev_state": uf_sigla})
        return geom, feat

    elif tipo_loc == "Município":
        uf_sigla = session_state.estado.split(" - ")[-1]
        muni = session_state.municipio
        gdf = geobr.read_municipality(code_muni=uf_sigla, year=2020)
        gdf = gdf[gdf["name_muni"] == muni]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"name_muni": muni, "abbrev_state": uf_sigla})
        return geom, feat

    elif tipo_loc == "Círculo (Lat/Lon/Raio)":
        lat, lon, raio_km = session_state.latitude, session_state.longitude, session_state.raio
        ponto = ee.Geometry.Point([lon, lat])
        geom = ponto.buffer(raio_km * 1000)
        feat = ee.Feature(geom, {"latitude": lat, "longitude": lon, "raio_km": raio_km})
        return geom, feat

    elif tipo_loc == "Polígono":
        if "drawn_geometry" not in session_state:
            st.warning("Nenhum polígono desenhado.")
            return None, None
        geom = ee.Geometry(session_state.drawn_geometry, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom)
        return geom, feat

    return None, None

# ------------------------------------------------------------------------------
# Busca ERA5-LAND (mapas)
# ------------------------------------------------------------------------------
def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e processa imagem ERA5-LAND."""
    config = ERA5_VARS.get(variable)
    if not config:
        return None

    bands = config.get("bands", config.get("band"))
    ic = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(bands)

    if ic.size().getInfo() == 0:
        st.warning("Sem dados ERA5-Land disponíveis para o período selecionado.")
        return None

    if variable == "Velocidade do Vento (10m)":
        def calc_ws(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return img.addBands(ws)
        ic = ic.map(calc_ws)

    agg = config["aggregation"]
    if agg == "mean":
        img = ic.select(config["result_band"]).mean()
    elif agg == "sum":
        img = ic.select(config["result_band"]).sum()
    else:
        img = ic.select(config["result_band"]).first()

    img = img.clip(geometry).float()
    if config["unit"] == "°C":
        img = img.subtract(273.15)
    elif config["unit"] == "mm":
        img = img.multiply(1000)
    return img

# ------------------------------------------------------------------------------
# Amostragem de dados (para tabela)
# ------------------------------------------------------------------------------
@st.cache_data
def get_sampled_data_as_dataframe(img, geom, variable):
    """Amostra pixels e retorna DataFrame."""
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    band = config["result_band"]
    unit = config["unit"]

    sample = img.select(band).sample(region=geom, scale=10000, numPixels=500, geometries=True)
    features = sample.getInfo().get("features", [])
    if not features:
        return pd.DataFrame()

    data = []
    for f in features:
        val = f["properties"].get(band)
        if val is not None:
            coords = f["geometry"]["coordinates"]
            data.append({
                "Longitude": coords[0],
                "Latitude": coords[1],
                f"{variable} ({unit})": val
            })
    return pd.DataFrame(data)

# ------------------------------------------------------------------------------
# Série Temporal (média diária)
# ------------------------------------------------------------------------------
@st.cache_data
def get_time_series_data(variable, start_date, end_date, geometry):
    """Extrai série temporal de média diária."""
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

    def extract_value(img):
        mean_value = img.select(config["result_band"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000
        ).get(config["result_band"])

        val = ee.Number(mean_value)
        if config["unit"] == "°C":
            val = val.subtract(273.15)
        elif config["unit"] == "mm":
            val = val.multiply(1000)

        return img.set("date", img.date().format("YYYY-MM-dd")).set("value", val)

    ts = ic.map(extract_value)
    data = ts.reduceColumns(ee.Reducer.toList(2), ["date", "value"]).get("list").getInfo()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df
