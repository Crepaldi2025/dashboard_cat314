# ==================================================================================
# skewt_handler.py (revisado)
# ==================================================================================
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date
import math

# Níveis de pressão padrão (Open-Meteo aceita estes níveis em hPa)
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700,
                   600, 500, 400, 300, 250, 200, 150, 100]


def _normalize_date(date_obj):
    """Garante que date_obj seja um datetime.date."""
    if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
        return date_obj
    if isinstance(date_obj, datetime):
        return date_obj.date()
    # Se vier string "YYYY-MM-DD"
    try:
        return datetime.strptime(str(date_obj), "%Y-%m-%d").date()
    except Exception:
        raise ValueError(f"date_obj inválido: {date_obj!r}")


def _normalize_hour(hour):
    """Converte hour em índice inteiro (0–23).
    Aceita: 12, '12', '12:00', '12 UTC', '12h', etc.
    """
    if isinstance(hour, (int, float)):
        return int(hour)

    h_str = str(hour).strip()

    # Tenta extrair a parte numérica inicial antes de ':', 'h', 'H' ou espaço
    for sep in [":", "h", "H", " "]:
        if sep in h_str:
            h_str = h_str.split(sep)[0]
            break

    return int(h_str)


def get_vertical_profile_data(lat, lon, date_obj, hour):
    # ----------------------------------------------------------------------
    # 0. Normalização de data e hora
    # ----------------------------------------------------------------------
    date_only = _normalize_date(date_obj)
    date_str = date_only.strftime("%Y-%m-%d")

    try:
        idx = _normalize_hour(hour)
    except ValueError as e:
        st.error(f"Hora inválida: {hour!r}. Erro: {e}")
        return None

    if idx < 0 or idx > 23:
        st.error(f"Hora fora do intervalo 0–23: {idx}")
        return None

    # ----------------------------------------------------------------------
    # 1. Seleção de API e FORÇAR MODELO ERA5 (quando histórico)
    # ----------------------------------------------------------------------
    # delta > 0 → passado; delta <= 14 → forecast+past_days, senão archive (ERA5)
    hoje_utc = datetime.utcnow().date()
    delta = (hoje_utc - date_only).days

    if delta <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "Forecast (GFS ou similar)"
        params = {"past_days": delta + 1} if delta > 0 else {}
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "Archive (ERA5)"
        # Força ERA5 como modelo global de reanálise :contentReference[oaicite:1]{index=1}
        params = {"models": "era5"}

    # ----------------------------------------------------------------------
    # 2. Variáveis em níveis de pressão
    # ----------------------------------------------------------------------
    vars_list = []
    for l in PRESSURE_LEVELS:
        vars_list.extend([
            f"temperature_{l}hPa",
            f"relative_humidity_{l}hPa",
            f"wind_speed_{l}hPa",
            f"wind_direction_{l}hPa",
        ])

    # ----------------------------------------------------------------------
    # 3. Montagem dos parâmetros finais
    # ----------------------------------------------------------------------
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
    # 4. Requisição
    # ----------------------------------------------------------------------
    try:
        req = requests.Request("GET", url, params=params)
        prepped = req.prepare()

        # Útil para debug
        print(f"[skewt_handler] URL Gerada: {prepped.url}")

        response = requests.Session().send(prepped)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Erro na conexão com Open-Meteo ({api_type}): {e}")
        st.write("Parâmetros usados:", params)
        return None

    if "hourly" not in data:
        st.warning("API respondeu sem bloco 'hourly'.")
        st.write("Resposta bruta da API:", data)
        return None

    # ----------------------------------------------------------------------
    # 5. Processamento dos dados horários
    # ----------------------------------------------------------------------
    try:
        ts = data["hourly"].get("time", [])
        if not ts:
            st.warning("Lista de 'time' vazia na resposta da API.")
            return None

        if idx >= len(ts):
            st.warning(f"Hora inválida: idx={idx} fora de range (len={len(ts)}).")
            return None

        # Validação de Data retornada
        returned_date = datetime.utcfromtimestamp(ts[idx]).date()
        if returned_date != date_only:
            st.info(
                f"Atenção: data retornada pela API ({returned_date}) "
                f"≠ data solicitada ({date_only})."
            )

        res = []
        for level in PRESSURE_LEVELS:
            t = data["hourly"].get(f"temperature_{level}hPa", [None])[idx]
            rh = data["hourly"].get(f"relative_humidity_{level}hPa", [None])[idx]
            ws = data["hourly"].get(f"wind_speed_{level}hPa", [None])[idx]
            wd = data["hourly"].get(f"wind_direction_{level}hPa", [None])[idx]

            # Se temperatura é None, descarta o nível
            if t is not None:
                u, v = 0.0, 0.0
                if ws is not None and wd is not None:
                    # ws vem em km/h por padrão; wd em graus :contentReference[oaicite:2]{index=2}
                    rad = math.radians(wd)
                    u = -ws * math.sin(rad)
                    v = -ws * math.cos(rad)

                res.append({
                    "pressure": level,
                    "temperature": float(t),
                    "relative_humidity": float(rh) if rh is not None else 0.0,
                    "u_component": u / 3.6,   # km/h -> m/s
                    "v_component": v / 3.6,
                })

        if not res:
            st.error(
                f"Dados NULOS recebidos para {returned_date}. "
                "Verifique se as variáveis em níveis de pressão estão disponíveis "
                "para este modelo/data."
            )
            with st.expander("URL chamada (deve conter models=era5, se histórico)"):
                st.write(prepped.url)
            st.write("Resposta bruta da API:", data)
            return None

        df = pd.DataFrame(res)
        df.attrs["source"] = api_type
        df.attrs["real_date"] = returned_date
        return df.sort_values("pressure", ascending=False)

    except Exception as e:
        st.error(f"Erro processando resposta da API: {e}")
        st.write("Resposta bruta da API para debug:", data)
        return None
