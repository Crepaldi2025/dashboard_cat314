# ==================================================================================
# ui.py
# ==================================================================================

import streamlit as st
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import locale
import docx
import os
import requests
import pypandoc
import tempfile
import pytz
import re

# ------------------------------
# Configuração da Página e Cache
# ------------------------------



try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    pass 

NOMES_MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

@st.cache_data
def _carregar_texto_docx(file_path):
    if not os.path.exists(file_path): return None 
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n\n".join(full_text)
    except Exception: return None

# --- FUNÇÃO AUXILIAR PARA BUSCAR NO IBGE (FALLBACK) ---
@st.cache_data
def get_municipios_ibge(uf_sigla):
    """Busca municípios diretamente do IBGE se o cache local falhar."""
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sigla}/municipios"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return sorted([m['nome'] for m in response.json()])
    except Exception as e:
        st.error(f"Falha na consulta ao IBGE: {type(e).__name__}: {e}")
    return []
# -----------------------
# Apagar dados da memória
# -----------------------

def reset_analysis_state():
    for key in ['analysis_triggered', 'analysis_results', 'drawn_geometry', 'skewt_results', 'hydro_shape']:
        if key in st.session_state: del st.session_state[key]

def reset_analysis_results_only():
    for key in ['analysis_triggered', 'analysis_results']:
        if key in st.session_state: del st.session_state[key]

# --------------------------
# Renderizar a barra lateral
# --------------------------

def renderizar_sidebar(dados_geo, mapa_nomes_uf):
    with st.sidebar:
        # --- 1. TÍTULO ---
        st.markdown("<h2 style='text-align: center;'>🌦️ Clima-Cast-Crepaldi</h2>", unsafe_allow_html=True)
        st.markdown("---")

        # --- 2. NAVEGAÇÃO PRINCIPAL ---
        st.radio(
            "Modo de Visualização",
            ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile", "Séries Temporais", "Múltiplas Séries", "Skew-T", "Sobre o Aplicativo"],
            label_visibility="collapsed", 
            key='nav_option',
            on_change=reset_analysis_state
        )
        
        opcao = st.session_state.get('nav_option', 'Mapas')

        # --- OPÇÃO SKEW-T ---
        if opcao == "Skew-T":
            st.markdown("### Diagrama Skew-T")
            st.info("Obtém perfil vertical da atmosfera (semelhante a radiossonda) usando dados do modelo GFS. Inclui perfil de temperatura do ar, temperatura do ponto de orvalho, trajetória da parcela, informações dos ventos, além de alguns índices termodinâmicos.")

            st.markdown(
                """
                <div style="font-size: 0.85rem; color: #444; background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px; border-left: 3px solid #ffbd45;">
                <b>Como obter as coordenadas:</b><br>
                Abra o <b>Google Maps</b>, clique com o <b>botão direito</b> no local desejado e os números aparecerão no topo da lista (ex: -23.55, -46.63).
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.divider()
            st.markdown("#### Localização Pontual")
            
            c1, c2 = st.columns(2)
            with c1: st.number_input("Lat", value=-23.55, format="%.4f", key='skew_lat', on_change=reset_analysis_state)
            with c2: st.number_input("Lon", value=-46.63, format="%.4f", key='skew_lon', on_change=reset_analysis_state)
            
            st.divider()
            st.markdown("#### Momento")
            
            hoje = datetime.now()
            data_padrao = hoje - relativedelta(days=0) 
            
            st.date_input("Data", value=data_padrao, max_value=hoje, key='skew_date', format="DD/MM/YYYY", on_change=reset_analysis_state)
            st.slider("Hora (UTC)", 0, 23, 12, key='skew_hour', help="Hora em UTC (3 horas à frente de Brasília).", on_change=reset_analysis_state)


            st.warning(
                "**Nota:** Dados de altitude (3D/Perfil Vertical) estão disponíveis apenas a partir de **23/03/2021** "
                "(limite do GFS). Para datas anteriores, apenas dados de superfície (2D) podem ser consultados."
            )

            st.divider()

            st.markdown(
                """
                <div style="font-size:0.8rem; color:#666; margin-bottom:10px; margin-top:15px;">
                <b>Atenção:</b> Confira os filtros antes de gerar.
                </div>
                """,
                unsafe_allow_html=True
            )

            st.button(
                "Gerar Skew-T", 
                type="primary", 
                use_container_width=True, 
                on_click=lambda: st.session_state.update(analysis_triggered=True)
            )

        # --- OPÇÕES GERAIS ---
        elif opcao in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile", "Séries Temporais", "Múltiplas Séries"]:
            st.markdown("### Parâmetros da Análise")
            
            # --- 3. BASE DE DADOS ---
            st.markdown("#### Base de Dados", help="Reanálise climática global de alta resolução (ECMWF).")
            st.selectbox(
                "Selecione a Base de Dados", 
                ["ERA5-LAND"], 
                key='base_de_dados', 
                on_change=reset_analysis_state,
                label_visibility="collapsed"
            )

            st.divider()

            # --- 4. VARIÁVEL ---
            st.markdown("#### Variável Meteorológica")
            
            lista_vars = [
                "Temperatura do Ar (2m)", 
                "Temperatura do Ponto de Orvalho (2m)",
                "Temperatura da Superfície (Skin)",
                "Precipitação Total", 
                "Umidade Relativa (2m)", 
                "Umidade do Solo (0-7 cm)",
                "Umidade do Solo (7-28 cm)",
                "Umidade do Solo (28-100 cm)",
                "Umidade do Solo (100-289 cm)",
                "Velocidade do Vento (10m)", 
                "Radiação Solar Incidente"
            ]

            if opcao in ["Múltiplos Mapas", "Múltiplas Séries"]:
                vars_sel = st.multiselect(
                    "Selecione até 4 variáveis:", 
                    lista_vars, 
                    default=["Temperatura do Ar (2m)", "Precipitação Total"],
                    key='variaveis_multiplas',
                    on_change=reset_analysis_state
                )
                if len(vars_sel) > 4:
                    st.warning(f"Você selecionou {len(vars_sel)} variáveis. O limite recomendado é 4 para não travar o sistema.")
            
            elif opcao == "Sobreposição (Camadas)":
                st.caption("Selecione duas variáveis para comparar:")
                st.selectbox("1ª Camada (Base/Esquerda):", lista_vars, index=0, key='var_camada_1', on_change=reset_analysis_state)
                st.selectbox("2ª Camada (Topo/Direita):", lista_vars, index=3, key='var_camada_2', on_change=reset_analysis_state)
                
                st.markdown("---")
                
                vis_mode = st.radio("Estilo de Comparação:", ["Transparência", "Split Map (Cortina)"], horizontal=True, key='overlay_mode', on_change=reset_analysis_results_only)
                
                if vis_mode == "Transparência":
                    st.markdown("**Controle de Opacidade**")
                    c_op1, c_op2 = st.columns(2)
                    with c_op1: st.slider("Base", 0.0, 1.0, 1.0, key='opacity_1', on_change=reset_analysis_results_only)
                    with c_op2: st.slider("Topo", 0.0, 1.0, 0.6, key='opacity_2', on_change=reset_analysis_results_only)
            
            else:
                st.selectbox(
                    "Selecione a Variável", 
                    lista_vars, 
                    key='variavel', 
                    on_change=reset_analysis_state,
                    label_visibility="collapsed"
                )
            
            st.divider()

            # --- 5. LOCALIZAÇÃO / SHAPEFILE ---
            tipo_loc = "N/A" 

            if opcao == "Shapefile":
                st.markdown("#### Shapefile")

                # 👇 --- INSIRA O BLOCO AQUI (ANTES DO INFO/UPLOAD) --- 👇
                with st.sidebar.expander("Não tem um Shapefile? Aprenda a criar!", expanded=False):
                    st.markdown("""
                    1. Acesse o site **[GeoJSON.io](https://geojson.io)** (clique no link).
                    2. Navegue no mapa até encontrar a área desejada (fazenda, bairro, bacia).
                    3. Use a ferramenta de Polígono (ícone de pentágono na lateral direita do mapa) e desenhe o contorno clicando ponto a ponto.
                    4. No menu superior, vá em Save > Shapefile.
                    5. O site baixará automaticamente um arquivo .zip. 6 Salve este aquivo .zip no seu computador/laptop
                    6. Pronto! Basta enviar esse arquivo .zip aqui no painel lateral do Clima-Cast.
                    """)

                               
                # --------------------------------------------------------
                
                st.info("Envie um arquivo **.ZIP** contendo o polígono de interesse (obrigatório: .shp, .shx, .dbf). Ex: Fazenda, Bacia, Área de Proteção.")
                
                uploaded_file = st.file_uploader("Upload ZIP", type=["zip"], key='shapefile_upload', on_change=reset_analysis_state)
                
                if uploaded_file:
                    st.success("Arquivo recebido! Clique em Gerar Análise.")
                
                tipo_loc = "Shapefile"
                
            else:
                st.markdown("#### Localização")
                st.selectbox(
                    "Tipo de Recorte", 
                    ["Estado", "Município", "Círculo (Lat/Lon/Raio)", "Polígono"], 
                    key='tipo_localizacao', 
                    on_change=reset_analysis_state
                ) 
                
                tipo_loc = st.session_state.get('tipo_localizacao', 'Estado')
                
                # Garante que mapa_nomes_uf não esteja vazio
                if not mapa_nomes_uf:
                    mapa_nomes_uf = {'AC':'Acre','AL':'Alagoas','AP':'Amapá','AM':'Amazonas','BA':'Bahia','CE':'Ceará','DF':'Distrito Federal','ES':'Espírito Santo','GO':'Goiás','MA':'Maranhão','MT':'Mato Grosso','MS':'Mato Grosso do Sul','MG':'Minas Gerais','PA':'Pará','PB':'Paraíba','PR':'Paraná','PE':'Pernambuco','PI':'Piauí','RJ':'Rio de Janeiro','RN':'Rio Grande do Norte','RS':'Rio Grande do Sul','RO':'Rondônia','RR':'Roraima','SC':'Santa Catarina','SP':'São Paulo','SE':'Sergipe','TO':'Tocantins'}

                lista_ufs = ["Selecione..."] + [f"{mapa_nomes_uf[uf]} - {uf}" for uf in sorted(mapa_nomes_uf)]

                if tipo_loc == "Estado":
                    st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
                
                elif tipo_loc == "Município":
                    st.selectbox("UF", lista_ufs, key='estado', on_change=reset_analysis_state)
                    
                    estado_str = st.session_state.get('estado', 'Selecione...')
                    lista_muns = ["Selecione um estado primeiro"]
                    
                    if estado_str != "Selecione...":
                         # Pega a sigla (sempre os 2 últimos)
                         uf_sigla = estado_str[-2:]
                         
                         # Tenta pegar do cache local
                         muns = dados_geo.get(uf_sigla, [])
                         
                         # Se o cache falhar ou estiver vazio, busca direto do IBGE
                         if not muns:
                             muns = get_municipios_ibge(uf_sigla)
                         
                         if muns: 
                             lista_muns = ["Selecione..."] + sorted(muns)
                         else:
                             lista_muns = [f"Erro ao carregar cidades de {uf_sigla}"]
                    
                    st.selectbox("Município", lista_muns, key='municipio', on_change=reset_analysis_state)
                
                elif tipo_loc == "Círculo (Lat/Lon/Raio)":

                    st.markdown(
                        """
                        <div style="font-size: 0.85rem; color: #444; background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px; border-left: 3px solid #ffbd45;">
                        <b>Como obter as coordenadas:</b><br>
                        Abra o <b>Google Maps</b>, clique com o <b>botão direito</b> no local desejado e os números aparecerão no topo da lista (ex: -22.42, -45.45).
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

                    
                    c1, c2 = st.columns(2)
                    with c1: st.number_input("Lat", value=-22.42, format="%.4f", key='latitude', on_change=reset_analysis_state)
                    with c2: st.number_input("Lon", value=-45.46, format="%.4f", key='longitude', on_change=reset_analysis_state)
                    st.number_input("Raio (km)", min_value=1.0, value=10.0, step=1.0, key='raio', on_change=reset_analysis_state)
                    
                    with st.popover("Ajuda: Definindo o Círculo"):
                        st.markdown("**1. Coordenadas (Latitude e Longitude)**")
                        st.markdown("Devem estar em **Graus Decimais** (ex: `-22.42`).\n*")
                        st.markdown("") 
                        st.markdown("**2. Raio**")
                        st.markdown("Defina a distância em **Quilômetros (km)** do centro até a borda do círculo.")
                    
                    st.markdown("<div style='background-color:#e0f7fa;padding:10px;border-radius:5px;border-left:5px solid #00acc1;font-size:0.85em;'><b>Atenção:</b> se o recorte temporal for redefinido é necessário redesenhar o círculo.</div>", unsafe_allow_html=True)
                
                elif tipo_loc == "Polígono":
                    if st.session_state.get('drawn_geometry'): 
                        st.success("Polígono Definido")
                    else: 
                        st.markdown("<div style='background-color:#e0f7fa;padding:10px;border-radius:5px;border-left:5px solid #00acc1;font-size:0.85em;'><b style='color:#006064;'>Desenhe no Mapa Principal</b><br>Utilize as ferramentas na lateral esquerda do mapa.<br><br><b>Atenção:</b> se o recorte temporal for redefinido é necessário redesenhar o polígono.</div>", unsafe_allow_html=True)
                    
                    with st.popover("Guia de Ferramentas"): 
                        st.markdown("### Guia de Uso")
                        st.markdown("**Controles de Visualização**")
                        st.markdown("*  **Zoom:** Aproxima ou afasta a visão.\n*  **Tela Cheia:** Expande o mapa.\n*  **Camadas:** Alterna entre Satélite e Mapa de Ruas.")
                        st.markdown("---")
                        st.markdown("**Ferramentas de Desenho**")
                        st.markdown("*  **Polígono:** Clique ponto a ponto para fechar uma área livre.\n*  **Retângulo:** Clique e arraste para criar uma área quadrada.\n*  **Círculo:** Clique no centro e arraste para definir o raio.\n*  **Marcador:** Adiciona um pino em um local específico.\n*  **Linha:** Desenhe uma linha (útil para medir distâncias).")
                        st.markdown("---")
                        st.markdown("**Edição e Limpeza**")
                        st.markdown("*  **Editar:** Habilita os nós (pontos brancos) para ajustar o desenho.\n*  **Lixeira:** Apaga todos os desenhos feitos no mapa.")
                    
                    with st.expander("Inserir Coordenadas Manualmente"):
                        st.caption("Cole as coordenadas abaixo (formato: `Latitude, Longitude`), uma por linha.")
                        texto_coords = st.text_area("Coordenadas:", height=150, placeholder="-22.123, -45.123\n-22.150, -45.100\n-22.200, -45.200")
                        
                        if st.button("Processar Coordenadas"):
                            try:
                                pontos = []
                                linhas = texto_coords.strip().split('\n')
                                for linha in linhas:
                                    partes = linha.replace(';', ',').split(',')
                                    if len(partes) >= 2:
                                        lat = float(partes[0].strip())
                                        lon = float(partes[1].strip())
                                        pontos.append([lon, lat])
                                
                                if len(pontos) < 3:
                                    st.error("Um polígono precisa de pelo menos 3 pontos.")
                                else:
                                    if pontos and pontos[0] != pontos[-1]:
                                        pontos.append(pontos[0])
                                    geometria_manual = {"type": "Polygon", "coordinates": [pontos]}
                                    st.session_state.drawn_geometry = geometria_manual
                                    st.success("Polígono processado com sucesso!")
                                    st.rerun()
                            except ValueError:
                                st.error("Erro no formato. Certifique-se de usar apenas números e vírgulas/pontos.")
                            except Exception as e:
                                st.error(f"Erro ao processar: {e}")
            
            st.divider()

            # --- 6. PERÍODO ---
            st.markdown("#### Recorte Temporal")
            
            opcoes_periodo = ["Personalizado", "Mensal", "Anual"]
            if opcao in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile"]: 
                opcoes_periodo.append("Horário Específico")
            
            if opcao in ["Mapas", "Múltiplos Mapas", "Sobreposição (Camadas)", "Shapefile"]:
                st.selectbox("Tipo de Período", opcoes_periodo, key='tipo_periodo', on_change=reset_analysis_state, label_visibility="collapsed")
            else:
                st.session_state.tipo_periodo = "Personalizado"
            
            tipo_per = st.session_state.get('tipo_periodo', 'Personalizado')
            ano_atual = datetime.now().year
            lista_anos = list(range(ano_atual, 1949, -1))
            st.session_state.date_error = False
            
            min_data = datetime(1950, 1, 1)
            max_data = datetime.now()
            
            if tipo_per == "Personalizado":
                hoje = datetime.now()
                fim_padrao = hoje.replace(day=1) - relativedelta(days=1)
                inicio_padrao = fim_padrao.replace(day=1)
                c1, c2 = st.columns(2)
                with c1: st.date_input("Início", value=inicio_padrao, min_value=min_data, max_value=max_data, key='data_inicio', on_change=reset_analysis_state, format="DD/MM/YYYY")
                with c2: st.date_input("Fim", value=fim_padrao, min_value=min_data, max_value=max_data, key='data_fim', on_change=reset_analysis_state, format="DD/MM/YYYY")
                if st.session_state.data_fim < st.session_state.data_inicio:
                    st.error("Data final anterior à inicial.")
                    st.session_state.date_error = True
            
            elif tipo_per == "Mensal":
                c1, c2 = st.columns(2)
                with c1: st.selectbox("Ano", lista_anos, key='ano_mensal', on_change=reset_analysis_state)
                with c2: st.selectbox("Mês", NOMES_MESES_PT, key='mes_mensal', on_change=reset_analysis_state)
            
            elif tipo_per == "Anual":
                st.selectbox("Ano", lista_anos, key='ano_anual', on_change=reset_analysis_state)
            
            elif tipo_per == "Horário Específico":
                hoje = datetime.now()
                data_padrao = hoje - relativedelta(months=4)
                st.date_input("Data", value=data_padrao, min_value=min_data, max_value=max_data, key='data_horaria', on_change=reset_analysis_state, format="DD/MM/YYYY")
                st.slider("Hora (UTC)", 0, 23, 12, key='hora_especifica', on_change=reset_analysis_state, help="Hora em UTC (3 horas à frente de Brasília).")
                st.info("**Nota:** Esta opção retorna um dado pontual (snapshot) apenas para a hora escolhida.")
            
            st.divider()

            # --- 7. VISUALIZAÇÃO ---
            if opcao == "Mapas":
                st.markdown("#### Visualização")
                st.radio("Formato", ["Interativo", "Estático"], key='map_type', horizontal=True, on_change=reset_analysis_results_only, label_visibility="collapsed")
                st.divider()
            elif opcao == "Múltiplos Mapas":
                st.info("Modo Múltiplo gera mapas estáticos para comparação.")
            elif opcao == "Múltiplas Séries":
                st.info("Gera múltiplos gráficos simultâneos.")
            elif opcao == "Sobreposição (Camadas)":
                pass
            elif opcao == "Shapefile":
                st.info("Sobrepõe dados climáticos sobre o shapefile enviado.")

            # --- 8. BOTÃO DE AÇÃO ---
            disable = st.session_state.get('date_error', False)
            
            if tipo_loc == "Polígono" and not st.session_state.get('drawn_geometry'): disable = True
            elif tipo_loc == "Círculo (Lat/Lon/Raio)" and not (st.session_state.get('latitude') and st.session_state.get('longitude')): disable = True
            
            if opcao in ["Múltiplos Mapas", "Múltiplas Séries"]:
                vars_sel = st.session_state.get("variaveis_multiplas", [])
                if not vars_sel or len(vars_sel) > 4: disable = True
            
            if opcao == "Shapefile":
                if not st.session_state.get("shapefile_upload"): disable = True
                else: disable = False

            st.button(
                "Gerar Análise", 
                type="primary", 
                use_container_width=True, 
                disabled=disable,
                on_click=lambda: st.session_state.update(analysis_triggered=True)
            )
            
            if not disable:
                st.markdown(
                    "<div style='margin-top:6px;padding:10px 12px;border-radius:8px;"
                    "border-left:4px solid #d99a16;background:#fff6dc;"
                    "font-size:0.86rem;line-height:1.45;color:#453400;'>"
                    "<strong>Orientações para a análise</strong>"
                    "<p style='margin:5px 0;'>Verifique a variável meteorológica, "
                    "a região de interesse e o intervalo temporal selecionados.</p>"
                    "<p style='margin:5px 0;'>A resolução espacial e temporal depende "
                    "do produto utilizado. Consultas extensas podem exigir maior "
                    "tempo de processamento.</p>"
                    "<p style='margin:0;'>A disponibilidade dos dados está condicionada "
                    "à cobertura temporal da base de reanálise.</p>"
                    "</div>",
                    unsafe_allow_html=True
                )
            
            else:
                if opcao == "Shapefile" and not st.session_state.get("shapefile_upload"):
                    st.markdown("<div style='font-size:14px;color:#d32f2f;margin-top:8px;'><b>Obrigatório:</b> Faça upload do arquivo .ZIP.</div>", unsafe_allow_html=True)
                elif opcao in ["Múltiplos Mapas", "Múltiplas Séries"]:
                    vars_sel = st.session_state.get("variaveis_multiplas", [])
                    if not vars_sel:
                        st.markdown("<div style='font-size:14px;color:#d32f2f;margin-top:8px;'><b>Obrigatório:</b> Selecione pelo menos uma variável.</div>", unsafe_allow_html=True)
                    elif len(vars_sel) > 4:
                         st.markdown("<div style='font-size:14px;color:#d32f2f;margin-top:8px;'><b>Erro:</b> Remova variáveis até ficar com no máximo 4.</div>", unsafe_allow_html=True)
                else:
                     st.markdown("<div style='font-size:14px;color:#d32f2f;margin-top:8px;'><b>Obrigatório:</b> Defina a localização.</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("<div style='text-align:center;color:grey;font-size:12px;'>Desenvolvido por <b>Paulo C. Crepaldi</b><br>v2.0 | 2026</div>", unsafe_allow_html=True)
        
        return opcao

# -----------------------------
# Renderizar a página principal
# -----------------------------

def renderizar_pagina_principal(opcao):
    
    st.markdown("""<style>.block-container{padding-top:1rem!important;padding-bottom:1rem!important}h1{margin-top:0rem!important}.stExpander{border:1px solid #f0f2f6;border-radius:8px}</style>""", unsafe_allow_html=True)
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora, agora_utc = datetime.now(fuso_br), datetime.now(pytz.utc)
    
    c1, c2 = st.columns([3, 1.5])
    with c1:
        st.markdown(
            f"<div style='font-size:1.35rem;font-weight:650;line-height:1.2;"
            f"margin:0;padding:0;'>{opcao}</div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(f"<div style='border:1px solid #e0e0e0;padding:8px;text-align:center;border-radius:8px;background-color:rgba(255,255,255,0.7);font-size:0.9rem;'><img src='https://flagcdn.com/24x18/br.png' style='vertical-align:middle;margin-bottom:2px;'> <b>BRT:</b> {agora.strftime('%d/%m/%Y %H:%M')}<br><span style='color:#666;font-size:0.8rem;'>🌐 UTC: {agora_utc.strftime('%d/%m/%Y %H:%M')}</span></div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='border:0;border-top:1px solid #d1d5db;margin:0.1rem 0 0.2rem 0;'>",
        unsafe_allow_html=True
    )
    
    # LÓGICA DE LIMPEZA ATUALIZADA
    has_results = st.session_state.get("analysis_results") is not None
    has_skewt = st.session_state.get("skewt_results") is not None
    is_generating = st.session_state.get("analysis_triggered", False)

    if not has_results and not has_skewt and not is_generating:
        # Boas-vindas com fundo meteorológico somente na tela inicial.
        # O fundo fica neste painel para não afetar mapas, gráficos ou resultados.
        from pathlib import Path
        import base64

        fundo = Path(__file__).resolve().parent.parent / "assets" / "fundo_climacast.png"
        if fundo.is_file():
            imagem_base64 = base64.b64encode(fundo.read_bytes()).decode("ascii")
            estilo_fundo = (
                "background-image:linear-gradient("
                "rgba(255,255,255,0.48),rgba(255,255,255,0.48)),"
                f"url('data:image/png;base64,{imagem_base64}');"
                "background-position:center 44%;"
                "background-size:cover;"
            )
        else:
            estilo_fundo = "background:#edf4fb;"

        st.markdown(
            "<div style='" + estilo_fundo +
            "border:1px solid #dbe5f0;border-radius:9px;"
            "padding:15px 18px;margin:0 0 4px 0;'>"
            "<div style='font-size:1.28rem;font-weight:650;"
            "color:#172b4d;line-height:1.3;margin:0 0 5px 0;'>"
            "Bem-vindo ao Clima-Cast!</div>"
            "<div style='font-size:0.91rem;color:#334155;line-height:1.45;'>"
            "◀ Selecione a análise e configure os parâmetros na barra lateral."
            "</div></div>",
            unsafe_allow_html=True
        )

        # --- AQUI ESTÁ A NOTA DIDÁTICA ---
              
        col1, col2 = st.columns(2, gap="medium")

        with col1:
            st.markdown("#### Análise Espacial")
            st.markdown("""
            **Mapas** — Visualização espacial de uma variável meteorológica para a área e o período selecionados.
            
            **Múltiplos Mapas** — Comparação de até quatro variáveis em painéis estáticos.
            
            **Sobreposição de Camadas** — Comparação de duas variáveis no mesmo mapa, com transparência ou cortina deslizante.
            
            **Shapefile** — Importação de arquivos geográficos para delimitar áreas de análise.
            """)

        with col2:
            st.markdown("#### Análise Temporal e Vertical")
            st.markdown("""
            **Séries Temporais** — Análise da evolução de uma variável meteorológica ao longo do tempo.
            
            **Múltiplas Séries** — Comparação temporal de diferentes variáveis meteorológicas.
            
            **Skew-T/log-P** — Visualização de perfis atmosféricos modelados de temperatura, ponto de orvalho e vento, com parâmetros termodinâmicos.
            """)
        
        # Caixas informativas com contraste adequado ao fundo de satélite.
        st.markdown(
            "<div style='background:rgba(255,255,255,0.92);"
            "border:1px solid rgba(170,185,200,0.65);border-radius:8px;"
            "padding:12px 16px;margin:12px 0 10px 0;"
            "color:#243447;font-size:0.91rem;line-height:1.5;'>"
            "<b>Sobre os dados:</b> Os resultados utilizam agregações temporais "
            "que dependem da variável meteorológica, como médias ou acumulados. "
            "Para consultar um horário específico, selecione <b>Horário Específico</b> "
            "e informe a hora em UTC."
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div style='background:rgba(255,255,255,0.88);"
            "border:1px solid rgba(170,185,200,0.60);border-radius:8px;"
            "padding:10px 16px;margin:0 0 8px 0;"
            "color:#475569;font-size:0.82rem;line-height:1.5;'>"
            "<b>Fontes de dados:</b> ERA5-Land/ECMWF, via Google Earth Engine, "
            "para mapas e séries temporais; Open-Meteo, para perfis atmosféricos "
            "modelados utilizados no Skew-T."
            "</div>",
            unsafe_allow_html=True
        )

def renderizar_resumo_selecao():
    nav_option = st.session_state.get('nav_option')

    # --- LÓGICA PARA SKEW-T ---
    if nav_option == "Skew-T":
        with st.expander("Resumo das Opções Selecionadas", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.markdown("**Análise:**\nSondagem (Skew-T)")
            with c2:
                lat = st.session_state.get('skew_lat')
                lon = st.session_state.get('skew_lon')
                st.markdown(f"**Localização:**\nLat: {lat} | Lon: {lon}")
            with c3:
                date = st.session_state.get('skew_date')
                hour = st.session_state.get('skew_hour')
                data_str = date.strftime('%d/%m/%Y') if date else "--/--/----"
                st.markdown(f"**Momento:**\n{data_str} às {hour}:00 UTC")
        return

    # --- LÓGICA PARA MAPAS E SÉRIES ---
    label_titulo = "Variável:"
    var_text = ""
    
    if nav_option in ["Múltiplos Mapas", "Múltiplas Séries"]:
        vars_selected = st.session_state.get("variaveis_multiplas", [])
        if not vars_selected: return
        var_text = "  \n".join([f"• {v}" for v in vars_selected])
        label_titulo = "Variáveis:"
    elif nav_option == "Sobreposição (Camadas)":
        v1 = st.session_state.get("var_camada_1", "N/A")
        v2 = st.session_state.get("var_camada_2", "N/A")
        var_text = f"1. Base: {v1}  \n2. Topo: {v2}"
        label_titulo = "Camadas:"
    else:
        if "variavel" not in st.session_state: return
        var_text = st.session_state.variavel

    with st.expander("Resumo das Opções Selecionadas", expanded=False):

        st.markdown("""
            <style>
            /* Títulos dos quadros expansíveis */
            div[data-testid="stExpander"] details > summary p {
                font-size: 16px !important;
                font-weight: 600 !important;
                line-height: 1.5 !important;
            }
        
            /* Informações dentro dos quadros */
            div[data-testid="stExpander"] details > div
            div[data-testid="stMarkdownContainer"] p {
                font-size: 15px !important;
                line-height: 1.6 !important;
            }
            </style>
        """, unsafe_allow_html=True)
    
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"**{label_titulo}** \n{var_text}")
        with c2:
            if nav_option == "Shapefile":
                st.markdown("**Local:**\nShapefile Personalizado")
            else:
                tipo = st.session_state.tipo_localizacao
                local_txt = ""
                if tipo == "Estado": local_txt = st.session_state.estado
                elif tipo == "Município": local_txt = f"{st.session_state.municipio} ({st.session_state.estado})"
                elif tipo == "Círculo (Lat/Lon/Raio)": local_txt = "Área Circular"
                elif tipo == "Polígono": local_txt = "Polígono Personalizado"
                st.markdown(f"**Local ({tipo}):**\n{local_txt}")
        with c3:
            periodo = st.session_state.tipo_periodo
            per_txt = ""
            if periodo == "Personalizado": per_txt = f"{st.session_state.data_inicio.strftime('%d/%m/%Y')} - {st.session_state.data_fim.strftime('%d/%m/%Y')}"
            elif periodo == "Mensal": per_txt = f"{st.session_state.mes_mensal}/{st.session_state.ano_mensal}"
            elif periodo == "Anual": per_txt = str(st.session_state.ano_anual)
            elif periodo == "Horário Específico":
                 data = st.session_state.get('data_horaria')
                 hora = st.session_state.get('hora_especifica')
                 if data: per_txt = f"{data.strftime('%d/%m/%Y')} às {hora}:00h (UTC)"
            st.markdown(f"**Período ({periodo}):**\n{per_txt}")

# -------------------------------------
# Renderizar a opção sobre o aplicativo
# -------------------------------------

def renderizar_pagina_sobre():
    """Página Sobre do ClimaCast, sem conversão de DOCX para HTML."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    imagens = raiz / "assets"

    st.title("Sobre o ClimaCast")
    st.caption("Plataforma de consulta, análise e visualização de dados meteorológicos")
    st.markdown(
        "O Clima-Cast-Crepaldi foi desenvolvido no âmbito da disciplina "
        "CAT314 — Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting), "
        "do curso de Ciências Atmosféricas da Universidade Federal de Itajubá (UNIFEI). "
        "A plataforma apoia atividades didáticas de exploração e análise de dados meteorológicos."
    )

    st.subheader("Objetivo")
    st.write(
        "Oferecer acesso interativo a informações meteorológicas por meio de mapas, "
        "séries temporais e perfis verticais, com explicitação das fontes e limitações dos dados."
    )

    st.subheader("Funcionalidades")
    st.markdown(
        "- **Mapas estáticos e interativos:** representação espacial de variáveis meteorológicas.\n"
        "- **Séries temporais:** análise de sua evolução e de estatísticas descritivas.\n"
        "- **Seleção de áreas:** estados, municípios e recortes geográficos disponibilizados pela aplicação.\n"
        "- **Perfis atmosféricos Skew-T:** apresentação de temperatura, ponto de orvalho, vento e índices termodinâmicos.\n"
        "- **Exportação:** imagens e tabelas, conforme a funcionalidade selecionada."
    )

    st.subheader("Fontes de dados e processamento")
    st.write(
        "Para os produtos de superfície, a aplicação consulta os conjuntos "
        "ERA5-Land do ECMWF por meio do Google Earth Engine. "
        "Os mapas e as séries são produzidos mediante seleção de área, período e variável, "
        "seguida de agregação espacial e/ou temporal apropriada ao produto."
    )
    st.write(
        "Os perfis Skew-T são obtidos separadamente da Open-Meteo, com dados de modelos "
        "atmosféricos. Não devem ser identificados como perfis observados por radiossonda "
        "nem como perfis diretamente extraídos do ERA5-Land."
    )
    st.markdown(
        "**Fontes técnicas:** "
        "[ERA5-Land horário](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY) · "
        "[ERA5-Land diário](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR) · "
        "[Open-Meteo](https://open-meteo.com/en/docs)"
    )

    fluxo = imagens / "fluxo.png"
    if fluxo.is_file():
        with st.expander("Fluxo de processamento", expanded=False):
            st.image(str(fluxo), caption="Esquema ilustrativo do processamento da aplicação.", width=580)

    st.subheader("Limitações científicas")
    st.markdown(
        "- O ERA5-Land é uma **reanálise**, não uma observação pontual direta.\n"
        "- Sua resolução espacial nominal é da ordem de **9 km**; pequenas variações locais podem não ser resolvidas.\n"
        "- Agregações diárias podem ocultar eventos de curta duração.\n"
        "- A disponibilidade temporal e a latência dependem do produto e da atualização do catálogo.\n"
        "- Os perfis modelados e os índices convectivos dependem do modelo e da resolução vertical; "
        "não substituem uma radiossondagem."
    )

    st.subheader("Exemplos de produtos")
    exemplos = [
        ("mapa_interativo.png", "Exemplo de mapa interativo"),
        ("mapa_estatico.png", "Exemplo de mapa estático"),
        ("serie_temporal.png", "Exemplo de série temporal"),
    ]
    for nome, legenda in exemplos:
        caminho = imagens / nome
        if caminho.is_file():
            st.image(str(caminho), caption=legenda, width=620)
        else:
            st.caption(f"Imagem ilustrativa indisponível: {nome}")

    st.subheader("Público-alvo")
    st.write(
        "Estudantes, docentes, pesquisadores e profissionais das Ciências Atmosféricas "
        "e áreas relacionadas."
    )

    st.subheader("Autoria e documentação")
    st.write("**Autor:** Paulo C. Crepaldi")
    st.write("**Instituição:** Universidade Federal de Itajubá (UNIFEI), Instituto de Recursos Naturais")
    st.write("**Orientador acadêmico do projeto original:** Prof. Dr. Enrique Vieira Mattos")
    st.write("**Projeto iniciado em:** 2025")
    st.markdown("**Código-fonte:** [dashboard_cat314](https://github.com/Crepaldi2025/dashboard_cat314)")
    st.caption(
        "A licença e os termos de reutilização devem ser consultados no arquivo "
        "LICENSE do repositório, quando disponível."
    )























