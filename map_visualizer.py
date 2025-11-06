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

    circle = folium.Circle(
        location=[latitude, longitude],
        radius=radius_km * 1000,
        color="red",
        fill=False,
    )
    mapa.add_child(circle)

    layer = geemap.ee_tile_layer(ee.Image().paint(circle), vis_params, variavel)
    mapa.add_layer(layer)

    _add_colorbar_discreto(mapa, vis_params, variavel)
    st_folium(mapa, width=900, height=500)


# ==================================================================================
# MAPA INTERATIVO — COMPATÍVEL COM main.py
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Exibe o mapa interativo com colorbar discreta no canto inferior esquerdo."""
    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()  # (lon, lat) -> (lat, lon)

    mapa = geemap.Map(center=centroid, zoom=7)

    # Adiciona fundo satélite manualmente (garantido)
    basemap = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
        name="Esri Satellite",
        overlay=False,
        control=False,
    )
    basemap.add_to(mapa)

    # Camadas do EE
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {"palette": "black"}, "Contorno da Área")

    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    mapa.to_streamlit(height=500)


# ==================================================================================
# MAPA ESTÁTICO — COMPATÍVEL COM main.py
# ==================================================================================
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera uma imagem estática (PNG e JPG) a partir dos dados do Earth Engine."""
    import matplotlib.pyplot as plt
    import numpy as np
    import io
    import base64
    from PIL import Image
    import requests

    # Gera thumbnail da imagem EE
    url = ee_image.getThumbURL({
        'region': feature.geometry(),
        'min': vis_params.get('min', 0),
        'max': vis_params.get('max', 1),
        'palette': vis_params.get('palette', ['blue', 'green', 'red']),
        'dimensions': 600
    })

    try:
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
    except Exception:
        st.error("Falha ao gerar mapa estático.")
        return None, None, None

    # Converte para PNG e JPG (em memória)
    png_buffer = io.BytesIO()
    jpg_buffer = io.BytesIO()
    image.save(png_buffer, format="PNG")
    image.save(jpg_buffer, format="JPEG")

    # Codifica em base64
    png_base64 = base64.b64encode(png_buffer.getvalue()).decode("utf-8")
    jpg_base64 = base64.b64encode(jpg_buffer.getvalue()).decode("utf-8")

    # Exibe no Streamlit
    st.image(image, caption=f"Mapa Estático — {unit_label}", use_column_width=True)

    # Cria colorbar
    fig, ax = plt.subplots(figsize=(5, 0.4))
    cmap = plt.cm.get_cmap('RdYlBu_r')
    if 'mm' in unit_label.lower():
        cmap = plt.cm.get_cmap('turbo')
    elif '°' in unit_label or 'temp' in unit_label.lower():
        cmap = plt.cm.get_cmap('RdYlBu_r')
    elif 'm/s' in unit_label.lower():
        cmap = plt.cm.get_cmap('viridis')

    cb = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), cax=ax, orientation='horizontal')
    cb.set_label(unit_label)
    plt.tight_layout()

    colorbar_buf = io.BytesIO()
    plt.savefig(colorbar_buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)

    # Retorna objetos compatíveis
    return png_base64, jpg_base64, colorbar_buf


# ==================================================================================
# FUNÇÃO INTERNA — COLORBAR DISCRETO
# ==================================================================================
def _add_colorbar_discreto(mapa, vis_params, unidade):
    from branca.colormap import LinearColormap

    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)

    if not palette:
        return

    if "°" in unidade or "temp" in unidade.lower():
        label = "Temperatura (°C)"
    elif "mm" in unidade.lower():
        label = "Precipitação (mm)"
    elif "m/s" in unidade.lower() or "vento" in unidade.lower():
        label = "Vento (m/s)"
    else:
        label = str(unidade) if unidade else ""

    colormap = LinearColormap(colors=palette, vmin=vmin, vmax=vmax)
    colormap.caption = label
    mapa.add_child(colormap)


# ==================================================================================
# FUNÇÃO INTERNA — COLORBAR FIXA
# ==================================================================================
def _add_colorbar_bottomleft(mapa, vis_params, unit_label):
    from branca.colormap import LinearColormap
    from branca.element import Template, MacroElement

    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette:
        return

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
