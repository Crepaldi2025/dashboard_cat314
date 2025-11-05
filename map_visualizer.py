# ==================================================================================
# map_visualizer.py — Funções de visualização do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
from streamlit_folium import st_folium


# ==================================================================================
# MAPA INTERATIVO — ESTADO
# ==================================================================================
def display_state_map(geometry, variavel, vis_params, titulo="Mapa Interativo"):
    """Exibe o mapa interativo com fundo de satélite e colorbar discreto."""
    st.subheader(titulo)

    mapa = geemap.Map(center=[-15.78, -47.93], zoom=5)
    mapa.add_basemap("SATELLITE")

    # Adiciona camada do Earth Engine
    layer = geemap.ee_tile_layer(geometry, vis_params, variavel)
    mapa.add_layer(layer)

    # Adiciona colorbar discreto e coerente
    _add_colorbar_discreto(mapa, vis_params, variavel)

    st_folium(mapa, width=900, height=500)
    st.success("Mapa interativo exibido com sucesso.")


# ==================================================================================
# MAPA INTERATIVO — CÍRCULO
# ==================================================================================
def display_circle_map(latitude, longitude, radius_km, variavel, vis_params):
    """Exibe um mapa interativo de conferência com círculo delimitador."""
    st.subheader("Mapa de Conferência (Círculo)")

    mapa = geemap.Map(center=[latitude, longitude], zoom=7)
    mapa.add_basemap("SATELLITE")

    # Círculo de referência
    circle = folium.Circle(
        location=[latitude, longitude],
        radius=radius_km * 1000,
        color="red",
        fill=False,
    )
    mapa.add_child(circle)

    # Adiciona camada e colorbar
    layer = geemap.ee_tile_layer(ee.Image().paint(circle), vis_params, variavel)
    mapa.add_layer(layer)

    _add_colorbar_discreto(mapa, vis_params, variavel)
    st_folium(mapa, width=900, height=500)


# ==================================================================================
# MAPA INTERATIVO — COMPATÍVEL COM main.py
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unidade):
    """Compatível com main.py — mapa interativo sem duplicação de colorbar."""
    st.subheader("Resultado da Análise")

    mapa = geemap.Map(center=[-15, -55], zoom=5)
    mapa.add_basemap("SATELLITE")

    # Adiciona camada sem gerar colorbar automática
    tile_layer = geemap.ee_tile_layer(ee_image, vis_params, "Resultado", shown=True, opacity=1.0)
    mapa.add_child(tile_layer)

    # Adiciona colorbar discreto (canto inferior esquerdo)
    _add_colorbar_discreto(mapa, vis_params, unidade)

    st_folium(mapa, width=900, height=500)


# ==================================================================================
# FUNÇÃO INTERNA — COLORBAR DISCRETO
# ==================================================================================
def _add_colorbar_discreto(mapa, vis_params, unidade):
    """Adiciona colorbar discreto e contrastante no canto inferior esquerdo."""
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)

    # Define rótulo
    if "°" in unidade or "temp" in unidade.lower():
        label = "Temperatura (°C)"
    elif "mm" in unidade.lower():
        label = "Precipitação (mm)"
    elif "m/s" in unidade.lower() or "vento" in unidade.lower():
        label = "Vento (m/s)"
    else:
        label = str(unidade) if unidade else ""

    # Adiciona colorbar usando o método nativo do geemap (mantém contraste e posição)
    if palette:
        mapa.add_colorbar(
            colors=palette,
            vmin=vmin,
            vmax=vmax,
            caption=label,
            position="bottomleft"
        )
