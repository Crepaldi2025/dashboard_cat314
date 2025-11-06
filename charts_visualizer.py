# ==================================================================================
# charts_visualizer.py — Gráficos de séries temporais (Clima-Cast-Crepaldi)
# ==================================================================================
import streamlit as st
import plotly.express as px
import pandas as pd

# ==================================================================================
# FUNÇÃO PRINCIPAL
# ==================================================================================
def exibir_grafico_series_temporais(df: pd.DataFrame):
    """
    Exibe a série temporal da variável meteorológica selecionada.
    O DataFrame deve conter colunas 'date' e 'value'.
    """
    if df is None or df.empty:
        st.info("Nenhum dado de série temporal disponível.")
        return

    # === Configuração básica ===
    df = df.sort_values("date")
    media = df["value"].mean()
    minimo = df["value"].min()
    maximo = df["value"].max()

    st.markdown("### 📈 Série Temporal (ERA5-Land)")
    st.caption("Média diária dos valores sobre a área de interesse selecionada.")

    # === Gráfico interativo ===
    fig = px.line(
        df,
        x="date",
        y="value",
        markers=True,
        line_shape="spline",
        title="Variação temporal da variável selecionada",
        labels={"date": "Data", "value": "Valor médio diário"},
    )

    fig.update_traces(line=dict(width=2.2), marker=dict(size=4))
    fig.update_layout(
        template="plotly_white",
        title_x=0.5,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        height=450,
        showlegend=False,
    )

    # === Linha horizontal de média ===
    fig.add_hline(
        y=media,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Média: {media:.2f}",
        annotation_position="bottom right",
    )

    st.plotly_chart(fig, use_container_width=True)

    # === Estatísticas adicionais ===
    col1, col2, col3 = st.columns(3)
    col1.metric("🌡️ Média", f"{media:.2f}")
    col2.metric("📉 Mínimo", f"{minimo:.2f}")
    col3.metric("📈 Máximo", f"{maximo:.2f}")

# ==================================================================================
# === FIM ===
# ==================================================================================
