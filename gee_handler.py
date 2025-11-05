# ==================================================================================
# gee_handler.py — Clima-Cast-Crepaldi (versão com extremos espaciais - nov/2025)
# ==================================================================================
# Recursos:
#   ✅ Conexão robusta com o Google Earth Engine (local ou service account)
#   ✅ Dados do ERA5-LAND (DAILY_AGGR)
#   ✅ Séries temporais com média, percentil 95 e máximo espacial
#   ✅ Backup comentado da versão original (caso queira reverter)
# ==================================================================================

import streamlit as st
import json
from collections import defaultdict
import ee
import geobr
import pandas as pd

# ------------------------------------------------------------------------------
# Inicialização padronizada do Google Earth Engine
# ------------------------------------------------------------------------------
PROJECT_ID = "gee-crepaldi-2025b"

def inicializar_gee():
    """Inicializa o Earth Engine com fallback para Service Account (Streamlit Cloud)."""
    try:
        ee.Initialize(project=PROJECT_ID)
        return "local"
    except Exception:
        try:
            creds_dict = dict(st.secrets["earthengine_service_account"])
            credentials = ee.ServiceAccountCredentials(
                creds_dict["client_email"], key_data=json.dumps(creds_dict)
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
        "band": "temperature_2m", "result_band": "temperature_2m",
        "unit": "°C", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 40,
                       "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00',
                                   '#FFFF00', '#FFA500', '#FF0000', '#800000']}
    },
    "Precipitação Total": {
        "band": "total_precipitation_sum", "result_band": "total_precipitation_sum",
        "unit": "mm", "aggregation": "sum",
        "vis_params": {"min": 0, "max": 500,
                       "palette": ['#FFFFFF', '#00FFFF', '#0000FF', '#00FF00',
                                   '#FFFF00', '#FF0000']}
    },
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m', 'v_component_of_wind_10m'],
        "result_band": "wind_speed", "unit": "m/s", "aggregation": "mean",
        "vis_params": {"min": 0, "max": 30,
                       "palette": ['#FFFFFF', '#B0E0E6', '#4682B4', '#DAA520',
                                   '#FF4500', '#8B0000']}
    }
}

# ------------------------------------------------------------------------------
# Dados geopolíticos locais (cacheados)
# ------------------------------------------------------------------------------
@st.cache_data
def get_brazilian_geopolitical_data_local():
    """Lê o arquivo JSON de municípios locais e organiza por UF."""
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

        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data.keys())}
        return sorted_geo_data, uf_name_map
    except Exception as e:
        st.error(f"Erro ao processar arquivo de municípios: {e}")
        return {}, {}

# ------------------------------------------------------------------------------
# Geometrias de interesse
# ------------------------------------------------------------------------------
def get_area_of_interest_geometry(session_state):
    """Obtém a geometria de interesse (Estado, Município, Polígono, Círculo)."""
    tipo = session_state.tipo_localizacao

    if tipo == "Estado":
        uf = session_state.estado.split(" - ")[-1]
        estados = geobr.read_state()
        gdf = estados[estados["abbrev_state"] == uf]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"abbrev_state": uf})
        return geom, feat

    elif tipo == "Município":
        uf = session_state.estado.split(" - ")[-1]
        muni = session_state.municipio
        gdf = geobr.read_municipality(code_muni=uf, year=2020)
        gdf = gdf[gdf["name_muni"] == muni]
        if gdf.empty:
            return None, None
        geojson = json.loads(gdf.to_json())["features"][0]["geometry"]
        geom = ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)
        feat = ee.Feature(geom, {"name_muni": muni, "abbrev_state": uf})
        return geom, feat

    elif tipo == "Círculo (Lat/Lon/Raio)":
        try:
            lat, lon, raio_km = session_state.latitude, session_state.longitude, session_state.raio
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

# ------------------------------------------------------------------------------
# Busca de imagem ERA5-LAND (mapas)
# ------------------------------------------------------------------------------
def get_era5_image(variable, start_date, end_date, geometry):
    """Busca e agrega imagens do ERA5-LAND."""
    config = ERA5_VARS.get(variable)
    if not config:
        return None

    bands = config.get("bands", config.get("band"))
    ic = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(bands)

    if ic.size().getInfo() == 0:
        st.warning("Sem dados para o período selecionado.")
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
# Amostragem para tabela (mapa)
# ------------------------------------------------------------------------------
@st.cache_data
def get_sampled_data_as_dataframe(img, geom, variable):
    """Extrai amostras do mapa como DataFrame."""
    import pandas as pd
    if variable not in ERA5_VARS:
        return pd.DataFrame()
    config = ERA5_VARS[variable]
    band = config["result_band"]
    unit = config["unit"]

    sample = img.select(band).sample(region=geom, scale=10000, numPixels=500, geometries=True)
    features = sample.getInfo().get("features", [])
    data = []
    for f in features:
        val = f["properties"].get(band)
        if val is not None:
            coords = f["geometry"]["coordinates"]
            data.append({"Longitude": coords[0], "Latitude": coords[1], f"{variable} ({unit})": val})
    return pd.DataFrame(data)

# ------------------------------------------------------------------------------
# SÉRIES TEMPORAIS (NOVA VERSÃO - com extremos espaciais)
# ------------------------------------------------------------------------------
@st.cache_data
def get_time_series_data(variable, start_date, end_date, geometry):
    """
    Extrai séries temporais diárias com estatísticas espaciais:
    - mean (média)
    - p95  (percentil 95)
    - max  (máximo)
    """
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    bands = config.get("bands", config.get("band"))

    ic = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(bands)

    # Para vento: calcula o módulo
    if variable == "Velocidade do Vento (10m)":
        def calc_ws(img):
            ws = img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config["result_band"])
            return img.addBands(ws)
        ic = ic.map(calc_ws)

    band = config["result_band"]

    def extract_stats(img):
        stats = img.select(band).reduceRegion(
            reducer=ee.Reducer.mean()
                .combine(ee.Reducer.percentile([95]), sharedInputs=True)
                .combine(ee.Reducer.max(), sharedInputs=True),
            geometry=geometry,
            scale=10000,
            bestEffort=True,
            maxPixels=1e9
        )
        mean = ee.Number(stats.get(f"{band}_mean"))
        p95 = ee.Number(stats.get(f"{band}_p95"))
        maxv = ee.Number(stats.get(f"{band}_max"))

        if config["unit"] == "°C":
            mean, p95, maxv = mean.subtract(273.15), p95.subtract(273.15), maxv.subtract(273.15)
        elif config["unit"] == "mm":
            mean, p95, maxv = mean.multiply(1000), p95.multiply(1000), maxv.multiply(1000)

        return img.set("date", img.date().format("YYYY-MM-dd")) \
                  .set("mean", mean).set("p95", p95).set("max", maxv)

    ts = ic.select(band).map(extract_stats)
    data = ts.reduceColumns(ee.Reducer.toList(4), ["date", "mean", "p95", "max"]).get("list").getInfo()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=["date", "mean", "p95", "max"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")

# ------------------------------------------------------------------------------
# 🔙 VERSÃO ORIGINAL (para restaurar se desejar)
# ------------------------------------------------------------------------------
"""
@st.cache_data
def get_time_series_data(variable, start_date, end_date, geometry):
    '''Versão original simples — apenas média diária.'''
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    bands = config.get('bands', config.get('band'))
    ic = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').filterDate(
        start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    ).select(bands)
    if variable == 'Velocidade do Vento (10m)':
        def ws(img): return img.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
        ic = ic.map(lambda i: i.addBands(ws(i)))
    def extract(img):
        val = img.select(config['result_band']).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=10000
        ).get(config['result_band'])
        v = ee.Number(val)
        if config['unit'] == '°C': v = v.subtract(273.15)
        elif config['unit'] == 'mm': v = v.multiply(1000)
        return img.set('date', img.date().format('YYYY-MM-dd')).set('value', v)
    ts = ic.map(extract)
    lst = ts.reduceColumns(ee.Reducer.toList(2), ['date', 'value']).get('list').getInfo()
    df = pd.DataFrame(lst, columns=['date', 'value'])
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date')
"""
