# ==================================================================================
# main.py - CLIMA CAST CRPALDI
# ==================================================================================
import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
from datetime import datetime, timedelta

# --- Importação dos Módulos Personalizados ---
import map_visualizer       # Seu módulo de mapas (corrigido)
import charts_visualizer    # Seu módulo de gráficos (corrigido)
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
        ee.Initialize(project='SEU_PROJETO_GEE_AQUI') # <--- Coloque seu projeto se necessário, ou deixe vazio se usar auth padrão
    except Exception as e:
        st.warning("Tentando autenticar no GEE...")
        ee.Authenticate()
        ee.Initialize()

initialize_gee()

# ==================================================================================
# 2. DICIONÁRIO DE VARIÁVEIS E PARÂMETROS
# ==================================================================================
# Aqui definimos como buscar e colorir cada variável climática
DATASETS = {
    "Temperatura do Ar (2m)": {
        "collection": "ECMWF/ERA5_LAND/HOURLY",
        "band": "temperature_2m",
        "reducer": "mean",
        "scale": 0, # Kelvin para Celsius (-273.15)
        "offset": -273.15,
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
        "collection": "JAXA/GPM_L3/GSMaP/v6/operational", # Exemplo GPM (ou use CHIRPS)
        "band": "hourlyPrecipRate",
        "reducer": "sum", # Chuva se soma
        "scale": 1,
        "offset": 0,
        "unit": "mm",
        "vis_params": {
            "min": 0, "max": 30, # Ajuste conforme necessidade
            "palette": ['white', 'blue', 'darkblue', 'purple'],
            "caption": "Precipitação Acumulada (mm)"
        }
    },
    # Módulo Especial (Não usa collection padrão)
    "Densidade de Raios": {
        "special_module": True, 
        "unit": "flashes",
        # Parâmetros visuais vêm do módulo
    }
}

# ==================================================================================
# 3. FUNÇÕES DE PROCESSAMENTO DE DADOS
# ==================================================================================

def get_gee_image(dataset_key, start_date, end_date, roi):
    """Retorna a imagem processada (média/soma) recortada na ROI."""
    
    config = DATASETS[dataset_key]
    
    # 1. Caso Especial: Raios
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
        
    # Aplicar conversão de unidade (ex: K -> C)
    if config["offset"] != 0:
        img = img.add(config["offset"])
        
    return img.clip(roi)

def get_chart_data(dataset_key, start_date, end_date, roi):
    """Extrai série temporal para o gráfico."""
    config = DATASETS[dataset_key]
    
    # Se for raio, retornamos None por enquanto (gráfico de raios é complexo)
    if config.get("special_module"):
        return None
        
    # Coleção
    col = ee.ImageCollection(config["collection"])\
            .filterDate(start_date, end_date)\
            .filterBounds(roi)\
            .select(config["band"])
            
    # Função para extrair valor médio da região por imagem
    def extract_value(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10000, # Escala aproximada em metros (aumentar se for muito lento)
            bestEffort=True
        )
        # Adiciona data e valor
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'value': stats.get(config["band"])
        })
        
    series = col.map(extract_value).getInfo()
    
    # Converter para Pandas
    data_list = [feat['properties'] for feat in series['features']]
    df = pd.DataFrame(data_list)
    
    if not df.empty:
        # Aplicar offset no DataFrame também
        df['value'] = df['value'] + config["offset"]
        
    return df

# ==================================================================================
# 4. INTERFACE DO USUÁRIO (SIDEBAR)
# ==================================================================================
with st.sidebar:
    st.title("⛈️ Clima Cast Crpaldi")
    st.markdown("---")
    
    # A. Filtros de Data
    st.subheader("📅 Período de Análise")
    col_d1, col_d2 = st.columns(2)
    start_date = col_d1.date_input("Início", datetime.now() - timedelta(days=30))
    end_date = col_d2.date_input("Fim", datetime.now())
    
    # Converter para string GEE
    s_date = start_date.strftime("%Y-%m-%d")
    e_date = end_date.strftime("%Y-%m-%d")

    # B. Filtros de Localização
    st.subheader("📍 Localização (ROI)")
    # Default: Coordenadas próximas à UNIFEI / Itajubá
    lat = st.number_input("Latitude", value=-22.41, format="%.4f")
    lon = st.number_input("Longitude", value=-45.45, format="%.4f")
    buffer_km = st.slider("Raio de Abrangência (km)", 10, 500, 50)
    
    # Criar geometria GEE
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(buffer_km * 1000) # km para metros
    
    # C. Variável
    st.subheader("📡 Variável")
    var_selecionada = st.selectbox("Selecione o dado:", list(DATASETS.keys()))
    
    st.info("O sistema combina dados de satélite e reanálise em tempo real.")

# ==================================================================================
# 5. EXECUÇÃO PRINCIPAL (MAIN AREA)
# ==================================================================================

st.title(f"Análise de {var_selecionada}")
st.markdown(f"**Período:** {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")

# Processamento
with st.spinner("Processando imagens de satélite..."):
    # 1. Obter Imagem para Mapa
    ee_image = get_gee_image(var_selecionada, s_date, e_date, roi)
    
    # 2. Obter Dados para Gráfico
    df_chart = get_chart_data(var_selecionada, s_date, e_date, roi)
    
    # 3. Definir Parâmetros Visuais
    conf = DATASETS[var_selecionada]
    if conf.get("special_module"):
        vis_params = lightning_module.get_lightning_config() # Pega do módulo
    else:
        vis_params = conf["vis_params"]

# Abas de Visualização
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Interativo", "📈 Série Temporal", "🖼️ Mapa Estático (Export)"])

with tab1:
    # Chama o visualizador de mapa (map_visualizer.py)
    map_visualizer.create_interactive_map(ee_image, roi, vis_params, conf["unit"])

with tab2:
    if df_chart is not None and not df_chart.empty:
        # Chama o visualizador de gráficos (charts_visualizer.py)
        charts_visualizer.display_time_series_chart(df_chart, var_selecionada, conf["unit"])
    elif conf.get("special_module"):
        st.info("Gráfico de série temporal ainda não disponível para Densidade de Raios nesta versão.")
    else:
        st.warning("Não há dados suficientes para gerar o gráfico na região selecionada.")

with tab3:
    st.markdown("### Pré-visualização para Relatório")
    col_static, col_btn = st.columns([3, 1])
    
    # Botão para gerar mapa estático (pode ser lento, então deixamos manual)
    if col_btn.button("Gerar Mapa Estático"):
        with st.spinner("Gerando imagem de alta resolução..."):
            png_b64, jpg_b64, legend_b64 = map_visualizer.create_static_map(ee_image, roi, vis_params, conf["unit"])
            
            if png_b64:
                # Aqui você poderia juntar título + mapa + legenda usando a função stitch do map_visualizer
                # Para simplificar, mostramos o mapa e a legenda
                st.image(png_b64, caption="Mapa Gerado")
                if legend_b64:
                    st.image(legend_b64, caption="Legenda")
                
                st.success("Mapa gerado com sucesso!")
            else:
                st.error("Erro ao gerar mapa estático.")
    else:
        st.info("Clique no botão para renderizar o mapa estático de alta qualidade.")
