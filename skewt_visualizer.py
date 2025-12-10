# ==================================================================================
# skewt_visualizer.py (COM CÁLCULO MANUAL DO LFC - FORÇA BRUTA)
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
except ImportError:
    METPY_AVAILABLE = False

def render_skewt_plot(df, lat, lon, date, hour):
    if not METPY_AVAILABLE:
        st.error("⚠️ Biblioteca 'MetPy' não instalada.")
        return

    if df is None or df.empty:
        st.warning("Sem dados para plotar.")
        return

    # --- 1. SUPER RESOLUÇÃO (Para capturar cruzamentos finos) ---
    try:
        # Ordena corretamente (1000 -> 100)
        df = df.sort_values("pressure", ascending=False).reset_index(drop=True)
        
        # Pega limites
        p_max = int(df["pressure"].max())
        p_min = int(df["pressure"].min())
        
        # Cria grade de 2 em 2 hPa (MUITO FINA)
        new_levels = range(p_max, p_min - 2, -2) 
        
        # Interpolação linear segura
        df_interp = df.set_index("pressure").reindex(new_levels)
        df_interp = df_interp.interpolate(method='linear')
        df_interp = df_interp.reset_index().rename(columns={'index': 'pressure'})
        
        data = df_interp # Usamos os dados finos para tudo agora
        
    except Exception as e:
        data = df # Fallback

    # --- 2. DADOS FÍSICOS ---
    try:
        p = data['pressure'].values * units.hPa
        T = data['temperature'].values * units.degC
        
        rh_vals = np.nan_to_num(data['relative_humidity'].values, nan=0.0)
        rh = rh_vals / 100.0
        
        u = (data['u_component'].values * units('m/s')).to('knots')
        v = (data['v_component'].values * units('m/s')).to('knots')

        Td = mpcalc.dewpoint_from_relative_humidity(T, rh)
    except Exception as e:
        st.error(f"Erro dados: {e}")
        return

    # --- 3. CÁLCULO MANUAL (BYPASS NO METPY LFC) ---
    # Aqui está o segredo. Não confiamos no mpcalc.lfc()
    
    cape, cin = None, None
    lcl_p, lcl_t = None, None
    lfc_p, lfc_t = None, None
    el_p, el_t = None, None
    prof = None
    li, k_idx, pw = None, None, None

    try:
        # 1. Acha NCL (LCL)
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        
        # 2. Calcula Perfil da Parcela
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        
        # 3. LÓGICA DE FORÇA BRUTA PARA O LFC
        # Regra: Primeiro ponto onde T_parcela > T_ambiente E Pressão < LCL
        
        # Array booleano: Onde a parcela é mais quente?
        is_warmer = prof.m > T.m
        
        # Array booleano: Onde estamos acima do LCL? (Pressão menor que LCL)
        above_lcl = p.m < lcl_p.m
        
        # Interseção: Parcela quente E acima do LCL
        instability_zone = is_warmer & above_lcl
        
        # Pega os índices onde isso acontece
        indices = np.where(instability_zone)[0]
        
        if len(indices) > 0:
            # O LFC é o PRIMEIRO ponto dessa zona (o de maior pressão)
            first_idx = indices[0] 
            
            # Pega o valor exato
            lfc_p = p[first_idx]
            
            # Interpola a temperatura nesse nível
            lfc_t = prof[first_idx]
        else:
            lfc_p = None # Estável, sem LFC

        # 4. Resto dos cálculos (CAPE/CIN/EL confiam no MetPy)
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        el_p, el_t = mpcalc.el(p, T, Td)
        li = mpcalc.lifted_index(p, T, prof)[0]
        pw = mpcalc.precipitable_water(p, Td)
        try: k_idx = mpcalc.k_index(p, T, Td)
        except: pass

    except Exception as e:
        # st.error(f"Erro calc: {e}")
        pass

    # --- 4. EXIBIÇÃO ---
    st.markdown("### 📊 Índices Termodinâmicos")

    st.markdown("""
        <style>
        /* Aumenta o número (Valor: 0 J/kg, 935 hPa...) */
        div[data-testid="stMetricValue"] {
            font-size: 1.2rem !important; /* Aumente este valor se quiser maior */
            font-weight: bold;
        }
        
        /* Aumenta o título (Rótulo: CAPE, CIN, LCL...) */
        div[data-testid="stMetricLabel"] {
            font-size: 1.2rem !important;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    # ------------------------------------


    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        def fmt(val, unit=""): return f"{val.magnitude:.0f} {unit}" if val is not None else "--"
        
        c1.metric("CAPE", fmt(cape, "J/kg"))
        c2.metric("CIN", fmt(cin, "J/kg"))
        c3.metric("LCL", fmt(lcl_p, "hPa"))
        c4.metric("LFC", fmt(lfc_p, "hPa"), help="Calculado via detecção térmica direta (Primeiro cruzamento > LCL).")

        c5, c6, c7, c8 = st.columns(4)
        li_str = f"{li.magnitude:.1f}" if li is not None else "--"
        c5.metric("LI", li_str)
        c6.metric("K-Index", f"{k_idx.magnitude:.0f}" if k_idx is not None else "--")
        c7.metric("Água Prec.", f"{pw.magnitude:.1f} mm" if pw is not None else "--")
        c8.metric("EL", fmt(el_p, "hPa"))

    # --- 5. PLOTAGEM ---
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')

    if prof is not None:
        skew.plot(p, prof, 'k', linewidth=1.5, linestyle='--', label='Parcela')
        if cape is not None and cape.magnitude > 0:
            skew.shade_cape(p, T, prof, alpha=0.2)
        if cin is not None and cin.magnitude < 0:
            skew.shade_cin(p, T, prof, alpha=0.2)

    # Marcadores
    if lcl_p is not None: skew.plot(lcl_p, lcl_t, 'ko', label='LCL')
    if lfc_p is not None: skew.plot(lfc_p, lfc_t, 'bo', label='LFC') # Plot do nosso LFC manual
    if el_p is not None: skew.plot(el_p, el_t, 'ro', label='EL')

    # Barbelas (Simplificadas)
    mask = (p.m % 50 == 0)
    if np.any(mask): skew.plot_barbs(p[mask], u[mask], v[mask])
    
    skew.plot_dry_adiabats(alpha=0.3)
    skew.plot_moist_adiabats(alpha=0.3)
    skew.plot_mixing_lines(linestyle='dotted', alpha=0.4)
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    
    # Título
    real_date = df.attrs.get('real_date', date)
    d_str = real_date if isinstance(real_date, str) else real_date.strftime('%d/%m/%Y')
    src = df.attrs.get('source', 'ERA5/GFS')
    plt.title(f"Skew-T | {d_str} {hour}:00 UTC\n{lat:.2f}, {lon:.2f} | {src}", loc='left')
    skew.ax.legend(loc='upper right')

    st.pyplot(fig)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    st.download_button("📷 Baixar Gráfico", buf.getvalue(), "skewt.png", "image/png")


