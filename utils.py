# -------------------------------------------------------------------------------------------------
# utils.py - Funções utilitárias
# -------------------------------------------------------------------------------------------------

# ----------------------
# - Importar bibliotecas
# ----------------------

from datetime import date
import calendar

# ---------------------
# - Mapeamento de meses
# ---------------------

MESES_PARA_NUMEROS = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}

# -------------------
# - Função para datas
# -------------------

def get_date_range(tipo_periodo, session_state):
    
    if tipo_periodo == "Personalizado":
        return session_state.data_inicio, session_state.data_fim

    elif tipo_periodo == "Anual":
        ano = session_state.ano_anual
        return date(ano, 1, 1), date(ano, 12, 31)

    elif tipo_periodo == "Mensal":
        ano = session_state.ano_mensal
        mes_nome = session_state.mes_mensal
        mes_num = MESES_PARA_NUMEROS.get(mes_nome.capitalize(), 1)
        
        ultimo_dia = calendar.monthrange(ano, mes_num)[1]
        return date(ano, mes_num, 1), date(ano, mes_num, ultimo_dia)
    
return None, None
