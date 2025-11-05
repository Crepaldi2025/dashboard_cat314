# ==================================================================================
# utils.py — Clima-Cast-Crepaldi (versão estável restaurada)
# ==================================================================================
import datetime as dt

# --------------------------------------------------------------------------
# Dicionários auxiliares
# --------------------------------------------------------------------------
MESES_PARA_NUMEROS = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
    "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}

# --------------------------------------------------------------------------
# Função principal para definir o intervalo de datas
# --------------------------------------------------------------------------
def get_date_range(tipo_periodo, session_state):
    """
    Retorna as datas inicial e final com base no tipo de período escolhido (Mensal ou Anual).
    """
    if tipo_periodo == "Mensal":
        ano = session_state.get("ano")
        mes_nome = session_state.get("mes")
        if ano is None or mes_nome is None:
            return None, None

        mes_num = MESES_PARA_NUMEROS.get(mes_nome.capitalize(), None)
        if mes_num is None:
            return None, None

        start_date = dt.date(ano, mes_num, 1)
        if mes_num == 12:
            end_date = dt.date(ano + 1, 1, 1)
        else:
            end_date = dt.date(ano, mes_num + 1, 1)
        return start_date, end_date

    elif tipo_periodo == "Anual":
        ano_inicio = session_state.get("ano_inicio")
        ano_fim = session_state.get("ano_fim")
        if ano_inicio is None or ano_fim is None:
            return None, None

        start_date = dt.date(ano_inicio, 1, 1)
        end_date = dt.date(ano_fim + 1, 1, 1)
        return start_date, end_date

    return None, None
