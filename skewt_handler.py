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
    
    # 1. Seleção de API e FORÇAR MODELO ERA5
    # Se não especificarmos 'models=era5', a API Archive usa ERA5-Land (que retorna null para altitude)
    if delta <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast (GFS)"
        params = {"past_days": delta + 1} if delta > 0 else {}
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive (ERA5)"
        # O SEGREDO ESTÁ AQUI: Forçar o modelo global
        params = {"models": "era5"} 

    # 2. Variáveis (Sintaxe Padrão com underscore)
    vars_list = []
    for l in PRESSURE_LEVELS:
        vars_list.extend([
            f"temperature_{l}hPa", 
            f"relative_humidity_{l}hPa", 
            f"wind_speed_{l}hPa", 
            f"wind_direction_{l}hPa"
        ])
    
    # 3. Montagem dos Parâmetros Finais
    params.update({
        "latitude": lat, 
        "longitude": lon, 
        "start_date": date_str, 
        "end_date": date_str,
        "hourly": ",".join(vars_list), 
        "timeformat": "unixtime", 
        "timezone": "UTC"
    })

    # 4. Requisição
    try:
        # Debug para você conferir a URL
        req = requests.Request('GET', url, params=params)
        prepped = req.prepare()
        
        # Mostra o link se der erro (ou sempre, para testar)
        print(f"URL Gerada: {prepped.url}") 
        
        response = requests.Session().send(prepped)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None

    if "hourly" not in data:
        st.warning("API respondeu sem dados horários.")
        return None

    # 5. Processamento dos Dados
    try:
        idx = int(hour)
        ts = data["hourly"].get("time", [])
        
        if idx >= len(ts): 
            st.warning("Hora inválida.")
            return None

        # Validação de Data
        returned_date = datetime.utcfromtimestamp(ts[idx]).date()
        
        res = []
        for level in PRESSURE_LEVELS:
            # Busca segura com .get()
            t = data["hourly"].get(f"temperature_{level}hPa", [None])[idx]
            rh = data["hourly"].get(f"relative_humidity_{level}hPa", [None])[idx]
            ws = data["hourly"].get(f"wind_speed_{level}hPa", [None])[idx]
            wd = data["hourly"].get(f"wind_direction_{level}hPa", [None])[idx]

            # Se temperatura for None, o nível está vazio
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
                    "u_component": u/3.6, # Converte km/h -> m/s
                    "v_component": v/3.6
                })

        if not res: 
            # Se cair aqui, a URL não tinha '&models=era5' ou a coord é inválida
            st.error(f"Dados Nulos recebidos para {returned_date}. Verifique se o modelo ERA5 está ativo.")
            with st.expander("Verificar URL (Deve conter models=era5)"):
                st.write(prepped.url)
            return None
            
        df = pd.DataFrame(res)
        df.attrs['source'] = api_type
        df.attrs['real_date'] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando: {e}")
        return None
