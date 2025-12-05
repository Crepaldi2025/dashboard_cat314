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

def get_vertical_profile_data(lat, lon, date_obj, hour):
    date_str = date_obj.strftime('%Y-%m-%d')
    delta = (datetime.now().date() - date_obj).days
    
    # Seleção de API
    if delta <= 14:
        base_url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast"
    else:
        base_url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive"

    # Montagem de Variáveis (Sintaxe Padrão Oficial: com underscore)
    # Ex: temperature_1000hPa, wind_speed_1000hPa
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
    
    if api_type == "Forecast" and delta > 0: 
        params["past_days"] = delta + 1

    # --- MODO DEBUG: Mostrar URL ---
    # Constrói a URL final para o usuário poder testar no navegador
    req = requests.Request('GET', base_url, params=params)
    prepped = req.prepare()
    
    with st.expander("🐞 Debug API (Clique aqui se der erro)", expanded=False):
        st.write(f"**Tipo de API:** {api_type}")
        st.write("Se o gráfico não carregar, clique no link abaixo para ver o erro real da API:")
        st.markdown(f"[🔗 Link da Requisição JSON]({prepped.url})")

    try:
        response = requests.Session().send(prepped)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

    if "hourly" not in data:
        st.warning("A API respondeu, mas sem dados horários.")
        return None

    # Processamento
    try:
        idx = int(hour)
        ts = data["hourly"].get("time", [])
        
        # Validação de Índice
        if idx >= len(ts): 
            st.warning(f"Hora {hour} inválida. A API retornou apenas {len(ts)} pontos.")
            return None
        
        # Validação de Data Retornada vs Pedida
        returned_ts = ts[idx]
        returned_date = datetime.utcfromtimestamp(returned_ts).date()
        
        res = []
        for level in PRESSURE_LEVELS:
            # Chaves com underscore (padrão oficial)
            key_t = f"temperature_{level}hPa"
            key_rh = f"relative_humidity_{level}hPa"
            key_ws = f"wind_speed_{level}hPa"
            key_wd = f"wind_direction_{level}hPa"
            
            # Extração Segura
            t_list = data["hourly"].get(key_t)
            rh_list = data["hourly"].get(key_rh)
            ws_list = data["hourly"].get(key_ws)
            wd_list = data["hourly"].get(key_wd)

            # Se a lista inteira é None, pula
            if not t_list: continue

            # Pega o valor
            t = t_list[idx]
            rh = rh_list[idx] if rh_list else None
            ws = ws_list[idx] if ws_list else None
            wd = wd_list[idx] if wd_list else None

            # Se Temperature é None, o dado é inválido
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
            st.warning(f"Dados vazios encontrados para {returned_date} às {hour}:00 UTC.")
            return None
            
        df = pd.DataFrame(res)
        df.attrs['source'] = f"{api_type} ({returned_date})"
        df.attrs['real_date'] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro no processamento dos dados: {e}")
        return None
