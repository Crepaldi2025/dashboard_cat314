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
    Busca dados de perfil vertical (Temp, UR, Vento U/V).
    Usa componentes U/V do vento para compatibilidade total com o ERA5 Archive.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Decisão Inteligente da Fonte de Dados
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Margem de segurança de 14 dias para garantir dados consolidados no Archive
    if delta_dias <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "archive"
    
    # Monta lista de variáveis (USANDO COMPONENTES U/V)
    variables = []
    for level in PRESSURE_LEVELS:
        variables.append(f"temperature_{level}hPa")
        variables.append(f"relative_humidity_{level}hPa")
        variables.append(f"u_component_of_wind_{level}hPa")
        variables.append(f"v_component_of_wind_{level}hPa")
    
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
    
    if api_type == "forecast" and delta_dias > 0:
        params["past_days"] = delta_dias + 1

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data:
            st.warning(f"A API ({api_type}) não retornou dados.")
            return None
            
        idx = int(hour)
        timestamps = data["hourly"].get("time", [])
        if idx >= len(timestamps):
            st.warning("Hora solicitada fora do intervalo retornado.")
            return None

        # Estrutura os dados
        profile_data = []
        for level in PRESSURE_LEVELS:
            try:
                # Busca as listas de dados usando nomes de variáveis corretos
                t_list = data["hourly"].get(f"temperature_{level}hPa")
                rh_list = data["hourly"].get(f"relative_humidity_{level}hPa")
                u_list = data["hourly"].get(f"u_component_of_wind_{level}hPa")
                v_list = data["hourly"].get(f"v_component_of_wind_{level}hPa")
                
                # Se a lista de temperatura não existir, algo crítico falhou
                if t_list is None: continue

                t = t_list[idx]
                rh = rh_list[idx] if rh_list else None
                u = u_list[idx] if u_list else None
                v = v_list[idx] if v_list else None
                
                # Só adiciona se a temperatura for válida
                if t is not None:
                    profile_data.append({
                        "pressure": level,
                        "temperature": float(t),
                        "relative_humidity": float(rh) if rh is not None else 0.0,
                        # Se vento for None (ex: subterrâneo), assume 0 para não quebrar o gráfico
                        "u_component": float(u) if u is not None else 0.0,
                        "v_component": float(v) if v is not None else 0.0
                    })
            except (IndexError, TypeError):
                continue
        
        if not profile_data:
            st.warning(f"Dados vazios para {date_str} {hour}:00 UTC. Tente outra data.")
            return None
        
        df = pd.DataFrame(profile_data)
        df.attrs['source'] = "Previsão/Análise" if api_type == "forecast" else "ERA5 (Histórico)"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None
