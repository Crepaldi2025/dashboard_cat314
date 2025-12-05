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
    """
    Busca dados de perfil vertical.
    Solicita Velocidade/Direção (compatível com todas APIs) e calcula U/V manualmente.
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # 1. Decisão Inteligente da Fonte de Dados (Híbrido)
    hoje = datetime.now().date()
    delta_dias = (hoje - date_obj).days
    
    # Margem segura de 14 dias
    if delta_dias <= 14:
        url = "https://api.open-meteo.com/v1/forecast"
        api_type = "forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"
        api_type = "archive"
    
    # Monta lista de variáveis (USANDO NOMES PADRÃO ACEITOS)
    variables = []
    for level in PRESSURE_LEVELS:
        variables.append(f"temperature_{level}hPa")
        variables.append(f"relative_humidity_{level}hPa")
        variables.append(f"windspeed_{level}hPa")    # Nome correto API
        variables.append(f"winddirection_{level}hPa") # Nome correto API
    
    hourly_vars = ",".join(variables)
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str, 
        "hourly": hourly_vars,
        "timeformat": "unixtime",
        "timezone": "UTC"
    }
    
    if api_type == "forecast" and delta_dias > 0:
        params["past_days"] = delta_dias + 1

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "hourly" not in data:
            st.warning(f"A API ({api_type}) não retornou dados.")
            return None
            
        idx = int(hour)
        timestamps = data["hourly"].get("time", [])
        if idx >= len(timestamps):
            st.warning("Hora solicitada fora do intervalo retornado.")
            return None

        # Estrutura os dados
        profile_data = []
        for level in PRESSURE_LEVELS:
            try:
                # Busca as listas de dados (Nota: Open-Meteo às vezes usa 'windspeed' ou 'wind_speed'. 
                # A URL construída usou 'windspeed', mas o JSON de retorno geralmente usa chaves iguais à query string)
                
                # Tenta pegar com a chave exata da requisição
                t_list = data["hourly"].get(f"temperature_{level}hPa")
                rh_list = data["hourly"].get(f"relative_humidity_{level}hPa")
                ws_list = data["hourly"].get(f"windspeed_{level}hPa")
                wd_list = data["hourly"].get(f"winddirection_{level}hPa")
                
                if t_list is None: continue

                t = t_list[idx]
                rh = rh_list[idx] if rh_list else None
                ws = ws_list[idx] if ws_list else None
                wd = wd_list[idx] if wd_list else None
                
                if t is not None:
                    # CÁLCULO MANUAL DOS COMPONENTES U E V
                    # Se não houver vento (subterrâneo ou nulo), define como 0
                    u, v = 0.0, 0.0
                    if ws is not None and wd is not None:
                        # Convertendo graus para radianos
                        # Meteorologia: Direção é de onde vem o vento. 
                        # u = -ws * sin(theta), v = -ws * cos(theta)
                        rad = math.radians(wd)
                        u = -ws * math.sin(rad)
                        v = -ws * math.cos(rad)

                    profile_data.append({
                        "pressure": level,
                        "temperature": float(t),
                        "relative_humidity": float(rh) if rh is not None else 0.0,
                        "u_component": u, # Calculado em m/s (Open-Meteo retorna km/h, convertemos se precisar no visualizer)
                        "v_component": v
                    })
            except (IndexError, TypeError):
                continue
        
        if not profile_data:
            st.warning(f"Dados vazios para {date_str} {hour}:00 UTC. Tente outra data.")
            return None
        
        df = pd.DataFrame(profile_data)
        
        # Open-Meteo retorna velocidade em km/h por padrão.
        # Nossos componentes U/V foram calculados mantendo a magnitude original (km/h).
        # O Visualizer espera converter m/s -> nós OU km/h -> nós.
        # Vamos sinalizar que está em km/h na metadata se precisar, 
        # mas o visualizer atual assume m/s. Vamos converter para m/s AQUI para padronizar.
        
        df['u_component'] = df['u_component'] / 3.6 # km/h para m/s
        df['v_component'] = df['v_component'] / 3.6 # km/h para m/s

        df.attrs['source'] = "Previsão/Análise" if api_type == "forecast" else "ERA5 (Histórico)"
        
        return df.sort_values(by="pressure", ascending=False)
        
    except Exception as e:
        st.error(f"Erro na conexão ({api_type}): {e}")
        # Debug URL para ajudar a identificar erros futuros
        # print(response.url) 
        return None
