# ==================================================================================
# skewt_visualizer.py (VERSÃO CORRIGIDA COM INTERPOLAÇÃO PANDAS)
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

    # --- 1. AUMENTO DE RESOLUÇÃO (INTERPOLAÇÃO SEGURA) ---
    # Isso resolve o problema de pular o LFC (de 870 para 550 hPa)
    try:
        # Garante ordenação correta (Pressão decrescente: 1000 -> 100)
        df = df.sort_values("pressure", ascending=False).reset_index(drop=True)
        
        # Cria um novo índice de pressão mais fino (de 10 em 10 hPa)
        # Pega o máximo (chão) e mínimo (topo) dos dados originais
        p_max = int(df["pressure"].max())
        p_min = int(df["pressure"].min())
        
        # Cria a nova grade (ex: 1000, 990, 980... até 100)
        new_levels = range(p_max, p_min - 10, -10) 
        
        # Reindexa e interpola
        df_interp = df.set_index("pressure").reindex(new_levels)
        df_interp = df_interp.interpolate(method='linear') # Preenche os buracos
        df_interp = df_interp.reset_index().rename(columns={'index': 'pressure'})
        
        # Usa o dataframe interpolado daqui para frente
        data_source = df_interp
        
    except Exception as e:
        # Se der erro na interpolação, usa o original como fallback
        # st.warning(f"Usando resolução padrão (Erro interpolação: {e})")
        data_source = df

    # --- 2. PREPARAÇÃO DOS DADOS FÍSICOS ---
    try:
        # Extrai valores e aplica unidades
        p = data_source['pressure'].values * units.hPa
        T = data_source['temperature'].values * units.degC
        
        # Umidade (Evita valores NaN que podem quebrar o cálculo)
        rh_vals = data_source['relative_humidity'].values
        rh_vals = np.nan_to_num(rh_vals, nan=0.0) # Troca NaN por 0
        rh = rh_vals / 100.0
        
        # Vento (m/s para nós)
        u = (data_source['u_component'].values * units('m/s')).to('knots')
        v = (data_source['v_component'].values * units('m/s')).to('knots')

        # Calcula Ponto de Orvalho (MetPy)
        Td = mpcalc.dewpoint_from_relative_humidity(T, rh)
        
    except Exception as e:
        st.error(f"Erro ao processar dados físicos: {e}")
        return

    # --- 3. CÁLCULOS TERMODINÂMICOS ---
    cape, cin = None, None
    lcl_p, lfc_p, el_p = None, None, None
    li, k_idx, pw = None, None, None
    prof = None

    try:
        # Perfil da Parcela (Começando da superfície)
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        
        # CAPE e CIN
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        
        # Níveis (LCL, LFC, EL)
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        lfc_p, lfc_t = mpcalc.lfc(p, T, Td)
        el_p, el_t = mpcalc.el(p, T, Td)

        # Índices
        li = mpcalc.lifted_index(p, T, prof)[0]
        pw = mpcalc.precipitable_water(p, Td)
        
        # K-Index (Tenta calcular, se faltar nível ignora)
        try: k_idx = mpcalc.k_index(p, T, Td)
        except: pass

    except Exception as e:
        # Debug silencioso: print(f"Erro Calc: {e}")
        pass

    # --- 4. EXIBIÇÃO ---
    st.markdown("### 📊 Índices Termodinâmicos")
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        
        # Formatadores seguros
        def fmt(val, unit=""):
            return f"{val.magnitude:.0f} {unit}" if val is not None else "--"
        
        c1.metric("CAPE", fmt(cape, "J/kg"), help="Energia potencial para tempestades.")
        c2.metric("CIN", fmt(cin, "J/kg"), help="Inibição convectiva (tampa).")
        c3.metric("LCL", fmt(lcl_p, "hPa"), help="Base das nuvens.")
        c4.metric("LFC", fmt(lfc_p, "hPa"), help="Nível de convecção livre (início da subida espontânea).")

        c5, c6, c7, c8 = st.columns(4)
        
        li_str = f"{li.magnitude:.1f}" if li is not None else "--"
        c5.metric("LI", li_str, help="Lifted Index.")
        
        k_str = f"{k_idx.magnitude:.0f}" if k_idx is not None else "--"
        c6.metric("K-Index", k_str, help="Potencial de trovoadas.")
        
        pw_str = f"{pw.magnitude:.1f} mm" if pw is not None else "--"
        c7.metric("Água Precipitável", pw_str, help="Umidade total na coluna.")
        
        c8.metric("EL", fmt(el_p, "hPa"), help="Topo da nuvem (Nível de Equilíbrio).")

    # Tabela Referência
    with st.expander("📚 Tabela de Referência", expanded=False):
        st.markdown("| Índice | Estável | Instável |\n|---|---|---|\n| CAPE | < 1000 | > 2500 |\n| LI | > 0 | < -4 |")

    # --- 5. GRÁFICO SKEW-T ---
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    # Plota as curvas (usando dados interpolados para suavidade)
    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')

    try:
        if prof is not None:
            skew.plot(p, prof, 'k', linewidth=1.5, linestyle='--', label='Parcela')
            if cape is not None and cape.magnitude > 0:
                skew.shade_cape(p, T, prof, alpha=0.2)
            if cin is not None and cin.magnitude < 0:
                skew.shade_cin(p, T, prof, alpha=0.2)
                
        # Marcadores dos Níveis
        if lcl_p is not None: skew.plot(lcl_p, lcl_t, 'ko', label='LCL')
        if lfc_p is not None: skew.plot(lfc_p, lfc_t, 'bo', label='LFC')
        if el_p is not None: skew.plot(el_p, el_t, 'ro', label='EL')
            
    except: pass

    # Barbelas de Vento (Reduz densidade para não poluir)
    try:
        # Plota a cada 50 hPa para ficar limpo
        mask = (p.m % 50 == 0)
        if np.any(mask):
            skew.plot_barbs(p[mask], u[mask], v[mask])
        else:
            # Fallback se a grade não casar com 50
            skew.plot_barbs(p[::5], u[::5], v[::5])
    except: pass

    # Decoração
    skew.plot_dry_adiabats(alpha=0.3)
    skew.plot_moist_adiabats(alpha=0.3)
    skew.plot_mixing_lines(linestyle='dotted', alpha=0.4)
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    
    # Título Seguro
    real_date = df.attrs.get('real_date', date)
    d_str = real_date if isinstance(real_date, str) else real_date.strftime('%d/%m/%Y')
    src = df.attrs.get('source', 'ERA5/GFS')
    
    plt.title(f"Skew-T | {d_str} {hour}:00 UTC\n{lat:.2f}, {lon:.2f} | {src}", loc='left')
    skew.ax.legend(loc='upper right')

    st.pyplot(fig)
    
    # Download
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    st.download_button("📷 Baixar Gráfico", buf.getvalue(), "skewt.png", "image/png")
