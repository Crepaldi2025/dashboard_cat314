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
    mapa.add_basemap("Esri.WorldImagery")

    # Adiciona camada do Earth Engine
    layer = geemap.ee_tile_layer(geometry, vis_params, variavel)
    mapa.add_layer(layer)

    # Adiciona colorbar discreto
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
    mapa.add_basemap("Esri.WorldImagery")

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
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Exibe o mapa interativo com fundo de satélite e colorbar discreta."""
    # O título já vem do main.py

    # Centraliza no AOI
    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()  # (lon, lat) -> (lat, lon)

    # Cria mapa com fundo satélite ESRI
    mapa = geemap.Map(center=centroid, zoom=7)
    basemap = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
        name="Esri Satellite",
        overlay=False,
        control=False,
    )
    basemap.add_to(mapa)

    # Adiciona camada do EE (sem gerar colorbar automática)
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    # Contorno do AOI (mantém o traço preto)
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {"palette": "black"}, "Contorno da Área")

    # Colorbar discreta (canto inferior esquerdo)
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    # Render
    mapa.to_streamlit(height=500)



# ==================================================================================
# FUNÇÃO INTERNA — COLORBAR DISCRETO
# ==================================================================================
def _add_colorbar_discreto(mapa, vis_params, unidade):
    """Adiciona colorbar discreto e compatível em qualquer ambiente."""
    from branca.colormap import LinearColormap

    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)

    if not palette:
        return  # sem paleta, não faz nada

    # Rótulo da legenda
    if "°" in unidade or "temp" in unidade.lower():
        label = "Temperatura (°C)"
    elif "mm" in unidade.lower():
        label = "Precipitação (mm)"
    elif "m/s" in unidade.lower() or "vento" in unidade.lower():
        label = "Vento (m/s)"
    else:
        label = str(unidade) if unidade else ""

    # Cria colormap discreto com contraste e legenda
    colormap = LinearColormap(colors=palette, vmin=vmin, vmax=vmax)
    colormap.caption = label

    # Adiciona ao mapa (canto inferior esquerdo)
    mapa.add_child(colormap)


# ==================================================================================
# FUNÇÃO INTERNA — COLORBAR FIXA (CANTO INFERIOR ESQUERDO)
# ==================================================================================
def _add_colorbar_bottomleft(mapa, vis_params, unit_label):
    """Adiciona uma colorbar com branca, posicionada no canto inferior esquerdo (compatível em qualquer versão)."""
    from branca.colormap import LinearColormap
    from branca.element import Template, MacroElement

    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette:
        return

    # Rótulo da legenda
    label = ""
    ul = (unit_label or "").lower()
    if "°" in unit_label or "temp" in ul:
        label = "Temperatura (°C)"
    elif "mm" in ul:
        label = "Precipitação (mm)"
    elif "m/s" in ul or "vento" in ul:
        label = "Vento (m/s)"
    elif unit_label:
        label = str(unit_label)

    colormap = LinearColormap(colors=palette, vmin=vmin, vmax=vmax)
    colormap.caption = label

    # Posiciona a colorbar no canto inferior esquerdo com CSS fixo
    html = colormap._repr_html_()
    template = Template(f"""
    {{% macro html(this, kwargs) %}}
    <div style="position: fixed; bottom: 12px; left: 12px; z-index: 9999; 
                background: rgba(255,255,255,0.85); padding: 8px 10px; 
                border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3);">
        {html}
    </div>
    {{% endmacro %}}
    """)
    macro = MacroElement()
    macro._template = template
    mapa.get_root().add_child(macro)

