# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import math

# Níveis de pressão padrão
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150, 100]

def _fetch(url, params):
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # Repassa o erro para ser tratado no nível superior
        raise e

def get_vertical_profile_data(lat, lon, date_obj, hour):
    date_str = date_obj.strftime('%Y-%m-%d')
    delta = (datetime.now().date() - date_obj).days
    
    # 1. Configuração da API e Modelo
    if delta <= 14:
        # --- DADOS RECENTES ---
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast (GFS)"
        # CORREÇÃO: Força o modelo 'gfs_seamless'. 
        # Evita erro 400 se o modelo 'auto' não tiver níveis de pressão.
        # Removemos 'past_days' pois start/end já definem o período.
        extra_params = {"models": "gfs_seamless"} 
    else:
        # --- DADOS HISTÓRICOS ---
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive (ERA5)"
        # CORREÇÃO: Força modelo 'era5' para ter dados de altitude.
        extra_params = {"models": "era5"}

    # 2. Montagem de Variáveis
    vars_list = []
    for l in PRESSURE_LEVELS:
        vars_list.extend([
            f"temperature_{l}hPa", 
            f"relative_humidity_{l}hPa", 
            f"wind_speed_{l}hPa", 
            f"wind_direction_{l}hPa"
        ])
    
    params = {
        "latitude": lat, 
        "longitude": lon, 
        "start_date": date_str, 
        "end_date": date_str,
        "hourly": ",".join(vars_list), 
        "timeformat": "unixtime", 
        "timezone": "UTC"
    }
    # Aplica a forçagem de modelo (GFS ou ERA5)
    params.update(extra_params)

    # 3. Requisição
    try:
        # Monta requisição para debug
        req = requests.Request('GET', url, params=params)
        prepped = req.prepare()
        
        # Link de Debug
        with st.expander("🐞 Debug API (Se der erro, clique aqui)", expanded=False):
            st.write(f"**API:** {api_type} | **Modelo Forçado:** {extra_params['models']}")
            st.markdown(f"[🔗 Link JSON]({prepped.url})")

        # Envia
        data = _fetch(url, params)

    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None

    if not data or "hourly" not in data:
        st.warning("API respondeu sem dados horários.")
        return None

    # 4. Processamento
    try:
        idx = int(hour)
        ts = data["hourly"].get("time", [])
        
        if idx >= len(ts): 
            st.warning("Hora inválida.")
            return None

        returned_date = datetime.utcfromtimestamp(ts[idx]).date()
        
        res = []
        for level in PRESSURE_LEVELS:
            # Busca segura
            t = data["hourly"].get(f"temperature_{level}hPa", [None])[idx]
            rh = data["hourly"].get(f"relative_humidity_{level}hPa", [None])[idx]
            ws = data["hourly"].get(f"wind_speed_{level}hPa", [None])[idx]
            wd = data["hourly"].get(f"wind_direction_{level}hPa", [None])[idx]

            # Se temperatura ok, processa
            if t is not None:
                u, v = 0.0, 0.0
                if ws is not None and wd is not None:
                    rad = math.radians(wd)
                    u = -ws * math.sin(rad)
                    v = -ws * math.cos(rad)
                
                res.append({
                    "pressure": level, 
                    "temperature": float(t), 
                    "relative_humidity": float(rh) if rh is not None else 0.0,
                    "u_component": u/3.6, # km/h -> m/s
                    "v_component": v/3.6
                })

        if not res: 
            st.error(f"Dados vazios. O modelo {extra_params['models']} falhou para esta data/local.")
            return None
            
        df = pd.DataFrame(res)
        df.attrs['source'] = api_type
        df.attrs['real_date'] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando dados: {e}")
        return None
