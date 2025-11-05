# ==================================================================================
# utils.py — Funções utilitárias do Clima-Cast-Crepaldi
# ==================================================================================
import locale
from datetime import datetime, date

# ==================================================================================
# CONFIGURAÇÃO DE LOCALE (sem chamadas Streamlit diretas)
# ==================================================================================
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        # Evita usar st.warning fora de função (causa erro no Cloud)
        print("Aviso: Locale 'pt_BR.UTF-8' não encontrado. Meses podem aparecer em inglês.")

# ==================================================================================
# DICIONÁRIOS DE MESES (Português + Inglês)
# ==================================================================================
MESES_PARA_NUMEROS = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

# ==================================================================================
# FUNÇÕES DE DATA E VARIÁVEIS
# ==================================================================================
def get_date_range(tipo_periodo, session_state):
    """Retorna a data inicial e final com base no tipo de período selecionado."""
    hoje = date.today()
    ano_atual = hoje.year

    if tipo_periodo == "Mensal":
        inicio = date(ano_atual, 1, 1)
        fim = date(ano_atual, 12, 31)

    elif tipo_periodo == "Sazonal":
        inicio = date(ano_atual, 12, 1)
        fim = date(ano_atual, 2, 28)

    elif tipo_periodo == "Anual":
        inicio = date(ano_atual, 1, 1)
        fim = date(ano_atual, 12, 31)

    else:  # Personalizado ou outros
        inicio = hoje.replace(month=1, day=1)
        fim = hoje

    return inicio, fim


def get_variable_config(tipo_variavel):
    """Retorna o dataset e parâmetros de visualização conforme a variável."""
    if tipo_variavel == "Precipitação":
        return {
            "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
            "vis_params": {"min": 0, "max": 50, "palette": ["#edf8fb", "#b2e2e2", "#66c2a4", "#238b45"]},
            "unit": "mm/dia"
        }

    elif "Temperatura" in tipo_variavel:
        return {
            "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
            "vis_params": {"min": -10, "max": 40, "palette": ["#313695", "#74add1", "#ffffbf", "#f46d43", "#a50026"]},
            "unit": "°C"
        }

    elif tipo_variavel == "Umidade do Solo":
        return {
            "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
            "vis_params": {"min": 0, "max": 100, "palette": ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45"]},
            "unit": "%"
        }

    else:
        return {
            "dataset": "ECMWF/ERA5_LAND/DAILY_AGGR",
            "vis_params": {"min": 0, "max": 1, "palette": ["#f7fbff", "#4292c6", "#084594"]},
            "unit": "-"
        }
