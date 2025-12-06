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
        p = df['pressure'].values * units.hPa
        T = df['temperature'].values * units.degC
        rh = df['relative_humidity'].values / 100.0
        
        # Componentes do vento
        u = (df['u_component'].values * units('m/s')).to('knots')
        v = (df['v_component'].values * units('m/s')).to('knots')

        # Calcula Ponto de Orvalho
        Td = mpcalc.dewpoint_from_relative_humidity(T, rh)
    except Exception as e:
        st.error(f"Erro nos dados físicos: {e}")
        return

    # --- 2. CÁLCULOS TERMODINÂMICOS AVANÇADOS ---
    # Inicializa variáveis com None
    cape, cin = None, None
    lcl_p, lfc_p, el_p = None, None, None
    li, k_idx, pw = None, None, None

    try:
        # Perfil da Parcela (Surface Based)
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        
        # CAPE e CIN
        cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
        
        # Níveis Significativos (LCL, LFC, EL)
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        lfc_p, lfc_t = mpcalc.lfc(p, T, Td)
        el_p, el_t = mpcalc.el(p, T, Td)

        # Índices de Instabilidade
        li = mpcalc.lifted_index(p, T, prof)[0] # Lifted Index
        
        # K-Index (Requer níveis específicos)
        try: k_idx = mpcalc.k_index(p, T, Td)
        except: pass

        # Água Precipitável
        pw = mpcalc.precipitable_water(p, Td)

    except Exception as e:
        # print(f"Aviso Calc: {e}") # Debug silencioso
        pass

    # --- 3. EXIBIÇÃO DAS MÉTRICAS (CAIXA DESTACADA) ---
    st.markdown("### 📊 Índices Termodinâmicos")
    
    with st.container(border=True):
        # Linha 1: Energias e Níveis
        c1, c2, c3, c4 = st.columns(4)
        
        # Correção do ValueError: Usar 'is not None' em vez de check booleano direto
        cape_val = f"{cape.magnitude:.0f} J/kg" if cape is not None else "--"
        c1.metric("CAPE", cape_val, 
            help="Convective Available Potential Energy.\nEnergia potencial disponível para que a parcela suba livremente. Valores elevados indicam ambiente mais instável.")
        
        cin_val = f"{cin.magnitude:.0f} J/kg" if cin is not None else "--"
        c2.metric("CIN", cin_val, 
            help="Convective Inhibition.\nEnergia que inibe o disparo da convecção.\nQuanto maior, mais difícil iniciar a tempestade.")
        
        lcl_val = f"{lcl_p.magnitude:.0f} hPa" if lcl_p is not None else "--"
        c3.metric("LCL", lcl_val, 
            help="Lifted Condensation Level.\nNível em que a parcela em ascensão se torna saturada, aproximando a altura da base das nuvens.")
        
        lfc_val = f"{lfc_p.magnitude:.0f} hPa" if lfc_p is not None else "--"
        c4.metric("LFC", lfc_val, 
            help="Level of Free Convection.\nNível a partir do qual a parcela fica mais quente que o ambiente e passa a subir espontaneamente.")

        # Linha 2: Índices de Estabilidade e Umidade
        c5, c6, c7, c8 = st.columns(4)
        
        li_val = f"{li.magnitude:.1f}" if li is not None else "--"
        c5.metric("LI", li_val, 
            help="Diferença de temperatura (Ambiente - Parcela) em 500hPa.\nValores muito negativos indicam forte instabilidade.")
        
        k_val = f"{k_idx.magnitude:.0f}" if k_idx is not None else "--"
        c6.metric("K-Index", k_val, 
            help="Índice que combina temperatura e umidade em 850–500 hPa para estimar potencial de convecção úmida e trovoadas.")
        
        pw_val = f"{pw.magnitude:.1f} mm" if pw is not None else "--"
        c7.metric("Água Precipitável", pw_val, 
            help="Quantidade total de vapor de água na coluna que poderia precipitar se toda a umidade se condensasse.\nIndica potencial para chuvas volumosas.")
        
        el_val = f"{el_p.magnitude:.0f} hPa" if el_p is not None else "--"
        c8.metric("EL", el_val, 
            help="Equilibrium Level.\nNível em que a temperatura da parcela volta a igualar a do ambiente, limitando a altura da convecção..")

    # --- TABELA DE REFERÊNCIA (NOVA) ---
    
    with st.expander("📚 Tabela de Referência: Limiares de Severidade", expanded=False):
        st.markdown("""
        | Índice | Estável / Fraco | Moderado | Forte / Severo | Descrição Rápida |
        | :--- | :---: | :---: | :---: | :--- |
        | **CAPE** (J/kg) | < 1000 | 1000 a 2500 | > 2500 | Combustível para a tempestade. |
        | **CIN** (J/kg) | 0 a -50 | -50 a -200 | < -200 | "Tampa" que impede a subida do ar. |
        | **Lifted (LI)** | > 0 | -3 a 0 | < -6 | Instabilidade (T_amb - T_parcela). |
        | **K-Index** | < 20 | 26 a 35 | > 35 | Potencial para trovoadas/chuva. |
        | **Total Totals** | < 45 | 45 a 55 | > 55 | Severidade geral da tempestade. |
        | **Água Prec.** (mm) | < 25 | 25 a 45 | > 50 | Umidade disponível na coluna. |
        """)
        
        st.caption("⚠️ **Nota:** Estes valores são referências gerais. Em regiões tropicais (como a Amazônia), valores de CAPE e Água Precipitável costumam ser naturalmente mais altos sem necessariamente indicar tempestades severas.")

    # --- 4. PLOTAGEM DO GRÁFICO ---
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)

    # Linhas principais
    skew.plot(p, T, 'r', linewidth=2, label='Temperatura')
    skew.plot(p, Td, 'g', linewidth=2, label='Ponto de Orvalho')

    # Perfil da Parcela (Tracejado preto)
    try:
        # Só plota se tiver calculado o perfil
        if 'prof' in locals() and prof is not None:
            skew.plot(p, prof, 'k', linewidth=1.5, linestyle='--', label='Parcela')
            
            # Áreas sombreadas (CAPE/CIN)
            if cape is not None and cape.magnitude > 0:
                skew.shade_cape(p, T, prof, alpha=0.2)
            if cin is not None and cin.magnitude < 0: # CIN é negativo no MetPy às vezes, ou positivo dependendo da versão
                skew.shade_cin(p, T, prof, alpha=0.2)

        # Pontos importantes
        if lcl_p is not None: skew.plot(lcl_p, lcl_t, 'ko', markerfacecolor='black', label='LCL')
        if lfc_p is not None: skew.plot(lfc_p, lfc_t, 'bo', markerfacecolor='blue', label='LFC')
        if el_p is not None: skew.plot(el_p, el_t, 'ro', markerfacecolor='red', label='EL')
    except Exception as e:
        # print(f"Erro plotagem extra: {e}")
        pass

    # Barbelas de Vento (Simplificadas)
    try:
        mask = p.m % 50 == 0 
        if not any(mask): mask = slice(None, None, 2)
        skew.plot_barbs(p[mask], u[mask], v[mask])
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
    
    # Formatação segura da data
    if isinstance(real_date, (str)): date_str = real_date
    else: date_str = real_date.strftime('%d/%m/%Y')
    
    title_txt = (
        f"Skew-T Log-P | {date_str} {hour}:00 UTC\n"
        f"Local: {lat:.4f}, {lon:.4f} | Fonte: {src}"
    )
    plt.title(title_txt, loc='left', fontsize=10)
    skew.ax.legend(loc='upper right')

    st.pyplot(fig)
    
    # Download
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    st.download_button("📷 Baixar Gráfico (PNG)", buf.getvalue(), "skewt.png", "image/png")






