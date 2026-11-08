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
