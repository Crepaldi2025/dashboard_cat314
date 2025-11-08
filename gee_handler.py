# ==================================================================================
# gee_handler.py (Corrigido v48)
# ==================================================================================
import streamlit as st
import json
from collections import defaultdict
import ee
import os
import geobr
import pandas as pd
from datetime import date # Importado para type hinting

# ==========================================================
# INICIALIZAÇÃO E AUTENTICAÇÃO (Idêntico)
# ==========================================================
def inicializar_gee():
    """
    Inicializa a API do Google Earth Engine.
    """
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
    """Alias de compatibilidade para inicializar_gee()"""
    return inicializar_gee()

# ==========================================================
# DEFINIÇÕES DE VARIÁVEIS (Modificado v48)
# ==========================================================

ERA5_VARS = {
    "Temperatura do Ar (2m)": {
        "band": "temperature_2m_mean", # < CORRIGIDO (usava 'temperature_2m' da v17)
        "result_band": "temperature_2m_mean", 
        "unit": "°C", 
        "aggregation": "mean",
        "vis_params": { 
            "min": 0, 
            "max": 40, 
            "palette": ['#000080', '#0000FF', '#00FFFF', '#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF4500', '#FF0000', '#800000'] 
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
            "palette": ['#ffffd9', '#edf8b1', '#c7e9b4', '#7fcdbb', '#41b6c4', '#1d91c0', '#225ea8', '#253494', '#081d58', '#081040']
        }
    },
    # --- INÍCIO DA CORREÇÃO v48 ---
    "Umidade Relativa (2m)": {
        # Pede a Temperatura (T) e Ponto de Orvalho (Td) médias diárias
        "bands": ["temperature_2m_mean", "dewpoint_temperature_2m_mean"], 
        "result_band": "relative_humidity", # Banda que vamos calcular
        "unit": "%", 
        "aggregation": "mean", # Vamos calcular a UR média do período
        "vis_params": { 
            "min": 30, 
            "max": 100, 
            # Paleta clássica (Seco: Marrom/Amarelo -> Úmido: Azul)
            "palette": ['#8B4513', '#FFA500', '#FFFF00', '#90EE90', '#87CEEB', '#0000FF', '#00008B']
        }
    },
    # --- FIM DA CORREÇÃO v48 ---
    "Velocidade do Vento (10m)": {
        "bands": ['u_component_of_wind_10m_mean', 'v_component_of_wind_10m_mean'], # < CORRIGIDO (usava bandas sem '_mean')
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
# CARREGAMENTO DE DADOS GEOGRÁFICOS (Idêntico)
# ==========================================================

@st.cache_data
def get_brazilian_geopolitical_data_local() -> tuple[dict, dict]:
    """
    Carrega os dados de estados e municípios do Brasil a partir de um
    arquivo JSON local (`municipios_ibge.json`).
    """
    arquivo = "municipios_ibge.json"
    geo_data = defaultdict(list)
    uf_name_map = {}

    try:
        if not os.path.exists(arquivo):
            st.warning(f"Arquivo '{arquivo}' não encontrado. Sidebar de municípios estará vazia.")
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
                            if uf_sigla and uf_nome and uf_sigla not in uf_name_map:
                                uf_name_map[uf_sigla] = uf_nome
                            nome_municipio = municipio.get('nome')
                            if uf_sigla and nome_municipio:
                                geo_data[uf_sigla].append(nome_municipio)
        
        elif isinstance(municipios_data, dict):
            geo_data = municipios_data.get("municipios_por_uf", {})
            uf_name_map = municipios_data.get("nomes_estados", {})

        sorted_geo_data = {uf: sorted(geo_data[uf]) for uf in sorted(geo_data.keys())}
        return sorted_geo_data, uf_name_map

    except Exception as e:
        st.error(f"Erro ao processar arquivo de municípios ({arquivo}): {e}")
        return {}, {}

@st.cache_data
def _load_all_states_gdf():
    """(Helper Interno) Carrega e cacheia o shapefile de todos os estados (via geobr)."""
    try:
        return geobr.read_state()
    except Exception as e:
        st.error(f"Falha ao carregar dados de estados (geobr): {e}")
        return None

@st.cache_data
def _load_municipalities_gdf(uf_sigla: str):
    """(Helper Interno) Carrega e cacheia os municípios de uma UF (via geobr)."""
    try:
        return geobr.read_municipality(code_muni=uf_sigla, year=2020)
    except Exception as e:
        st.error(f"Falha ao carregar municípios de {uf_sigla} (geobr): {e}")
        return None

# ==========================================================
# PROCESSAMENTO DE GEOMETRIA (Idêntico)
# ==========================================================

def get_area_of_interest_geometry(session_state) -> tuple[ee.Geometry, ee.Feature]:
    """
    Obtém a geometria GEE (ee.Geometry) e o Feature GEE (ee.Feature)
    com base nas seleções do usuário no `st.session_state`.
    """
    tipo_loc = session_state.get('tipo_localizacao', 'Estado')
    
    try:
        if tipo_loc == "Estado":
            estado_selecionado_str = session_state.get('estado', 'Selecione...')
            if estado_selecionado_str == "Selecione...": return None, None
            uf_sigla = estado_selecionado_str.split(' - ')[-1]
            
            todos_estados_gdf = _load_all_states_gdf() 
            if todos_estados_gdf is None: return None, None
            
            estado_gdf = todos_estados_gdf[todos_estados_gdf['abbrev_state'] == uf_sigla]
            if estado_gdf.empty: return None, None
            
            estado_geojson = json.loads(estado_gdf.to_json())['features'][0]['geometry']
            ee_geometry = ee.Geometry(estado_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {'abbrev_state': uf_sigla})
            return ee_geometry, ee_feature

        elif tipo_loc == "Município":
            estado_selecionado_str = session_state.get('estado', 'Selecione...')
            municipio_nome = session_state.get('municipio', 'Selecione...')
            if estado_selecionado_str == "Selecione..." or municipio_nome == "Selecione...":
                return None, None
            
            uf_sigla = estado_selecionado_str.split(' - ')[-1]
            with st.spinner(f"Buscando geometria para {municipio_nome}, {uf_sigla}..."):
                municipios_do_estado_gdf = _load_municipalities_gdf(uf_sigla)
                if municipios_do_estado_gdf is None: return None, None

            municipio_gdf = municipios_do_estado_gdf[municipios_do_estado_gdf['name_muni'] == municipio_nome]
            if municipio_gdf.empty:
                st.warning(f"Não foi possível encontrar a geometria para '{municipio_nome}'.")
                return None, None
            
            municipio_geojson = json.loads(municipio_gdf.to_json())['features'][0]['geometry']
            ee_geometry = ee.Geometry(municipio_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry, {'name_muni': municipio_nome, 'abbrev_state': uf_sigla})
            return ee_geometry, ee_feature

        elif tipo_loc == "Círculo (Lat/Lon/Raio)":
            latitude = session_state.latitude
            longitude = session_state.longitude
            raio_km = session_state.raio
            ponto_central = ee.Geometry.Point([longitude, latitude])
            raio_em_metros = raio_km * 1000
            ee_geometry = ponto_central.buffer(raio_em_metros)
            ee_feature = ee.Feature(ee_geometry, {'latitude': latitude, 'longitude': longitude, 'raio_km': raio_km})
            return ee_geometry, ee_feature
                
        elif tipo_loc == "Polígono":
            if 'drawn_geometry' not in session_state or not session_state.drawn_geometry:
                return None, None
            
            polygon_geojson = session_state.drawn_geometry
            ee_geometry = ee.Geometry(polygon_geojson, proj='EPSG:4326', geodesic=False)
            ee_feature = ee.Feature(ee_geometry)
            return ee_geometry, ee_feature
    
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar a geometria da área: {e}")
        return None, None

    return None, None

# ==========================================================
# PROCESSAMENTO DE DADOS GEE (MAPAS E SÉRIES)
# ==========================================================

# --- INÍCIO DA CORREÇÃO v48 (Função helper de UR) ---
def _calculate_rh(image):
    """
    Função GEE (server-side) para calcular a Umidade Relativa (%) a 
    partir de T_mean e Td_mean (em Kelvin).
    
    Usa a fórmula August-Roche-Magnus.
    """
    T = image.select('temperature_2m_mean').subtract(273.15) # K -> C
    Td = image.select('dewpoint_temperature_2m_mean').subtract(273.15) # K -> C
    
    # e_s = 6.11 * exp((17.625 * T_C) / (243.04 + T_C))
    es = T.multiply(17.625).divide(T.add(243.04)).exp().multiply(6.11)
    # e = 6.11 * exp((17.625 * Td_C) / (243.04 + Td_C))
    e = Td.multiply(17.625).divide(Td.add(243.04)).exp().multiply(6.11)
    
    # RH = (e / e_s) * 100
    rh = e.divide(es).multiply(100).rename('relative_humidity')
    
    # Garante que RH não passe de 100
    return image.addBands(rh.min(ee.Image.constant(100)))
# --- FIM DA CORREÇÃO v48 ---

def get_era5_image(variable: str, start_date: date, end_date: date, 
                   geometry: ee.Geometry) -> ee.Image:
    """
    Busca, processa e agrega dados do ERA5-Land para geração de mapas.
    (v48) - Adiciona lógica para calcular UR se solicitado.
    """
    if variable not in ERA5_VARS: return None
    config = ERA5_VARS[variable]
    bands_to_select = config.get('bands', config.get('band'))
    
    try:
        image_collection = (
            ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .select(bands_to_select)
        )
        
        if image_collection.size().getInfo() == 0:
            st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
            return None

        # --- INÍCIO DA CORREÇÃO v48 ---
        # Cálculo especial para Vento ou Umidade Relativa
        if variable == "Velocidade do Vento (10m)":
            def calculate_wind_speed(image):
                wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
                return image.addBands(wind_speed)
            image_collection = image_collection.map(calculate_wind_speed)
        
        elif variable == "Umidade Relativa (2m)":
            image_collection = image_collection.map(_calculate_rh)
        # --- FIM DA CORREÇÃO v48 ---
            
        # Agregação temporal (Média ou Soma)
        if config['aggregation'] == 'mean':
            aggregated_image = image_collection.select(config['result_band']).mean()
        elif config['aggregation'] == 'sum':
            aggregated_image = image_collection.select(config['result_band']).sum()
        else:
            aggregated_image = None
            
        if aggregated_image:
            final_image = aggregated_image.clip(geometry).float()
            
            # Correção de unidades (só para T e P, UR já está em %)
            if config['unit'] == "°C": final_image = final_image.subtract(273.15)
            if config['unit'] == "mm": final_image = final_image.multiply(1000)
            
            if final_image.bandNames().size().getInfo() == 0: return None
            return final_image
        
        return None
    
    except Exception as e:
        st.error(f"Erro ao processar imagem do GEE: {e}")
        return None

def get_sampled_data_as_dataframe(ee_image: ee.Image, geometry: ee.Geometry, 
                                  variable: str) -> pd.DataFrame:
    """
    Amostra a imagem GEE em pontos aleatórios dentro da geometria para
    criar uma tabela de dados (DataFrame).
    """
    if variable not in ERA5_VARS: return pd.DataFrame()
    config = ERA5_VARS[variable]
    band_name = config['result_band']
    unit = config['unit']
    
    try:
        sample = ee_image.select(band_name).sample(
            region=geometry, 
            scale=10000, 
            numPixels=500, 
            geometries=True 
        )
        
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
    
    except Exception as e:
        st.error(f"Erro ao amostrar dados para tabela: {e}")
        return pd.DataFrame()

def get_time_series_data(variable: str, start_date: date, end_date: date, 
                         geometry: ee.Geometry) -> pd.DataFrame:
    """
    Extrai a série temporal diária (média espacial) para uma dada geometria.
    (v48) - Adiciona lógica para calcular UR se solicitado.
    """
    if variable not in ERA5_VARS:
        return pd.DataFrame()

    config = ERA5_VARS[variable]
    bands_to_select = config.get("bands", config.get("band"))

    try:
        collection = (
            ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .select(bands_to_select)
        )

        if collection.size().getInfo() == 0:
            st.warning("Não há dados ERA5-Land disponíveis para o período selecionado.")
            return pd.DataFrame()

        band_name_for_reduction = config["result_band"] # Nome padrão
        
        # --- INÍCIO DA CORREÇÃO v48 ---
        if variable == "Velocidade do Vento (10m)":
            def calculate_wind_speed(image):
                wind_speed = image.pow(2).reduce(ee.Reducer.sum()).sqrt().rename(config['result_band'])
                return image.addBands(wind_speed)
            collection = collection.map(calculate_wind_speed)
        
        elif variable == "Umidade Relativa (2m)":
            collection = collection.map(_calculate_rh)
        
        else:
            # Renomeia a banda (lógica antiga)
            collection = collection.map(lambda img: img.rename(band_name_for_reduction))
        # --- FIM DA CORREÇÃO v48 ---
            
        def extract_value(image):
            stats = image.select(band_name_for_reduction).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=9000, 
                bestEffort=True,
                maxPixels=1e9
            )
            mean_value = stats.get(band_name_for_reduction)

            # Correção de unidades (só para T e P, UR já está em %)
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
    
    except Exception as e:
        st.error(f"Erro ao extrair série temporal: {e}")
        return pd.DataFrame()


# ==========================================================
# FUNÇÃO DE COMPATIBILIDADE (Legado)
# ==========================================================

def get_gee_data(dataset, band, start_date, end_date, feature):
    """(Função legada) Mantém compatibilidade com versões antigas do main.py."""
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
        st.error(f"⚠️ Falha ao processar dados legados do GEE: {e}")
        return None
