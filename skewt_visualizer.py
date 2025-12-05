# ==================================================================================
# skewt_visualizer.py
# ==================================================================================
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64

# Tenta importar MetPy. Se não existir, define flag para avisar o usuário.
try:
    from metpy.plots import SkewT, Hodograph
    from metpy.units import units
    import metpy.calc as mpcalc
    METPY_AVAILABLE = True
except ImportError:
    METPY_AVAILABLE = False

def render_skewt_plot(df: pd.DataFrame, lat, lon, date, hour):
    """
    Gera o diagrama Skew-T Log-P usando dados de um DataFrame.
    Calcula CAPE, CIN, LCL e exibe na interface do Streamlit.
    """
    
    # 1. Verificação de Dependências
    if not METPY_AVAILABLE:
        st.error("⚠️ A biblioteca `metpy` não está instalada. Adicione `metpy` ao seu arquivo requirements.txt.")
        return

    # 2. Verificação de Dados
    if df is None or df.empty:
        st.warning("Dados insuficientes para gerar o diagrama.")
        return

    # 3. Preparação das Variáveis com Unidades (MetPy/Pint)
    try:
        # Pressão (hPa)
        p = df['pressure'].values * units.hPa
        
        # Temperatura (Graus Celsius)
        T = df['temperature'].values * units.degC
        
        # Umidade Relativa (0 a 1)
        # O handler retorna em %, então dividimos por 100
        rh = df['relative_humidity'].values / 100.0
        
        # Vento (U e V)
        # O handler entrega em m/s. Convertemos para nós (knots) para o gráfico padrão.
        u = (df['u_component'].values * units('m/s')).to(units.knots)
        v = (df['v_component'].values * units('m/s')).to(units.knots)

        # Cálculo do Ponto de Orvalho (Dewpoint)
        Td = mpcalc.dewpoint_from_relative_humidity(T, rh)

    except Exception as e:
        st.error(f"Erro ao processar unidades dos dados: {e}")
        return

    # 4. Configuração da Figura (Matplotlib)
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    # 5. Plotagem das Linhas Principais
    # Linha de Temperatura (Vermelha)
    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    
    # Linha de Ponto de Orvalho (Verde)
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')
    
    # Barbelas de Vento (Resampling para não poluir o gráfico)
    # Seleciona niveis a cada ~50hPa para plotar o vento
    try:
        interval = np.arange(100, 1000, 50) * units.hPa
        idx = mpcalc.resample_nn_1d(p, interval)
        skew.plot_barbs(p[idx], u[idx], v[idx])
    except:
        # Se falhar o resample (poucos dados), plota tudo ou pula
        pass

    # 6. Linhas de Fundo (Grades Termodinâmicas)
    # Adiabáticas Secas (Laranja)
    skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='orange')
    
    # Adiabáticas Úmidas (Verde)
    skew.plot_moist_adiabats(t0=np.arange(233, 400, 5) * units.K, alpha=0.25, color='green')
    
    # Linhas de Razão de Mistura (Azul pontilhado)
    skew.plot_mixing_lines(pressure=np.arange(1000, 99, -20) * units.hPa, linestyle='dotted', color='blue')

    # Ajuste dos Limites dos Eixos
    skew.ax.set_ylim(1000, 100) # De 1000hPa até 100hPa
    skew.ax.set_xlim(-40, 50)   # De -40°C a +50°C
    
    # Título do Gráfico
    source_label = df.attrs.get('source', 'Dados Atmosféricos')
    plt.title(f"Diagrama Skew-T ({source_label})\nLat: {lat} | Lon: {lon} | {date.strftime('%d/%m/%Y')} {hour}:00 UTC", loc='left', fontsize=10)

    # 7. Cálculos Termodinâmicos Avançados (Parcela, CAPE, CIN, LCL)
    cape_val, cin_val, lcl_val = 0, 0, 0
    
    try:
        # Perfil da Parcela (Surface Based - SB)
        # Calcula o caminho que uma parcela de ar faria se subisse da superfície
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        skew.plot(p, prof, 'k', linewidth=2, linestyle='--', label='Parcela (SB)')

        # Cálculo de CAPE e CIN
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        cape_val = cape.magnitude
        cin_val = cin.magnitude
        
        # Cálculo do Nível de Condensação por Levantamento (LCL)
        lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
        lcl_val = lcl_pressure.magnitude
        
        # Marca o LCL no gráfico (Ponto Preto)
        skew.plot(lcl_pressure, lcl_temperature, 'ko', markerfacecolor='black')
        
        # Sombreamento das áreas de CAPE (Instabilidade) e CIN (Inibição)
        skew.shade_cin(p, T, prof, alpha=0.2)  # Azulado/Cinza
        skew.shade_cape(p, T, prof, alpha=0.2) # Vermelho/Laranja

    except Exception as e:
        # Em caso de erro nos cálculos (ex: dados muito estáveis ou incompletos no topo),
        # segue gerando o gráfico sem essas áreas.
        # print(f"Aviso cálculo termodinâmico: {e}") 
        pass

    # Adiciona a Legenda
    skew.ax.legend(loc='upper right', frameon=True)

    # 8. Exibir Métricas no Streamlit
    c1, c2, c3 = st.columns(3)
    c1.metric("CAPE", f"{cape_val:.0f} J/kg", help="Convective Available Potential Energy (Energia potencial para tempestades)")
    c2.metric("CIN", f"{cin_val:.0f} J/kg", help="Convective Inhibition (Energia que impede a convecção)")
    c3.metric("LCL", f"{lcl_val:.0f} hPa", help="Nível de Condensação por Levantamento (Base das nuvens)")

    # 9. Renderizar Figura na Tela
    st.pyplot(fig)

    # 10. Botões de Exportação (Download)
    buf_png = io.BytesIO()
    fig.savefig(buf_png, format='png', dpi=150, bbox_inches='tight')
    
    buf_jpg = io.BytesIO()
    fig.savefig(buf_jpg, format='jpeg', dpi=150, bbox_inches='tight')

    col_down1, col_down2 = st.columns(2)
    with col_down1:
        st.download_button("📷 Baixar Diagrama (PNG)", buf_png.getvalue(), "skewt.png", "image/png", use_container_width=True)
    with col_down2:
        st.download_button("📷 Baixar Diagrama (JPEG)", buf_jpg.getvalue(), "skewt.jpg", "image/jpeg", use_container_width=True)
