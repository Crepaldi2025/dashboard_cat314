# utils.py

"""
utils.py — Funções auxiliares do sistema Clima-Cast-Crepaldi
------------------------------------------------------------
Este módulo contém funções utilitárias usadas em diferentes partes do dashboard,
principalmente para manipulação de datas e períodos selecionados pelo usuário.
"""

from datetime import date
import calendar

"""
Mapeamento entre nomes de meses (em português) e seus respectivos números (1 a 12).
Esse dicionário é usado para converter a escolha do usuário (ex: "Março") em valores numéricos
reconhecidos pelo módulo `calendar`.
"""

# ============================================================
# Dicionário de meses (Português + fallback em Inglês)
# ============================================================
MESES_PARA_NUMEROS = {
    # Português
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
    # Inglês (fallback)
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}


def get_date_range(tipo_periodo, session_state):
    """
    Retorna as datas de início e fim de análise com base no tipo de período selecionado.
    Parâmetros
    ----------
    tipo_periodo : str
    Pode ser "Personalizado", "Mensal" ou "Anual".
    session_state : streamlit.runtime.state.session_state
    Contém os valores selecionados pelo usuário na interface (datas, mês, ano etc.).
    Retorna
    -------
    tuple (date, date)
    Datas de início e fim do período correspondente.
    """
    if tipo_periodo == "Personalizado":
        return session_state.data_inicio, session_state.data_fim

    elif tipo_periodo == "Anual":
        ano = session_state.ano_anual
        return date(ano, 1, 1), date(ano, 12, 31)

    elif tipo_periodo == "Mensal":
        ano = session_state.ano_mensal
        mes_nome = session_state.mes_mensal
        mes_num = MESES_PARA_NUMEROS[mes_nome.capitalize()]
        ultimo_dia = calendar.monthrange(ano, mes_num)[1]
        return date(ano, mes_num, 1), date(ano, mes_num, ultimo_dia)
    
# Caso o tipo de período não seja reconhecido, retorna None (tratado posteriormente em main.py)
    

    return None, None
