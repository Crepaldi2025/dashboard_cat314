# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st

# Níveis de pressão padrão disponíveis no ERA5 (Open-Meteo)
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150, 100]

def get_vertical_profile_data(lat, lon, date, hour):
    """
    Busca dados de perfil vertical do ERA5 via Open-Meteo API.
    """
    date_str = date.strftime('%Y-%m-%d')
    
    # Monta a lista de variáveis para a API
    variables = []
    for level in PRESSURE_LEVELS:
        variables.append(f"temperature_{level}hPa")
        variables.append(f"relative_humidity_{level}hPa")
        variables.append(f"wind_speed_{level}hPa")
        variables.append(f"wind_direction_{level}hPa")
    
    hourly_vars = ",".join(variables)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": hourly_vars,
        "timeformat": "unixtime",
        "timezone": "UTC"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Encontrar o índice da hora desejada
        # A API retorna dados horários (0-23). O índice 'hour' corresponde à hora (0=00h, 1=01h...)
        # Validação simples:
        if "hourly" not in data:
            return None
            
        timestamps = data["hourly"]["time"]
        # O índice é simplesmente a hora, pois pedimos apenas 1 dia
        idx = hour 
        
        if idx >= len(timestamps):
            return None

        # Estruturar dados para DataFrame Vertical
        profile_data = []
        for level in PRESSURE_LEVELS:
            temp = data["hourly"][f"temperature_{level}hPa"][idx]
            rh = data["hourly"][f"relative_humidity_{level}hPa"][idx]
            ws = data["hourly"][f"wind_speed_{level}hPa"][idx]
            wd = data["hourly"][f"wind_direction_{level}hPa"][idx]
            
            if temp is not None:
                profile_data.append({
                    "pressure": level,
                    "temperature": temp,
                    "relative_humidity": rh,
                    "wind_speed": ws,
                    "wind_direction": wd
                })
        
        df = pd.DataFrame(profile_data)
        return df.sort_values(by="pressure", ascending=False) # Ordena do solo para o topo
        
    except Exception as e:
        st.error(f"Erro ao buscar dados do perfil vertical: {e}")
        return None