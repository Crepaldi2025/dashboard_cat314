# ==================================================================================
# main.py - CLIMA CAST CRPALDI
# ==================================================================================
import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
from datetime import datetime, timedelta

# --- Importação dos Módulos Personalizados ---
import map_visualizer       # Seu módulo de mapas
import charts_visualizer    # Seu módulo de gráficos
import lightning_module     # Novo módulo de raios

# ==================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO
# ==================================================================================
st.set_page_config(
    page_title="Clima Cast Crpaldi",
    page_icon="⛈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do GEE
@st.cache_resource
def initialize_gee():
    try:
        # Tenta usar o projeto padrão ou credenciais salvas
        ee.Initialize(project='SEU_PROJETO_GEE_AQUI') # <--- Deixe vazio se não souber o projeto
    except Exception as e:
        st.warning("Autenticando no Google Earth Engine...")
        ee.Authenticate()
        ee.Initialize()

initialize_gee()

# ==================================================================================
# 2. DICIONÁRIO DE VARIÁVEIS E PARÂMETROS
# ==================================================================================
DATASETS = {
    "Temperatura do Ar (2m)": {
        "collection": "ECMWF/ERA5_LAND/HOURLY",
        "band": "temperature_2m",
        "reducer": "mean",
        "scale": 0,
        "offset": -273.15, # Kelvin -> Celsius
        "unit": "°C",
        "vis_params": {
            "min": 10, "max": 35,
            "palette": ['blue', 'cyan', 'lime', 'yellow', 'red'],
            "caption": "Temperatura Média (°C)"
        }
    },
    "Temperatura do Ponto de Orvalho": {
        "collection": "ECMWF/ERA5_LAND/HOURLY",
        "band": "dewpoint_temperature_2m",
        "reducer": "mean",
        "scale": 0,
        "offset": -273.15,
        "unit": "°C",
        "vis_params": {
            "min": 5, "max": 25,
            "palette": ['#a50026', '#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695'],
            "caption": "Temp. Ponto de Orvalho (°C)"
        }
    },
    "Precipitação Total": {
        "collection": "JAXA/GPM_L3/GSMaP/v6/operational",
        "band": "hourlyPrecipRate",
        "reducer": "sum",
        "scale": 1,
        "offset": 0,
        "unit": "mm",
        "vis_params": {
            "min": 0, "max": 50, # Ajuste conforme a época do ano
            "palette": ['white', 'blue', 'darkblue', 'purple'],
            "caption": "Precipitação Acumulada (mm)"
        }
    },
    # Módulo Especial de Raios
    "Densidade de Raios": {
        "special_module": True, 
        "unit": "flashes",
        # Os parâmetros visuais (palette, min, max) vêm do arquivo lightning_module.py
    }
}

# ==================================================================================
# 3. FUNÇÕES DE PROCESSAMENTO
# ==================================================================================

def get_gee_image(dataset_key, start_date, end_date, roi):
    """Retorna a imagem processada recortada na ROI."""
    config = DATASETS[dataset_key]
    
    # 1. Caso Especial: Raios (usa o módulo novo)
    if config.get("special_module"):
        return lightning_module.compute_lightning_density(roi, start_date, end_date)

    # 2. Caso Padrão: Coleções Climáticas
    col = ee.ImageCollection(config["collection"])\
            .filterDate(start_date, end_date)\
            .filterBounds(roi)\
            .select(config["band"])
            
    if config["reducer"] == "mean":
        img = col.mean()
    elif config["reducer"] == "sum":
        img = col.sum()
    else:
        img = col.median()
        
    if config["offset"] != 0:
        img = img.add(config["offset"])
        
    return img.clip(roi)

def get_chart_data(dataset_key, start_date, end_date, roi):
    """Extrai dados para o gráfico de série temporal."""
    config = DATASETS[dataset_key]
    
    # Se for módulo especial (raios), não geramos gráfico por enquanto
    if config.get("special_module"):
        return None
        
    col = ee.ImageCollection(config["collection"])\
            .filterDate(start_date, end_date)\
            .filterBounds(roi)\
            .select(config["band"])
            
    def extract_value(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10000, 
            bestEffort=True
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'value': stats.get(config["band"])
        })
        
    series = col.map(extract_value).getInfo()
    data_list = [feat['properties'] for feat in series['features']]
    df = pd.DataFrame(data_list)
    
    if not df.empty:
        df['value'] = df['value'] + config["offset"]
        
    return df

# ==================================================================================
# 4. INTERFACE DO USUÁRIO
# ==================================================================================
with st.sidebar:
    st.title("⛈️ Clima Cast Crpaldi")
    st.markdown("---")
    
    # A. Filtros de Data
    st.subheader("📅 Período de Análise")
    col_d1, col_d2 = st.columns(2)
    start_date = col_d1.date_input("Início", datetime.now() - timedelta(days=30))
    end_date = col_d2.date_input("Fim", datetime.now())
    
    s_date = start_date.strftime("%Y-%m-%d")
    e_date = end_date.strftime("%Y-%m-%d")

    # B. Filtros de Localização
    st.subheader("📍 Localização (ROI)")
    lat = st.number_input("Latitude", value=-22.41, format="%.4f")
    lon = st.number_input("Longitude", value=-45.45, format="%.4f")
    buffer_km = st.slider("Raio de Abrangência (km)", 10, 500, 50)
    
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(buffer_km * 1000)
    
    # C. Seletor de Variável
    st.subheader("📡 Variável")
    var_selecionada = st.selectbox("Selecione o dado:", list(DATASETS.keys()))
    
    st.info("Combinação de dados GOES, ERA5 e GPM.")

# ==================================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==================================================================================

st.title(f"Análise de {var_selecionada}")
st.markdown(f"**Período:** {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")

# Processamento
with st.spinner("Processando imagens de satélite..."):
    # 1. Imagem
    ee_image = get_gee_image(var_selecionada, s_date, e_date, roi)
    
    # 2. Dados Gráfico
    df_chart = get_chart_data(var_selecionada, s_date, e_date, roi)
    
    # 3. Configuração Visual
    conf = DATASETS[var_selecionada]
    if conf.get("special_module"):
        # Se for Raios, pega a configuração do módulo
        vis_params = lightning_module.get_lightning_config()
    else:
        vis_params = conf["vis_params"]

# Abas
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Interativo", "📈 Série Temporal", "🖼️ Mapa Estático (Export)"])

with tab1:
    # CORREÇÃO: Usamos ee.Feature(roi) para que o map_visualizer funcione corretamente
    map_visualizer.create_interactive_map(ee_image, ee.Feature(roi), vis_params, conf["unit"])

with tab2:
    if df_chart is not None and not df_chart.empty:
        charts_visualizer.display_time_series_chart(df_chart, var_selecionada, conf["unit"])
    elif conf.get("special_module"):
        st.info(f"O gráfico temporal para '{var_selecionada}' ainda não foi implementado.")
    else:
        st.warning("Não há dados suficientes para gerar o gráfico na região selecionada.")

with tab3:
    st.markdown("### Pré-visualização para Relatório")
    col_static, col_btn = st.columns([3, 1])
    
    if col_btn.button("Gerar Mapa Estático"):
        with st.spinner("Gerando imagem de alta resolução..."):
            # CORREÇÃO: Usamos ee.Feature(roi) aqui também
            png_b64, jpg_b64, legend_b64 = map_visualizer.create_static_map(ee_image, ee.Feature(roi), vis_params, conf["unit"])
            
            if png_b64:
                st.image(png_b64, caption="Mapa Gerado")
                if legend_b64:
                    st.image(legend_b64, caption="Legenda")
                st.success("Mapa gerado com sucesso!")
            else:
                st.error("Erro ao gerar mapa estático.")
    else:
        st.info("Clique no botão para renderizar o mapa estático.")
