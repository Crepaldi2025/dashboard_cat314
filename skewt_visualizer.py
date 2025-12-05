# ==================================================================================
# skewt_visualizer.py
# ==================================================================================
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64

try:
    from metpy.plots import SkewT, Hodograph
    from metpy.units import units
    import metpy.calc as mpcalc
    METPY_AVAILABLE = True
except ImportError:
    METPY_AVAILABLE = False

def render_skewt_plot(df: pd.DataFrame, lat, lon, date, hour):
    if not METPY_AVAILABLE:
        st.error("⚠️ A biblioteca `metpy` não está instalada.")
        return

    if df is None or df.empty:
        st.warning("Dados insuficientes para gerar o diagrama.")
        return

    # Unidades
    try:
        p = df['pressure'].values * units.hPa
        T = df['temperature'].values * units.degC
        rh = df['relative_humidity'].values / 100.0
        u = (df['u_component'].values * units('m/s')).to(units.knots)
        v = (df['v_component'].values * units('m/s')).to(units.knots)
        Td = mpcalc.dewpoint_from_relative_humidity(T, rh)
    except Exception as e:
        st.error(f"Erro dados: {e}")
        return

    # Figura
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')
    
    try:
        interval = np.arange(100, 1000, 50) * units.hPa
        idx = mpcalc.resample_nn_1d(p, interval)
        skew.plot_barbs(p[idx], u[idx], v[idx])
    except: pass

    skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='orange')
    skew.plot_moist_adiabats(t0=np.arange(233, 400, 5) * units.K, alpha=0.25, color='green')
    skew.plot_mixing_lines(pressure=np.arange(1000, 99, -20) * units.hPa, linestyle='dotted', color='blue')

    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    
    # Título (Usa a data real retornada pela API se disponível)
    real_date = df.attrs.get('real_date', date)
    source_label = df.attrs.get('source', 'ERA5')
    
    date_str = real_date.strftime('%d/%m/%Y')
    plt.title(f"Diagrama Skew-T ({source_label})\nLat: {lat} | Lon: {lon} | {date_str} {hour}:00 UTC", loc='left', fontsize=10)

    # Termodinâmica
    cape_val, cin_val, lcl_val = 0, 0, 0
    try:
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        skew.plot(p, prof, 'k', linewidth=2, linestyle='--', label='Parcela (SB)')
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
        skew.plot(lcl_pressure, lcl_temperature, 'ko', markerfacecolor='black')
        skew.shade_cin(p, T, prof, alpha=0.2)
        skew.shade_cape(p, T, prof, alpha=0.2)
        cape_val = cape.magnitude
        cin_val = cin.magnitude
        lcl_val = lcl_pressure.magnitude
    except: pass

    skew.ax.legend(loc='upper right', frameon=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("CAPE", f"{cape_val:.0f} J/kg")
    c2.metric("CIN", f"{cin_val:.0f} J/kg")
    c3.metric("LCL", f"{lcl_val:.0f} hPa")

    st.pyplot(fig)

    buf_png = io.BytesIO()
    fig.savefig(buf_png, format='png', dpi=150, bbox_inches='tight')
    buf_jpg = io.BytesIO()
    fig.savefig(buf_jpg, format='jpeg', dpi=150, bbox_inches='tight')

    cd1, cd2 = st.columns(2)
    with cd1: st.download_button("📷 PNG", buf_png.getvalue(), "skewt.png", "image/png", use_container_width=True)
    with cd2: st.download_button("📷 JPEG", buf_jpg.getvalue(), "skewt.jpg", "image/jpeg", use_container_width=True)
