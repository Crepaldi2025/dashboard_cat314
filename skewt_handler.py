# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import math

# Níveis padrão
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150, 100]

def _fetch(url, params):
    """Tenta buscar dados e retorna JSON ou None se falhar."""
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except: 
        return None

def get_vertical_profile_data(lat, lon, date_obj, hour):
    date_str = date_obj.strftime('%Y-%m-%d')
    delta = (datetime.now().date() - date_obj).days
    
    # Seleção de API (Forecast vs Archive)
    if delta <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive"

    # --- TENTATIVA 1: Variáveis com underscore (Padrão Forecast) ---
    vars_v1 = []
    for l in PRESSURE_LEVELS:
        vars_v1.extend([f"temperature_{l}hPa", f"relative_humidity_{l}hPa", f"wind_speed_{l}hPa", f"wind_direction_{l}hPa"])
    
    params = {
        "latitude": lat, "longitude": lon, 
        "start_date": date_str, "end_date": date_str,
        "hourly": ",".join(vars_v1), "timeformat": "unixtime", "timezone": "UTC"
    }
    if api_type == "Forecast" and delta > 0: params["past_days"] = delta + 1

    data = _fetch(url, params)
    syntax = "v1"

    # --- TENTATIVA 2: Variáveis sem underscore (Fallback Archive) ---
    if not data:
        vars_v2 = [v.replace("wind_", "wind") for v in vars_v1]
        params["hourly"] = ",".join(vars_v2)
        data = _fetch(url, params)
        syntax = "v2"

    # Se ambas falharem
    if not data or "hourly" not in data:
        st.error(f"Erro ao baixar dados ({api_type}). Verifique a conexão.")
        return None

    # Processamento
    idx = int(hour)
    ts = data["hourly"].get("time", [])
    if idx >= len(ts): 
        st.warning("Hora inválida.")
        return None

    # Validação de Data Retornada
    returned_date = datetime.utcfromtimestamp(ts[idx]).date()
    # Aviso opcional se a data for diferente
    if returned_date != date_obj:
        st.caption(f"ℹ️ Dados exibidos de: {returned_date}")

    res = []
    for level in PRESSURE_LEVELS:
        # Define chaves baseadas no que funcionou (v1 ou v2)
        k_ws = f"wind_speed_{level}hPa" if syntax == "v1" else f"windspeed_{level}hPa"
        k_wd = f"wind_direction_{level}hPa" if syntax == "v1" else f"winddirection_{level}hPa"
        
        t = data["hourly"].get(f"temperature_{level}hPa", [None])[idx]
        rh = data["hourly"].get(f"relative_humidity_{level}hPa", [0])[idx]
        ws = data["hourly"].get(k_ws, [None])[idx]
        wd = data["hourly"].get(k_wd, [None])[idx]

        if t is not None:
            u, v = 0.0, 0.0
            if ws is not None and wd is not None:
                rad = math.radians(wd)
                u = -ws * math.sin(rad)
                v = -ws * math.cos(rad)
            
            res.append({
                "pressure": level, "temperature": t, "relative_humidity": rh,
                "u_component": u/3.6, "v_component": v/3.6 # Converte km/h para m/s
            })

    if not res: 
        st.warning("Dados vazios.")
        return None
        
    df = pd.DataFrame(res)
    df.attrs['source'] = f"{api_type}"
    df.attrs['real_date'] = returned_date
    return df.sort_values("pressure", ascending=False)
