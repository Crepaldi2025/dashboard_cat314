import streamlit as st
import ui  # Importa nosso módulo de interface

def main():
    """
    Função principal que organiza e executa a aplicação Streamlit.
    """
    # 1. Configura as propriedades da página (título, ícone, layout)
    ui.configurar_pagina()

    # 2. Renderiza a barra lateral com todos os seus elementos
    ui.renderizar_sidebar()

    # 3. Renderiza a área de conteúdo principal da página
    ui.renderizar_pagina_principal()

if __name__ == "__main__":
    main()