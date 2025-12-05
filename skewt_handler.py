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
    
    # 1. Seleção de API
    if delta <= 14:
        # Previsão (GFS/IFS) - Possui dados recentes sem gap
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast"
        extra_params = {"past_days": delta + 1} if delta > 0 else {}
    else:
        # Arquivo Histórico (ERA5)
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive"
        # --- CORREÇÃO CRÍTICA ---
        # Força o modelo ERA5. Sem isso, a API usa ERA5-Land (só superfície) 
        # e retorna 'null'/'undefined' para níveis de pressão.
        extra_params = {"models": "era5"}

    # 2. Montagem de Variáveis (Sintaxe Padrão com Underscore)
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
    
    # Adiciona parâmetros específicos (models ou past_days)
    params.update(extra_params)

    # 3. Requisição e Debug
    # Cria o link para o debug antes de enviar
    req = requests.Request('GET', url, params=params)
    prepped = req.prepare()
    
    # Mostra caixa de debug se der erro
    with st.expander("🐞 Debug API (Clique se os dados falharem)", expanded=False):
        st.write(f"**API:** {api_type} | **Modelo:** {params.get('models', 'Auto')}")
        st.markdown(f"[🔗 Link JSON da Requisição]({prepped.url})")

    data = _fetch(url, params)

    if not data or "hourly" not in data:
        st.error(f"Erro ao obter dados da API ({api_type}). Verifique a conexão.")
        return None

    # 4. Processamento
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
            # Chaves esperadas
            k_t = f"temperature_{level}hPa"
            k_rh = f"relative_humidity_{level}hPa"
            k_ws = f"wind_speed_{level}hPa"
            k_wd = f"wind_direction_{level}hPa"
            
            # Obtém listas (usa .get para segurança)
            t_list = data["hourly"].get(k_t)
            rh_list = data["hourly"].get(k_rh)
            ws_list = data["hourly"].get(k_ws)
            wd_list = data["hourly"].get(k_wd)

            # Se a lista não existir no JSON, pula
            if not t_list: continue

            # Extrai valores no índice da hora
            t = t_list[idx]
            rh = rh_list[idx] if rh_list else None
            ws = ws_list[idx] if ws_list else None
            wd = wd_list[idx] if wd_list else None

            # Se t for None, o dado é inválido (gap ou erro de modelo)
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
            st.warning(f"Dados vazios. O modelo ERA5 pode não ter dados para {lat},{lon} nesta data.")
            return None
            
        df = pd.DataFrame(res)
        df.attrs['source'] = f"{api_type} (ERA5)"
        df.attrs['real_date'] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando dados: {e}")
        return None
