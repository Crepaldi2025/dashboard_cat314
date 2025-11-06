# utils.py (Corrigido)

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

MESES_PARA_NUMEROS = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
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
        
        # Garante que o nome do mês capitalizado exista no dicionário
        mes_num = MESES_PARA_NUMEROS.get(mes_nome.capitalize(), 1)
        
        ultimo_dia = calendar.monthrange(ano, mes_num)[1]
        return date(ano, mes_num, 1), date(ano, mes_num, ultimo_dia)
    
    # Caso o tipo de período não seja reconhecido
    return None, None