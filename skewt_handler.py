# ==================================================================================
# skewt_handler.py
# ==================================================================================
import requests
import pandas as pd
import streamlit as st

# Níveis de pressão padrão disponíveis no ERA5 (Open-Meteo)
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200, 150, 100]

def get_vertical_profile_data(lat, lon, date, hour):
    """
    Busca dados de perfil vertical do ERA5 via Open-Meteo API.
    """
    date_str = date.strftime('%Y-%m-%d')
    
    # Monta a lista de variáveis para a API
    variables = []
    for level in PRESSURE_LEVELS:
        variables.append(f"temperature_{level}hPa")
        variables.append(f"relative_humidity_{level}hPa")
        variables.append(f"wind_speed_{level}hPa")
        variables.append(f"wind_direction_{level}hPa")
    
    hourly_vars = ",".join(variables)
    
    # Endpoint do Arquivo Histórico (ERA5)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": hourly_vars,
        "timeformat": "unixtime",
        "timezone": "UTC"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data:
            st.warning("A API não retornou dados horários para esta requisição.")
            return None
            
        timestamps = data["hourly"].get("time", [])
        if not timestamps:
            st.warning("Lista de horários vazia.")
            return None

        # O índice é a hora (0-23)
        idx = int(hour)
        if idx >= len(timestamps):
            st.warning(f"Hora solicitada ({idx}) fora do intervalo retornado.")
            return None

        # Estruturar dados para DataFrame Vertical
        profile_data = []
        for level in PRESSURE_LEVELS:
            # Tenta pegar os valores com segurança
            try:
                t_key = f"temperature_{level}hPa"
                rh_key = f"relative_humidity_{level}hPa"
                ws_key = f"wind_speed_{level}hPa"
                wd_key = f"wind_direction_{level}hPa"

                # Verifica se as chaves existem na resposta
                if t_key not in data["hourly"]: continue

                temp = data["hourly"][t_key][idx]
                rh = data["hourly"][rh_key][idx]
                ws = data["hourly"][ws_key][idx]
                wd = data["hourly"][wd_key][idx]
                
                # Só adiciona se tiver temperatura válida
                if temp is not None:
                    profile_data.append({
                        "pressure": level,
                        "temperature": temp,
                        "relative_humidity": rh,
                        "wind_speed": ws,
                        "wind_direction": wd
                    })
            except IndexError:
                continue
        
        # Se a lista estiver vazia, retorna None imediatamente para evitar o erro de 'pressure'
        if not profile_data:
            st.warning("Nenhum dado válido encontrado para os níveis de pressão neste horário. (Possível gap no ERA5 ou data muito recente).")
            return None
        
        df = pd.DataFrame(profile_data)
        return df.sort_values(by="pressure", ascending=False) # Ordena do solo para o topo
        
    except Exception as e:
        # Imprime o erro real no console para debug e avisa o usuário
        print(f"Erro detalhado Skew-T: {e}") 
        st.error(f"Erro ao buscar dados: {e}. Tente uma data anterior a 5 dias atrás.")
        return None
