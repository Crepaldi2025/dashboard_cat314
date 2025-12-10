# ==================================================================================
# skewt_visualizer.py (COM CÁLCULO DE ALTA RESOLUÇÃO)
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

    # --- 1. PREPARAÇÃO DOS DADOS (Unidades MetPy) ---
    try:
        # Dados originais (podem ter baixa resolução vertical)
        p_raw = df['pressure'].values * units.hPa
        T_raw = df['temperature'].values * units.degC
        rh_raw = df['relative_humidity'].values / 100.0
        
        # Componentes do vento (originais)
        u_raw = (df['u_component'].values * units('m/s')).to('knots')
        v_raw = (df['v_component'].values * units('m/s')).to('knots')

        # Calcula Td original
        Td_raw = mpcalc.dewpoint_from_relative_humidity(T_raw, rh_raw)

        # --- 1.1 INTERPOLAÇÃO DE ALTA RESOLUÇÃO (A CORREÇÃO) ---
        # Cria uma malha fina de 5 em 5 hPa para capturar o LFC exato (ex: 870hPa)
        # O np.interp precisa dos dados ordenados (crescente), por isso usamos [::-1]
        
        # Define novo eixo de pressão (do chão até o topo)
        max_p = int(p_raw.max().m)
        min_p = int(p_raw.min().m)
        p_dense = np.arange(max_p, min_p, -5) * units.hPa
        
        # Interpola Temperatura e Ponto de Orvalho
        # Nota: p_raw geralmente vem decrescente (1000->100), np.interp quer xp crescente
        T_dense = np.interp(p_dense.m, p_raw.m[::-1], T_raw.m[::-1]) * units.degC
        Td_dense = np.interp(p_dense.m, p_raw.m[::-1], Td_raw.m[::-1]) * units.degC
        
        # Usamos as variáveis _dense para CÁLCULOS (precisão)
        # Usamos as variáveis _raw para PLOTAR VENTO (para não poluir o gráfico com mil setas)
        
        p, T, Td = p_dense, T_dense, Td_dense

    except Exception as e:
        st.error(f"Erro nos dados físicos: {e}")
        return

    # --- 2. CÁLCULOS TERMODINÂMICOS AVANÇADOS ---
    # Inicializa variáveis com None
    cape, cin = None, None
    lcl_p, lfc_p, el_p = None, None, None
    li, k_idx, pw = None, None, None

    try:
        # Perfil da Parcela (Surface Based usando dados densos)
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        
        # CAPE e CIN
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        
        # Níveis Significativos (LCL, LFC, EL)
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        lfc_p, lfc_t = mpcalc.lfc(p, T, Td)
        el_p, el_t = mpcalc.el(p, T, Td)

        # Índices de Instabilidade
        li = mpcalc.lifted_index(p, T, prof)[0] # Lifted Index
        
        # K-Index (Usa dados originais para garantir níveis padrão 850/700/500 se existirem)
        try: k_idx = mpcalc.k_index(p_raw, T_raw, Td_raw)
        except: pass

        # Água Precipitável
        pw = mpcalc.precipitable_water(p, Td)

    except Exception as e:
        # print(f"Aviso Calc: {e}") 
        pass

    # --- 3. EXIBIÇÃO DAS MÉTRICAS ---
    st.markdown("### 📊 Índices Termodinâmicos")
    
    with st.container(border=True):
        # Linha 1: Energias e Níveis
        c1, c2, c3, c4 = st.columns(4)
        
        cape_val = f"{cape.magnitude:.0f} J/kg" if cape is not None else "--"
        c1.metric("CAPE", cape_val, 
            help="Convective Available Potential Energy.\nEnergia potencial disponível para tempestades.")
        
        cin_val = f"{cin.magnitude:.0f} J/kg" if cin is not None else "--"
        c2.metric("CIN", cin_val, 
            help="Convective Inhibition.\nEnergia que inibe o disparo da convecção.")
        
        lcl_val = f"{lcl_p.magnitude:.0f} hPa" if lcl_p is not None else "--"
        c3.metric("LCL", lcl_val, 
            help="Lifted Condensation Level.\nBase das nuvens.")
        
        lfc_val = f"{lfc_p.magnitude:.0f} hPa" if lfc_p is not None else "--"
        c4.metric("LFC", lfc_val, 
            help="Level of Free Convection.\nNível onde a parcela sobe livremente. Agora com cálculo de alta precisão.")

        # Linha 2: Índices de Estabilidade e Umidade
        c5, c6, c7, c8 = st.columns(4)
        
        li_val = f"{li.magnitude:.1f}" if li is not None else "--"
        c5.metric("LI", li_val, help="Lifted Index.")
        
        k_val = f"{k_idx.magnitude:.0f}" if k_idx is not None else "--"
        c6.metric("K-Index", k_val, help="Potencial de trovoadas.")
        
        pw_val = f"{pw.magnitude:.1f} mm" if pw is not None else "--"
        c7.metric("Água Precipitável", pw_val, help="Umidade total na coluna.")
        
        el_val = f"{el_p.magnitude:.0f} hPa" if el_p is not None else "--"
        c8.metric("EL", el_val, help="Nível de Equilíbrio (Topo da nuvem).")

    # --- TABELA DE REFERÊNCIA ---
    with st.expander("📚 Tabela de Referência: Limiares de Severidade", expanded=False):
        st.markdown("""
        | Índice | Estável / Fraco | Moderado | Forte / Severo |
        | :--- | :---: | :---: | :---: |
        | **CAPE** (J/kg) | < 1000 | 1000 a 2500 | > 2500 |
        | **CIN** (J/kg) | 0 a -50 | -50 a -200 | < -200 |
        | **LI** | > 0 | -3 a 0 | < -6 |
        """)
        
    # --- 4. PLOTAGEM DO GRÁFICO ---
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    # Plota curvas usando DADOS DENSOS (Curva suave)
    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')

    # Perfil da Parcela
    try:
        if 'prof' in locals() and prof is not None:
            skew.plot(p, prof, 'k', linewidth=1.5, linestyle='--', label='Parcela')
            
            # Áreas sombreadas (CAPE/CIN)
            if cape is not None and cape.magnitude > 0:
                skew.shade_cape(p, T, prof, alpha=0.2)
            if cin is not None and cin.magnitude < 0:
                skew.shade_cin(p, T, prof, alpha=0.2)

        # Pontos importantes
        if lcl_p is not None: skew.plot(lcl_p, lcl_t, 'ko', markerfacecolor='black', label='LCL')
        if lfc_p is not None: skew.plot(lfc_p, lfc_t, 'bo', markerfacecolor='blue', label='LFC')
        if el_p is not None: skew.plot(el_p, el_t, 'ro', markerfacecolor='red', label='EL')
    except Exception as e: pass

    # Barbelas de Vento (Usando dados ORIGINAIS para não poluir)
    try:
        # Pula níveis para não ficar amontoado (ex: a cada 50hPa)
        mask = p_raw.m % 50 == 0 
        if not any(mask): mask = slice(None, None, 2)
        skew.plot_barbs(p_raw[mask], u_raw[mask], v_raw[mask])
    except: pass

    # Linhas de fundo
    skew.plot_dry_adiabats(alpha=0.3)
    skew.plot_moist_adiabats(alpha=0.3)
    skew.plot_mixing_lines(linestyle='dotted', alpha=0.4)

    # Limites e Título
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 50)
    
    real_date = df.attrs.get('real_date', date)
    src = df.attrs.get('source', '')
    if isinstance(real_date, (str)): date_str = real_date
    else: date_str = real_date.strftime('%d/%m/%Y')
    
    title_txt = f"Skew-T Log-P | {date_str} {hour}:00 UTC\nLocal: {lat:.4f}, {lon:.4f} | Fonte: {src}"
    plt.title(title_txt, loc='left', fontsize=10)
    skew.ax.legend(loc='upper right')

    st.pyplot(fig)
    
    # Download
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    st.download_button("📷 Baixar Gráfico (PNG)", buf.getvalue(), "skewt.png", "image/png", use_container_width=True)
