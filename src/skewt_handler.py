# ==================================================================================
# skewt_handler.py — Perfis verticais para o diagrama Skew-T (ClimaCast)
# ==================================================================================
from datetime import date, datetime, timezone
import math

import pandas as pd
import requests
import streamlit as st


# Níveis isobáricos solicitados à Open-Meteo, em hPa.
PRESSURE_LEVELS = [
    1000, 975, 950, 925, 900, 850, 800, 700,
    600, 500, 400, 300, 250, 200, 150, 100,
]

# Limite operacional anteriormente adotado no projeto para a API histórica.
# A disponibilidade efetiva depende do arquivo e do modelo da Open-Meteo.
HIST_FC_START_DATE = date(2021, 3, 23)


def _normalize_date(value):
    """Converte a entrada em datetime.date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data inválida: {value!r}") from exc


def _normalize_hour(value):
    """Obtém a hora inteira UTC (0–23), sem arredondamentos silenciosos."""
    if isinstance(value, bool):
        raise ValueError("Hora inválida: valor booleano.")
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)) or int(value) != value:
            raise ValueError(f"Hora inválida: {value!r}")
        hour = int(value)
    else:
        token = str(value).strip().replace("H", "h")
        token = token.split(":", 1)[0].split("h", 1)[0].split(" ", 1)[0]
        hour = int(token)
    if not 0 <= hour <= 23:
        raise ValueError(f"Hora fora do intervalo 0–23: {hour}")
    return hour


def _hourly_value(hourly, name, index):
    """Recupera com segurança o valor de uma variável horária."""
    values = hourly.get(name)
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


@st.cache_data(ttl=3600)
def get_vertical_profile_data(lat, lon, date_obj, hour):
    """Obtém o perfil modelado em um instante UTC, acima da superfície.

    Retorna DataFrame ordenado por pressão decrescente com colunas:
    pressure (hPa), temperature (°C), relative_humidity (%),
    u_component e v_component (m/s).

    O primeiro nível representa a superfície do modelo (temperatura e UR a 2 m).
    Níveis isobáricos com pressão >= pressão de superfície são descartados.
    Dados ausentes permanecem como NaN; não são convertidos em zero.
    """
    try:
        selected_date = _normalize_date(date_obj)
        selected_hour = _normalize_hour(hour)
        lat = float(lat)
        lon = float(lon)
        if not all(map(math.isfinite, (lat, lon))):
            raise ValueError("Coordenadas não finitas.")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Latitude ou longitude fora dos limites geográficos.")
    except (TypeError, ValueError) as exc:
        st.error(f"Parâmetros inválidos para o Skew-T: {exc}")
        return None

    # Mantém a política de escolha de endpoint previamente usada pelo projeto.
    delta_days = (datetime.now(timezone.utc).date() - selected_date).days
    if delta_days <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        source = "Open-Meteo Forecast (modelo não fixado)"
    else:
        if selected_date < HIST_FC_START_DATE:
            st.error(
                "Dados históricos de níveis de pressão não habilitados nesta "
                f"aplicação antes de {HIST_FC_START_DATE:%d/%m/%Y}."
            )
            return None
        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        source = "Open-Meteo Historical Forecast (modelo não fixado)"

    variables = []
    for level in PRESSURE_LEVELS:
        variables.extend((
            f"temperature_{level}hPa",
            f"relative_humidity_{level}hPa",
            f"wind_speed_{level}hPa",
            f"wind_direction_{level}hPa",
        ))
    variables.extend(("surface_pressure", "temperature_2m", "relative_humidity_2m"))

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": selected_date.isoformat(),
        "end_date": selected_date.isoformat(),
        "hourly": ",".join(variables),
        "timeformat": "unixtime",
        "timezone": "UTC",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
    }

    try:
        response = requests.get(url, params=params, timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        st.error(f"Falha na consulta à Open-Meteo ({source}): {exc}")
        return None

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        st.error("Resposta da Open-Meteo sem dados horários válidos.")
        return None

    timestamps = hourly.get("time")
    if not isinstance(timestamps, list) or not timestamps:
        st.error("Resposta da Open-Meteo sem timestamps horários.")
        return None

    target = datetime(
        selected_date.year, selected_date.month, selected_date.day,
        selected_hour, tzinfo=timezone.utc,
    )
    target_unix = int(target.timestamp())
    try:
        index = next(
            i for i, value in enumerate(timestamps)
            if int(value) == target_unix
        )
    except (StopIteration, TypeError, ValueError):
        st.warning(f"Não há perfil disponível para {target:%d/%m/%Y %H:%M} UTC.")
        return None

    ps = _hourly_value(hourly, "surface_pressure", index)
    t2m = _hourly_value(hourly, "temperature_2m", index)
    rh2m = _hourly_value(hourly, "relative_humidity_2m", index)

    if ps is None or t2m is None or rh2m is None:
        st.error("Pressão, temperatura ou umidade de superfície indisponível.")
        return None
    if not (100 < ps <= 1100 and 0 < rh2m <= 100):
        st.error("Pressão ou umidade relativa de superfície inválida.")
        return None

    rows = [{
        "pressure": ps,
        "temperature": t2m,
        "relative_humidity": rh2m,
        "u_component": float("nan"),
        "v_component": float("nan"),
    }]

    for level in PRESSURE_LEVELS:
        if level >= ps:  # Pressão maior = nível sob a superfície.
            continue

        temperature = _hourly_value(hourly, f"temperature_{level}hPa", index)
        if temperature is None:
            continue

        rh = _hourly_value(hourly, f"relative_humidity_{level}hPa", index)
        if rh is not None and not (0 < rh <= 100):
            rh = None  # Zero não permite ponto de orvalho finito.

        speed = _hourly_value(hourly, f"wind_speed_{level}hPa", index)
        direction = _hourly_value(hourly, f"wind_direction_{level}hPa", index)
        u = v = float("nan")
        if speed is not None and speed >= 0 and direction is not None:
            angle = math.radians(direction)
            speed_ms = speed / 3.6
            u = -speed_ms * math.sin(angle)
            v = -speed_ms * math.cos(angle)

        rows.append({
            "pressure": float(level),
            "temperature": temperature,
            "relative_humidity": rh if rh is not None else float("nan"),
            "u_component": u,
            "v_component": v,
        })

    if len(rows) < 2:
        st.error("Não há níveis atmosféricos suficientes acima da superfície.")
        return None

    profile = pd.DataFrame(rows).sort_values("pressure", ascending=False)
    profile = profile.reset_index(drop=True)
    profile.attrs["source"] = source
    profile.attrs["real_date"] = selected_date
    profile.attrs["valid_time_utc"] = target.isoformat()
    profile.attrs["surface_pressure_hpa"] = ps

    # Verificação operacional: não confundir ausência de umidade com atmosfera seca.
    if profile["relative_humidity"].isna().any():
        st.warning(
            "Há níveis sem umidade relativa válida. A representação gráfica pode "
            "ser parcial; CAPE/CIN devem ser calculados somente após validação "
            "dos dados termodinâmicos."
        )

    return profile
