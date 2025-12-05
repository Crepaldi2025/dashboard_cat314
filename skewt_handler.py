# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date
import math

# Níveis de pressão padrão (Open-Meteo aceita estes níveis em hPa)
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700,
                   600, 500, 400, 300, 250, 200, 150, 100]

# Data de início dos dados de pressão no Historical Forecast (GFS)
HIST_FC_START_DATE = date(2021, 3, 23)

def _normalize_date(date_obj):
    """Garante que date_obj seja um datetime.date."""
    if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
        return date_obj
    if isinstance(date_obj, datetime):
        return date_obj.date()
    try:
        return datetime.strptime(str(date_obj), "%Y-%m-%d").date()
    except Exception:
        raise ValueError(f"date_obj inválido: {date_obj!r}")

def _normalize_hour(hour):
    """Converte hour em índice inteiro (0–23)."""
    if isinstance(hour, (int, float)):
        return int(hour)
    h_str = str(hour).strip()
    for sep in [":", "h", "H", " "]:
        if sep in h_str:
            h_str = h_str.split(sep)[0]
            break
    return int(h_str)

def get_vertical_profile_data(lat, lon, date_obj, hour):
    # ----------------------------------------------------------------------
    # 0. Normalização
    # ----------------------------------------------------------------------
    try:
        date_only = _normalize_date(date_obj)
        date_str = date_only.strftime("%Y-%m-%d")
        idx = _normalize_hour(hour)
    except Exception as e:
        st.error(f"Erro nos parâmetros de data/hora: {e}")
        return None

    if not (0 <= idx <= 23):
        st.warning(f"Hora inválida: {idx}")
        return None

    hoje_utc = datetime.utcnow().date()
    delta = (hoje_utc - date_only).days

    # ----------------------------------------------------------------------
    # 1. Escolha do endpoint da Open-Meteo
    # ----------------------------------------------------------------------
    
    # REGRA SIMPLIFICADA:
    # Se for recente (futuro ou até 14 dias atrás) -> Usa API de Previsão
    # Se for antigo (> 14 dias atrás) -> Usa API de Previsão Histórica (Historical Forecast)
    
    if delta <= 14:
        # Endpoint de Previsão (Forecast)
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast (GFS/Seamless)"
        # CORREÇÃO: Removemos 'past_days'. As datas start/end já são suficientes.
        params = {}
    else:
        # Endpoint Histórico (Historical Forecast - contém dados de altitude)
        # Nota: Não usamos 'archive-api' (ERA5) porque ele não tem pressão horária
        if date_only < HIST_FC_START_DATE:
            st.error(f"⚠️ Dados de altitude indisponíveis antes de {HIST_FC_START_DATE.strftime('%d/%m/%Y')}.")
            return None

        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        api_type = "Historical Forecast (GFS)"
        params = {}

    # ----------------------------------------------------------------------
    # 2. Montagem da Requisição
    # ----------------------------------------------------------------------
    vars_list = []
    for l in PRESSURE_LEVELS:
        vars_list.extend([
            f"temperature_{l}hPa",
            f"relative_humidity_{l}hPa",
            f"wind_speed_{l}hPa",
            f"wind_direction_{l}hPa",
        ])

    params.update({
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": ",".join(vars_list),
        "timeformat": "unixtime",
        "timezone": "UTC",
    })

    # ----------------------------------------------------------------------
    # 3. Execução
    # ----------------------------------------------------------------------
    try:
        req = requests.Request("GET", url, params=params)
        prepped = req.prepare()

        # Debug Opcional (Remova o # abaixo se quiser ver o link na tela)
        # with st.expander("🐞 Debug Link"): st.write(prepped.url)

        response = requests.Session().send(prepped)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        return None

    if "hourly" not in data:
        st.warning("API respondeu sem dados horários.")
        return None

    # ----------------------------------------------------------------------
    # 4. Processamento dos Dados
    # ----------------------------------------------------------------------
    try:
        ts = data["hourly"].get("time", [])
        if not ts: return None
        
        # Garante que o índice existe
        if idx >= len(ts):
            # Fallback: Se pedir hora futura não disponível, pega a última
            idx = len(ts) - 1
            st.caption(f"⚠️ Hora {hour}:00 não disponível ainda. Usando última disponível.")

        returned_date = datetime.utcfromtimestamp(ts[idx]).date()
        
        if returned_date != date_only:
            st.caption(f"ℹ️ Dados exibidos de: {returned_date}")

        res = []
        for level in PRESSURE_LEVELS:
            t = data["hourly"].get(f"temperature_{level}hPa", [None])[idx]
            rh = data["hourly"].get(f"relative_humidity_{level}hPa", [None])[idx]
            ws = data["hourly"].get(f"wind_speed_{level}hPa", [None])[idx]
            wd = data["hourly"].get(f"wind_direction_{level}hPa", [None])[idx]

            if t is not None:
                # Converte Vento (km/h -> m/s) e calcula componentes
                u, v = 0.0, 0.0
                if ws is not None and wd is not None:
                    rad = math.radians(wd)
                    # Open-Meteo Forecast usa Wind Speed em km/h por padrão
                    ws_ms = ws / 3.6 
                    u = -ws_ms * math.sin(rad)
                    v = -ws_ms * math.cos(rad)

                res.append({
                    "pressure": level,
                    "temperature": float(t),
                    "relative_humidity": float(rh) if rh is not None else 0.0,
                    "u_component": u,
                    "v_component": v,
                })

        if not res:
            st.error(f"Dados vazios. O modelo {api_type} não retornou níveis de pressão.")
            return None

        df = pd.DataFrame(res)
        df.attrs["source"] = api_type
        df.attrs["real_date"] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando resposta: {e}")
        return None
