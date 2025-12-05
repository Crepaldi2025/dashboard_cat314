# ==================================================================================
# skewt_visualizer.py
# ==================================================================================
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64

# Tenta importar MetPy. Se não existir, avisa o usuário.
try:
    from metpy.plots import SkewT, Hodograph
    from metpy.units import units
    import metpy.calc as mpcalc
    METPY_AVAILABLE = True
except ImportError:
    METPY_AVAILABLE = False

def render_skewt_plot(df: pd.DataFrame, lat, lon, date, hour):
    if not METPY_AVAILABLE:
        st.error("⚠️ A biblioteca `metpy` não está instalada. Adicione `metpy` ao seu ambiente Python.")
        return

    if df is None or df.empty:
        st.warning("Dados insuficientes para gerar o diagrama.")
        return

    # 1. Preparação dos Dados com Unidades (Pint)
    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    rh = df['relative_humidity'].values / 100.0
    ws = (df['wind_speed'].values * units('km/h')).to(units.knots) # Skew-T usa nós geralmente
    wd = df['wind_direction'].values * units.degrees

    # Calcular Dewpoint (Td) e Componentes do Vento (u, v)
    Td = mpcalc.dewpoint_from_relative_humidity(T, rh)
    u, v = mpcalc.wind_components(ws, wd)

    # 2. Configuração da Figura
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    # 3. Plotagem das Linhas Principais
    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')
    
    # Plotar Barbelas de Vento (apenas alguns níveis para não poluir)
    # Pula alguns níveis se tiver muitos dados
    interval = np.arange(100, 1000, 50) * units.hPa
    idx = mpcalc.resample_nn_1d(p, interval)
    skew.plot_barbs(p[idx], u[idx], v[idx])

    # 4. Linhas de Fundo (Adiabáticas, Razão de Mistura)
    skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='orange')
    skew.plot_moist_adiabats(t0=np.arange(233, 400, 5) * units.K, alpha=0.25, color='green')
    skew.plot_mixing_lines(pressure=np.arange(1000, 99, -20) * units.hPa, linestyle='dotted', color='blue')

    # Limites e Títulos
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    plt.title(f"Diagrama Skew-T Log-P (ERA5)\nLat: {lat} | Lon: {lon} | {date.strftime('%d/%m/%Y')} {hour}:00 UTC", loc='left', fontsize=10)

    # 5. Cálculos Termodinâmicos (CAPE, CIN, LCL)
    try:
        # Perfil da Parcela (Surface Based)
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        skew.plot(p, prof, 'k', linewidth=2, linestyle='--', label='Parcela (SB)')

        # CAPE e CIN
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        
        # Nível de Condensação por Levantamento (LCL)
        lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
        skew.plot(lcl_pressure, lcl_temperature, 'ko', markerfacecolor='black')
        
        # Sombreamento do CAPE/CIN
        skew.shade_cin(p, T, prof, alpha=0.2)
        skew.shade_cape(p, T, prof, alpha=0.2)

    except Exception as e:
        cape, cin = 0 * units('J/kg'), 0 * units('J/kg')
        print(f"Erro no cálculo termodinâmico: {e}")

    # Legenda
    skew.ax.legend(loc='upper right', frameon=True)

    # 6. Exibir Estatísticas na Tela
    c1, c2, c3 = st.columns(3)
    c1.metric("CAPE", f"{cape.magnitude:.0f} J/kg")
    c2.metric("CIN", f"{cin.magnitude:.0f} J/kg")
    c3.metric("LCL", f"{lcl_pressure.magnitude:.0f} hPa")

    # 7. Renderizar no Streamlit
    st.pyplot(fig)

    # 8. Exportação
    buf_png = io.BytesIO()
    fig.savefig(buf_png, format='png', dpi=150, bbox_inches='tight')
    buf_jpg = io.BytesIO()
    fig.savefig(buf_jpg, format='jpeg', dpi=150, bbox_inches='tight')

    col_down1, col_down2 = st.columns(2)
    with col_down1:
        st.download_button("📷 Baixar Diagrama (PNG)", buf_png.getvalue(), "skewt.png", "image/png", use_container_width=True)
    with col_down2:
        st.download_button("📷 Baixar Diagrama (JPEG)", buf_jpg.getvalue(), "skewt.jpg", "image/jpeg", use_container_width=True)