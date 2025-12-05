# ==================================================================================
# skewt_visualizer.py
# ==================================================================================
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io

try:
    from metpy.plots import SkewT
    from metpy.units import units
    import metpy.calc as mpcalc
    METPY_AVAILABLE = True
except: METPY_AVAILABLE = False

def render_skewt_plot(df, lat, lon, date, hour):
    if not METPY_AVAILABLE:
        st.error("Erro: Instale 'MetPy' no requirements.txt")
        return

    # Preparação das Variáveis
    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    rh = df['relative_humidity'].values / 100.0
    u = (df['u_component'].values * units('m/s')).to('knots')
    v = (df['v_component'].values * units('m/s')).to('knots')
    Td = mpcalc.dewpoint_from_relative_humidity(T, rh)

    # Configuração do Gráfico
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)
    skew.plot(p, T, 'r', linewidth=2, label='Temp')
    skew.plot(p, Td, 'g', linewidth=2, label='Dewpoint')
    
    # Barbelas de Vento (apenas onde existe pressão múltipla de 50)
    mask = p.m % 50 == 0 
    # Fallback simples se a mask ficar vazia
    if not any(mask): mask = slice(None, None, 2)
    skew.plot_barbs(p[mask], u[mask], v[mask])

    # Linhas de fundo
    skew.plot_dry_adiabats(alpha=0.3)
    skew.plot_moist_adiabats(alpha=0.3)
    skew.plot_mixing_lines(linestyle='dotted')

    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    
    # Título
    real_date = df.attrs.get('real_date', date)
    src = df.attrs.get('source', '')
    plt.title(f"Skew-T | {real_date.strftime('%d/%m/%Y')} {hour}h UTC | {src}")

    # Cálculos Termodinâmicos
    cape_val, cin_val, lcl_val = 0, 0, 0
    try:
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        skew.plot(p, prof, 'k', linestyle='--')
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        skew.plot(lcl_p, lcl_t, 'ko')
        
        cape_val = cape.magnitude
        cin_val = cin.magnitude
        lcl_val = lcl_p.magnitude
    except: pass

    skew.ax.legend()
    
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("CAPE", f"{cape_val:.0f} J/kg")
    c2.metric("CIN", f"{cin_val:.0f} J/kg")
    c3.metric("LCL", f"{lcl_val:.0f} hPa")

    st.pyplot(fig)
    
    # Botões de Download
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    st.download_button("📷 Baixar PNG", buf.getvalue(), "skewt.png", "image/png")
