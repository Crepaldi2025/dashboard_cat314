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

def _fetch_data_from_api(url, params, syntax_type):
    """Função auxiliar para tentar a requisição com diferentes sintaxes."""
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None

def get_vertical_profile_data(lat, lon, date_obj, hour):
    date_str = date_obj.strftime('%Y-%m-%d')
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Define URL base - Margem segura de 14 dias
    if delta_dias <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "archive"

    # --- TENTATIVA 1: SINTAXE PADRÃO (com underscore) ---
    variables_v1 = []
    for level in PRESSURE_LEVELS:
        variables_v1.append(f"temperature_{level}hPa")
        variables_v1.append(f"relative_humidity_{level}hPa")
        variables_v1.append(f"wind_speed_{level}hPa")
        variables_v1.append(f"wind_direction_{level}hPa")
    
    params_v1 = {
        "latitude": lat, "longitude": lon,
        "start_date": date_str, "end_date": date_str,
        "hourly": ",".join(variables_v1),
        "timeformat": "unixtime", "timezone": "UTC"
    }
    if api_type == "forecast" and delta_dias > 0: params_v1["past_days"] = delta_dias + 1

    data = _fetch_data_from_api(url, params_v1, "v1")
    used_syntax = "v1"

    # --- TENTATIVA 2: SINTAXE ALTERNATIVA (sem underscore) ---
    if data is None:
        variables_v2 = []
        for level in PRESSURE_LEVELS:
            variables_v2.append(f"temperature_{level}hPa")
            variables_v2.append(f"relative_humidity_{level}hPa")
            variables_v2.append(f"windspeed_{level}hPa")
            variables_v2.append(f"winddirection_{level}hPa")
        
        params_v2 = params_v1.copy()
        params_v2["hourly"] = ",".join(variables_v2)
        
        data = _fetch_data_from_api(url, params_v2, "v2")
        used_syntax = "v2"

    if data is None:
        st.error(f"Erro ao obter dados da API ({api_type}). Verifique a conexão.")
        return None

    if "hourly" not in data:
        st.warning("Dados não encontrados na resposta da API.")
        return None

    try:
        idx = int(hour)
        timestamps = data["hourly"].get("time", [])
        if idx >= len(timestamps):
            st.warning("Hora solicitada inválida.")
            return None

        # --- VERIFICAÇÃO DE DATA ---
        # Verifica se o timestamp retornado realmente corresponde à data pedida
        returned_ts = timestamps[idx]
        returned_date = datetime.utcfromtimestamp(returned_ts).date()
        
        if returned_date != date_obj:
            st.warning(f"⚠️ Atenção: A API retornou dados de {returned_date} em vez de {date_obj}. Tente outro período.")
            # Se for crítico, pode retornar None aqui.
            # return None

        profile_data = []
        for level in PRESSURE_LEVELS:
            ws_key = f"wind_speed_{level}hPa" if used_syntax == "v1" else f"windspeed_{level}hPa"
            wd_key = f"wind_direction_{level}hPa" if used_syntax == "v1" else f"winddirection_{level}hPa"
            
            t_list = data["hourly"].get(f"temperature_{level}hPa")
            rh_list = data["hourly"].get(f"relative_humidity_{level}hPa")
            ws_list = data["hourly"].get(ws_key)
            wd_list = data["hourly"].get(wd_key)

            if t_list is None: continue

            t = t_list[idx]
            rh = rh_list[idx] if rh_list else None
            ws = ws_list[idx] if ws_list else None
            wd = wd_list[idx] if wd_list else None

            if t is not None:
                u, v = 0.0, 0.0
                if ws is not None and wd is not None:
                    rad = math.radians(wd)
                    u = -ws * math.sin(rad)
                    v = -ws * math.cos(rad)

                profile_data.append({
                    "pressure": level,
                    "temperature": float(t),
                    "relative_humidity": float(rh) if rh is not None else 0.0,
                    "u_component": u,
                    "v_component": v
                })

        if not profile_data:
            st.warning("Dados vazios encontrados.")
            return None

        df = pd.DataFrame(profile_data)
        df['u_component'] = df['u_component'] / 3.6
        df['v_component'] = df['v_component'] / 3.6
        # Guarda a data real retornada para exibir no título
        df.attrs['source'] = f"{api_type.capitalize()}"
        df.attrs['real_date'] = returned_date 
        
        return df.sort_values(by="pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None
