# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# Níveis de pressão padrão
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150, 100]

def get_vertical_profile_data(lat, lon, date_obj, hour):
    """
    Busca dados de perfil vertical. 
    - Usa 'Archive API' (ERA5) para datas antigas (> 5 dias).
    - Usa 'Forecast API' (GFS/Models) para datas recentes (<= 5 dias) para evitar gap de dados.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Decisão Inteligente da Fonte de Dados
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Se for recente (menos de 6 dias), usa a API de Previsão/Tempo Real
    if delta_dias <= 5:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "archive"
    
    # Monta a lista de variáveis
    variables = []
    for level in PRESSURE_LEVELS:
        variables.append(f"temperature_{level}hPa")
        variables.append(f"relative_humidity_{level}hPa")
        variables.append(f"wind_speed_{level}hPa")
        variables.append(f"wind_direction_{level}hPa")
    
    hourly_vars = ",".join(variables)
    
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
        
        # Validações de Segurança
        if "hourly" not in data:
            st.warning(f"A API ({api_type}) não retornou dados.")
            return None
            
        timestamps = data["hourly"].get("time", [])
        if not timestamps:
            st.warning("Lista de horários vazia.")
            return None

        # O índice 'hour' corresponde à hora solicitada (0 a 23)
        idx = int(hour)
        if idx >= len(timestamps):
            st.warning(f"Hora solicitada ({idx}) não disponível nos dados retornados.")
            return None

        # Estrutura os dados para o DataFrame
        profile_data = []
        for level in PRESSURE_LEVELS:
            try:
                t = data["hourly"].get(f"temperature_{level}hPa", [])[idx]
                rh = data["hourly"].get(f"relative_humidity_{level}hPa", [])[idx]
                ws = data["hourly"].get(f"wind_speed_{level}hPa", [])[idx]
                wd = data["hourly"].get(f"wind_direction_{level}hPa", [])[idx]
                
                if t is not None:
                    profile_data.append({
                        "pressure": level,
                        "temperature": t,
                        "relative_humidity": rh,
                        "wind_speed": ws,
                        "wind_direction": wd
                    })
            except (IndexError, TypeError):
                continue
        
        if not profile_data:
            st.warning("Dados verticais incompletos para gerar o gráfico.")
            return None
        
        df = pd.DataFrame(profile_data)
        
        # Adiciona metadados para informar a fonte no gráfico se necessário
        df.attrs['source'] = "Previsão (Recente)" if api_type == "forecast" else "ERA5 (Histórico)"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão com Open-Meteo ({api_type}): {e}")
        return None
