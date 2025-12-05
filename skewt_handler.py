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
    
    # 1. Seleção de API e Modelo
    if delta <= 14:
        # Previsão (GFS/IFS) - Dados recentes
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast"
        extra_params = {"past_days": delta + 1} if delta > 0 else {}
    else:
        # Arquivo Histórico (ERA5)
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive"
        # --- CORREÇÃO CRÍTICA ---
        # Força o modelo 'era5'. Sem isso, a API usa 'era5-land' (padrão)
        # que NÃO POSSUI dados de níveis de pressão (retorna null).
        extra_params = {"models": "era5"}

    # 2. Montagem de Variáveis (Padrão snake_case)
    vars_list = []
    for l in PRESSURE_LEVELS:
        vars_list.extend([
            f"temperature_{l}hPa", 
            f"relative_humidity_{l}hPa", 
            f"wind_speed_{l}hPa", 
            f"wind_direction_{l}hPa"
        ])
    
    params = {
        "latitude": lat, "longitude": lon, 
        "start_date": date_str, "end_date": date_str,
        "hourly": ",".join(vars_list), 
        "timeformat": "unixtime", "timezone": "UTC"
    }
    
    # Adiciona os parâmetros extras (incluindo models="era5")
    params.update(extra_params)

    # 3. Requisição e Debug Visual
    req = requests.Request('GET', url, params=params)
    prepped = req.prepare()
    
    # Mostra o link para você confirmar se "&models=era5" está lá
    with st.expander("🐞 Debug URL (Verifique se &models=era5 existe)", expanded=False):
        st.write(f"API: {api_type}")
        st.markdown(f"[🔗 Clique aqui para abrir o JSON no navegador]({prepped.url})")

    try:
        response = requests.Session().send(prepped)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

    if "hourly" not in data:
        st.warning("API respondeu sem dados horários.")
        return None

    # 4. Processamento
    try:
        idx = int(hour)
        ts = data["hourly"].get("time", [])
        
        if idx >= len(ts): 
            st.warning("Hora inválida.")
            return None

        res = []
        for level in PRESSURE_LEVELS:
            k_t = f"temperature_{level}hPa"
            k_rh = f"relative_humidity_{level}hPa"
            k_ws = f"wind_speed_{level}hPa"
            k_wd = f"wind_direction_{level}hPa"
            
            t_list = data["hourly"].get(k_t)
            rh_list = data["hourly"].get(k_rh)
            ws_list = data["hourly"].get(k_ws)
            wd_list = data["hourly"].get(k_wd)

            if not t_list: continue

            t = t_list[idx]
            rh = rh_list[idx] if rh_list else None
            ws = ws_list[idx] if ws_list else None
            wd = wd_list[idx] if wd_list else None

            # Se t for None, significa que o modelo falhou ou não tem dados nessa altitude
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
            st.error(f"Dados vazios (Null). O modelo '{params.get('models')}' falhou para esta coordenada.")
            return None
            
        df = pd.DataFrame(res)
        returned_date = datetime.utcfromtimestamp(ts[idx]).date()
        df.attrs['source'] = f"{api_type} (ERA5)"
        df.attrs['real_date'] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando dados: {e}")
        return None
