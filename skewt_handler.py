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
    Usa lógica robusta de índice de tempo para evitar erros de 'dados incompletos'.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # Formata a string de data/hora alvo para busca exata (Padrão Open-Meteo: ISO8601 sem Z)
    # Ex: "2025-12-05T12:00"
    target_time_str = f"{date_str}T{hour:02d}:00"

    # 1. Decisão Inteligente da Fonte de Dados
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Se for recente (<= 5 dias), usa Forecast. Se antigo, usa Archive.
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
        "end_date": date_str,
        "hourly": hourly_vars,
        "timeformat": "iso8601", # Força formato ISO para facilitar a busca
        "timezone": "UTC"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data or "time" not in data["hourly"]:
            st.warning(f"A API ({api_type}) não retornou a estrutura de tempo esperada.")
            return None
            
        timestamps = data["hourly"]["time"]
        
        # --- BUSCA DO ÍNDICE CORRETO (CORREÇÃO PRINCIPAL) ---
        try:
            # Procura a posição exata da hora desejada na lista
            idx = timestamps.index(target_time_str)
        except ValueError:
            st.warning(f"Horário {target_time_str} não encontrado nos dados retornados pela API.")
            st.write("Horários disponíveis:", timestamps) # Debug para o usuário ver
            return None
        # -----------------------------------------------------

        # Estrutura os dados
        profile_data = []
        for level in PRESSURE_LEVELS:
            try:
                # Usa .get() para evitar erros se a variável específica faltar
                t_list = data["hourly"].get(f"temperature_{level}hPa")
                rh_list = data["hourly"].get(f"relative_humidity_{level}hPa")
                ws_list = data["hourly"].get(f"wind_speed_{level}hPa")
                wd_list = data["hourly"].get(f"wind_direction_{level}hPa")

                # Se alguma lista inteira faltar, pula o nível
                if not all([t_list, rh_list, ws_list, wd_list]):
                    continue

                t = t_list[idx]
                rh = rh_list[idx]
                ws = ws_list[idx]
                wd = wd_list[idx]
                
                # Valida se os dados não são nulos
                if t is not None and rh is not None:
                    profile_data.append({
                        "pressure": level,
                        "temperature": float(t),
                        "relative_humidity": float(rh),
                        "wind_speed": float(ws),
                        "wind_direction": float(wd)
                    })
            except (IndexError, TypeError, ValueError):
                continue
        
        if not profile_data:
            st.warning(f"Dados encontrados, mas vazios para o horário {hour}:00 UTC.")
            return None
        
        df = pd.DataFrame(profile_data)
        df.attrs['source'] = "Previsão (Recente)" if api_type == "forecast" else "ERA5 (Histórico)"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão/processamento ({api_type}): {e}")
        return None
