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
    Usa lógica Híbrida (Forecast/Archive) baseada em índice horário simples.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Decisão Inteligente da Fonte de Dados
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Se for recente (<= 5 dias), usa Forecast (GFS/IFS). Se antigo, usa Archive (ERA5).
    if delta_dias <= 5:
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

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data:
            st.warning(f"A API ({api_type}) não retornou dados.")
            return None
            
        # Como pedimos start_date == end_date, a API retorna exatamente 24 horas (indices 0 a 23)
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
                
                # Se a lista não existir, pula
                if t_list is None: continue

                # Pega o valor no índice da hora
                t = t_list[idx]
                rh = rh_list[idx]
                ws = ws_list[idx]
                wd = wd_list[idx]
                
                # Só adiciona se a temperatura for válida (não nula)
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
            st.warning(f"Dados vazios para o horário {hour}:00 UTC (API: {api_type}). Tente outro horário.")
            return None
        
        df = pd.DataFrame(profile_data)
        # Metadado para título do gráfico
        df.attrs['source'] = "Previsão/GFS" if api_type == "forecast" else "ERA5/Histórico"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None
