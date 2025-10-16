# utils.py
from datetime import date
import calendar

# Dicionário com os nomes dos meses em português e com a primeira letra maiúscula
MESES_PARA_NUMEROS = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}

def get_date_range(tipo_periodo, session_state):
    """
    Calcula as datas de início e fim com base na seleção do usuário.
    """
    if tipo_periodo == "Personalizado":
        return session_state.data_inicio, session_state.data_fim

    elif tipo_periodo == "Anual":
        ano = session_state.ano_anual
        return date(ano, 1, 1), date(ano, 12, 31)

    elif tipo_periodo == "Mensal":
        ano = session_state.ano_mensal
        mes_nome = session_state.mes_mensal
        
        # --- INÍCIO DA CORREÇÃO ---
        # Garante que a primeira letra do mês seja maiúscula antes da busca no dicionário.
        # Ex: "janeiro" -> "Janeiro"
        mes_num = MESES_PARA_NUMEROS[mes_nome.capitalize()]
        # --- FIM DA CORREÇÃO ---
        
        # Encontra o último dia do mês
        ultimo_dia = calendar.monthrange(ano, mes_num)[1]
        
        return date(ano, mes_num, 1), date(ano, mes_num, ultimo_dia)
    
    return None, None