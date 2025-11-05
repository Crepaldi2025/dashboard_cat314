# ==================================================================================
# map_visualizer.py — Funções de visualização do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
from branca.colormap import linear
from streamlit_folium import st_folium

# ==================================================================================
# MAPA INTERATIVO — ESTADO
# ==================================================================================
def display_state_map(geometry, variavel, vis_params, titulo="Mapa Interativo"):
    """Exibe o mapa interativo com colorbar contrastante no canto inferior esquerdo."""
    st.subheader(titulo)

    # Criação do mapa base
    mapa = geemap.Map(center=[-15.78, -47.93], zoom=5)
    mapa.add_basemap("SATELLITE")

    # Camada de dados do Earth Engine
    layer = geemap.ee_tile_layer(geometry, vis_params, variavel)
    mapa.add_layer(layer)

    # === Colorbar customizado e discreto ===
    if variavel.lower().startswith("temp"):
        cmap = linear.RdYlBu_11.scale(0, 40)
        label = "Temperatura (°C)"
    elif "prec" in variavel.lower():
        cmap = linear.Blues_09.scale(0, 500)
        label = "Precipitação (mm)"
    elif "vento" in variavel.lower():
        cmap = linear.Viridis_09.scale(0, 30)
        label = "Vento (m/s)"
    else:
        cmap = linear.Greys_09.scale(0, 1)
        label = ""

    cmap.caption = label
    cmap.add_to(mapa)
    cmap.position = "bottomleft"

    # Renderização final no Streamlit
    st_folium(mapa, width=900, height=500)
    st.success("Mapa interativo exibido com sucesso.")


# ==================================================================================
# MAPA INTERATIVO — CÍRCULO
# ==================================================================================
def display_circle_map(latitude, longitude, radius_km, variavel, vis_params):
    """Exibe um mapa de conferência interativo com fundo de satélite."""
    st.subheader("Mapa de Conferência (Círculo)")

    mapa = geemap.Map(center=[latitude, longitude], zoom=7)
    mapa.add_basemap("SATELLITE")

    circle = folium.Circle(
        location=[latitude, longitude],
        radius=radius_km * 1000,
        color="red",
        fill=False,
    )
    mapa.add_child(circle)

    # Camada e colorbar conforme variável
    layer = geemap.ee_tile_layer(ee.Image().paint(circle), vis_params, variavel)
    mapa.add_layer(layer)

    if variavel.lower().startswith("temp"):
        cmap = linear.RdYlBu_11.scale(0, 40)
        label = "Temperatura (°C)"
    elif "prec" in variavel.lower():
        cmap = linear.Blues_09.scale(0, 500)
        label = "Precipitação (mm)"
    elif "vento" in variavel.lower():
        cmap = linear.Viridis_09.scale(0, 30)
        label = "Vento (m/s)"
    else:
        cmap = linear.Greys_09.scale(0, 1)
        label = ""

    cmap.caption = label
    cmap.add_to(mapa)
    cmap.position = "bottomleft"

    st_folium(mapa, width=900, height=500)
def create_interactive_map(ee_image, feature, vis_params, unidade):
    """Função compatível com chamadas antigas (mantém fluxo original)."""
    variavel = unidade  # só para compatibilidade, pode usar nome real se desejar
    mapa = geemap.Map(center=[-15, -55], zoom=5)
    mapa.add_basemap("SATELLITE")
    mapa.add_layer(ee_image, vis_params, variavel)

    # Colorbar discreto e coerente com unidade
    from branca.colormap import linear
    if "°" in unidade or "temp" in unidade.lower():
        cmap = linear.RdYlBu_11.scale(0, 40)
        label = "Temperatura (°C)"
    elif "mm" in unidade.lower():
        cmap = linear.Blues_09.scale(0, 500)
        label = "Precipitação (mm)"
    elif "m/s" in unidade.lower():
        cmap = linear.Viridis_09.scale(0, 30)
        label = "Vento (m/s)"
    else:
        cmap = linear.Greys_09.scale(0, 1)
        label = unidade

    cmap.caption = label
    cmap.add_to(mapa)
    cmap.position = "bottomleft"

    st_folium(mapa, width=900, height=500)


