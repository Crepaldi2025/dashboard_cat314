# ==================================================================================
# charts_visualizer.py
# ==================================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import io
import re

def _create_chart_figure(df: pd.DataFrame, variable: str, unit: str):
    
    variable_name = variable.split(" (")[0]
    
    fig = px.line(
        df,
        x='date',
        y='value',
        title=None, 
        labels={
            "date": "Data",
            "value": f"{variable_name} ({unit})"
        },
        markers=True
    )

    fig.update_layout(
        xaxis=dict(
            showline=True, linecolor='black', linewidth=1, ticks='outside', ticklen=6, tickcolor='black',
            showgrid=True, gridcolor='#E5E5E5', mirror=True,
            showspikes=True, spikemode='across', spikesnap='cursor', spikethickness=1, spikecolor='#555555', spikedash='solid',
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1a", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ]),
                bgcolor="white", bordercolor="#cccccc", borderwidth=1, x=0, y=1.1
            )
        ),
        yaxis=dict(
            showline=True, linecolor='black', linewidth=1, ticks='outside', ticklen=6, tickcolor='black',
            showgrid=True, gridcolor='#E5E5E5', mirror=True, zeroline=False,
            showspikes=True, spikemode='across', spikethickness=1, spikecolor='#555555', spikedash='solid'
        ),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", size=14, color="black"),
        hovermode="x"
    )
    
    fig.update_traces(
        line=dict(width=2.5, color='#1f77b4'), 
        marker=dict(size=7, symbol='circle', line=dict(width=1, color='white')),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Valor:</b> %{y:.2f} " + f"{unit}"
    )

    return fig

def _convert_df_to_excel(df: pd.DataFrame) -> bytes:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return excel_buffer.getvalue()

def display_time_series_chart(df: pd.DataFrame, variable: str, unit: str, show_help: bool = True):
    st.markdown("""<style>div[data-testid="stMetricValue"] { font-size: 1.1rem; }</style>""", unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.warning("Nenhum dado válido encontrado.")
        return

    df_clean = df.copy()

    if 'date' not in df_clean.columns:
        if 'system:time_start' in df_clean.columns: df_clean.rename(columns={'system:time_start': 'date'}, inplace=True)
        elif pd.api.types.is_datetime64_any_dtype(df_clean.iloc[:, 0]): df_clean.rename(columns={df_clean.columns[0]: 'date'}, inplace=True)
        else: return

    if 'value' not in df_clean.columns:
         if len(df_clean.columns) > 1 and pd.api.types.is_numeric_dtype(df_clean.iloc[:, 1]):
             df_clean.rename(columns={df_clean.columns[1]: 'value'}, inplace=True)
         else: return

    df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')
    df_clean = df_clean.dropna(subset=['date', 'value']).sort_values('date')

    # 1. Gráfico
    try:
        fig = _create_chart_figure(df_clean, variable, unit)
        fig.update_layout(margin=dict(t=40, l=60, r=30, b=60))
        st.plotly_chart(fig, use_container_width=True)
        
        data_ini = df_clean['date'].min().strftime('%d/%m/%Y')
        data_fim = df_clean['date'].max().strftime('%d/%m/%Y')
        fig.update_layout(title=dict(text=f"<b>Série Temporal de {variable}</b><br><sup>({data_ini} a {data_fim})</sup>", font=dict(size=24), x=0, y=0.95))
        
    except Exception as e:
        st.error(f"Erro ao plotar gráfico: {e}")
        return

    # 2. Download Imagem
    # --- CORREÇÃO AQUI: Gera um ID único usando o nome completo da variável ---
    # Removemos caracteres especiais, mas mantemos números e distinções
    variable_clean = re.sub(r'[^a-zA-Z0-9]', '_', variable).lower()
    
    col_img1, col_img2, _ = st.columns([1, 1, 2])
    
    try:
        img_png = fig.to_image(format="png", width=1200, height=800, scale=2)
        img_jpg = fig.to_image(format="jpeg", width=1200, height=800, scale=2)
        
        with col_img1: 
            st.download_button(
                "📷 Baixar Gráfico (PNG)", 
                data=img_png, 
                file_name=f"grafico_{variable_clean}.png", 
                mime="image/png", 
                use_container_width=True, 
                key=f"btn_png_{variable_clean}"
            )
        
        with col_img2: 
            st.download_button(
                "📷 Baixar Gráfico (JPG)", 
                data=img_jpg, 
                file_name=f"grafico_{variable_clean}.jpg", 
                mime="image/jpeg", 
                use_container_width=True, 
                key=f"btn_jpg_{variable_clean}"
            )
            
    except (ValueError, RuntimeError):
        with col_img1: st.warning("⚠️ Erro no servidor de imagem.")

    # 3. Ajuda
    if show_help:
        pass 

    # 4. Estatísticas
    st.markdown("#### Estatísticas do Período")
    media, maximo, minimo = df_clean['value'].mean(), df_clean['value'].max(), df_clean['value'].min()
    amplitude, desvio = maximo - minimo, df_clean['value'].std()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Média", f"{media:.1f} {unit}")
    c2.metric("Máxima", f"{maximo:.1f} {unit}")
    c3.metric("Mínima", f"{minimo:.1f} {unit}")
    c4.metric("Amplitude", f"{amplitude:.1f} {unit}", help="Diferença entre Máximo e Mínimo.")
    c5.metric("Desvio Padrão", f"{desvio:.1f}", help="Dispersão dos dados em relação à média.")
    
    # 5. Tabela
    st.markdown("---")
    
    variable_label = variable.split(" (")[0]
    col_name_display = f"{variable_label} ({unit})"
    
    df_export = df_clean.rename(columns={'date': 'Data', 'value': col_name_display})
    
    if pd.api.types.is_datetime64tz_dtype(df_export['Data']):
        df_export['Data'] = df_export['Data'].dt.tz_localize(None)
    
    with st.expander("📄 Ver Tabela de Dados", expanded=False):
        st.dataframe(
            df_export,
            use_container_width=True,
            height=300,
            hide_index=True,
            column_config={
                "Data": st.column_config.DateColumn("Data da Leitura", format="DD/MM/YYYY", width="medium"),
                col_name_display: st.column_config.NumberColumn(col_name_display, format="%.2f " + unit, width="medium")
            }
        )

    # Botões de exportação
    csv_data = df_export.to_csv(index=False, encoding='utf-8-sig', date_format='%d/%m/%Y')
    try: excel_data = _convert_df_to_excel(df_export)
    except: excel_data = None
    
    cex1, cex2 = st.columns(2)
    
    with cex1: 
        st.download_button(
            "💾 Exportar CSV", 
            data=csv_data, 
            file_name=f"serie_{variable_clean}.csv", 
            mime="text/csv", 
            use_container_width=True, 
            key=f"btn_csv_{variable_clean}"
        )
        
    with cex2: 
        if excel_data: 
            st.download_button(
                "💾 Exportar Excel", 
                data=excel_data, 
                file_name=f"serie_{variable_clean}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True, 
                key=f"btn_xlsx_{variable_clean}"
            )

def display_multiaxis_chart(data_dict):
    """
    Gera um único gráfico com múltiplos eixos Y para comparar variáveis.
    data_dict: Dicionário contendo os resultados das séries {nome_var: {df, var_cfg}}
    """
    if not data_dict:
        return

    fig = go.Figure()
    
    colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e'] 
    
    layout_settings = {
        'xaxis': dict(domain=[0.1, 0.9] if len(data_dict) > 2 else [0, 1]),
        'yaxis': dict(title="Eixo 1", titlefont=dict(color=colors[0]), tickfont=dict(color=colors[0])),
        'yaxis2': dict(title="Eixo 2", titlefont=dict(color=colors[1]), tickfont=dict(color=colors[1]), anchor="x", overlaying="y", side="right"),
        'yaxis3': dict(title="Eixo 3", titlefont=dict(color=colors[2]), tickfont=dict(color=colors[2]), anchor="free", overlaying="y", side="right", position=0.95),
        'yaxis4': dict(title="Eixo 4", titlefont=dict(color=colors[3]), tickfont=dict(color=colors[3]), anchor="free", overlaying="y", side="left", position=0.05)
    }

    idx = 0
    for var_name, res in data_dict.items():
        if idx >= 4: break 
        
        df = res["time_series_df"]
        unit = res["var_cfg"]["unit"]
        
        if 'date' not in df.columns: continue
        
        yaxis_name = f"y{idx+1}" if idx > 0 else "y"
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['value'],
            name=f"{var_name} ({unit})",
            yaxis=yaxis_name,
            line=dict(color=colors[idx], width=2.5),
            mode='lines+markers'
        ))
        
        key = f"yaxis{idx+1}" if idx > 0 else "yaxis"
        layout_settings[key]['title'] = f"{var_name} ({unit})"
        
        idx += 1

    layout_settings['xaxis'].update(dict(title="Data", showgrid=True))

    fig.update_layout(
        title="Comparação Multi-Eixos",
        legend=dict(x=0.5, y=1.1, orientation="h", xanchor="center"),
        height=600,
        margin=dict(l=20, r=20, t=60, b=20),
        **layout_settings
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 **Dica:** Dê dois cliques na legenda de uma variável para isolá-la.")
