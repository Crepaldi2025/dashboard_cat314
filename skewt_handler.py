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
    Usa lógica Híbrida com margem de segurança maior para evitar gaps do ERA5.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Decisão Inteligente da Fonte de Dados
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # ALTERAÇÃO AQUI: Aumentamos a margem para 14 dias.
    # O ERA5 pode demorar 5-7 dias. A API Forecast segura dados passados recentes (Analysis)
    # sem gaps. Isso evita cair no "limbo" entre o Forecast e o Archive.
    if delta_dias <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "archive"
    
    # Monta lista de variáveis
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
        "end_date": date_str, # Garante que pedimos apenas 1 dia (00h-23h)
        "hourly": hourly_vars,
        "timeformat": "unixtime",
        "timezone": "UTC"
    }
    
    # Se for forecast buscando passado, precisamos habilitar past_days (embora start/end resolvam na v1, é bom garantir)
    if api_type == "forecast" and delta_dias > 0:
        params["past_days"] = delta_dias + 1

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data:
            st.warning(f"A API ({api_type}) não retornou dados.")
            return None
            
        # O índice é simplesmente a hora solicitada.
        idx = int(hour)
        
        # Validação simples de limites
        timestamps = data["hourly"].get("time", [])
        if idx >= len(timestamps):
            st.warning("Hora solicitada fora do intervalo retornado pela API.")
            return None

        # Estrutura os dados
        profile_data = []
        for level in PRESSURE_LEVELS:
            try:
                # Busca as listas de dados
                t_list = data["hourly"].get(f"temperature_{level}hPa")
                rh_list = data["hourly"].get(f"relative_humidity_{level}hPa")
                ws_list = data["hourly"].get(f"wind_speed_{level}hPa")
                wd_list = data["hourly"].get(f"wind_direction_{level}hPa")
                
                if t_list is None: continue

                t = t_list[idx]
                rh = rh_list[idx]
                ws = ws_list[idx]
                wd = wd_list[idx]
                
                if t is not None:
                    profile_data.append({
                        "pressure": level,
                        "temperature": float(t),
                        "relative_humidity": float(rh) if rh is not None else 0,
                        "wind_speed": float(ws) if ws is not None else 0,
                        "wind_direction": float(wd) if wd is not None else 0
                    })
            except (IndexError, TypeError):
                continue
        
        if not profile_data:
            st.warning(f"Dados vazios para o horário {hour}:00 UTC (API: {api_type}). Tente mudar a data em +/- 1 dia.")
            return None
        
        df = pd.DataFrame(profile_data)
        df.attrs['source'] = "Previsão/Análise (Recente)" if api_type == "forecast" else "ERA5 (Consolidado)"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None
