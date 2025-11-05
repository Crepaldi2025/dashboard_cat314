# ==================================================================================
# map_visualizer.py — Clima-Cast-Crepaldi (versão estável restaurada)
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import io
from streamlit_folium import st_folium
from PIL import Image
import requests

# ==================================================================================
# MAPA: CÍRCULO
# ==================================================================================
def display_circle_map(latitude, longitude, radius_km):
    """Exibe um mapa interativo com o círculo de interesse."""
    st.subheader("🗺️ Mapa de Confirmação da Área de Interesse")

    m = geemap.Map(center=(latitude, longitude), zoom=7)
    folium.Circle(
        location=(latitude, longitude),
        radius=radius_km * 1000,
        color="blue",
        fill=True,
        fill_opacity=0.2,
        tooltip=f"Centro: ({latitude:.2f}, {longitude:.2f}) | Raio: {radius_km} km"
    ).add_to(m)
    m.add_basemap("SATELLITE")
    st_folium(m, width=700, height=500)

# ==================================================================================
# MAPA: POLÍGONO DESENHADO
# ==================================================================================
def display_polygon_draw_map():
    """Permite desenhar um polígono no mapa interativo."""
    st.subheader("✏️ Desenhe a área de interesse")
    m = geemap.Map(center=[-15, -55], zoom=4)
    m.add_basemap("SATELLITE")
    m.add_draw_control(
        draw_options={"polygon": True, "rectangle": True, "circle": False, "marker": False},
        edit=False
    )
    output = st_folium(m, height=500, width=700)
    if output and "last_draw" in output and output["last_draw"] is not None:
        st.session_state.drawn_geometry = output["last_draw"]["geometry"]
        st.success("✅ Polígono capturado! Clique em 'Validar Área' para continuar.")
    else:
        st.info("Desenhe o polígono no mapa e confirme.")

# ==================================================================================
# MAPA INTERATIVO (ERA5-LAND)
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Gera e exibe um mapa interativo compatível com Streamlit Cloud."""
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return

    centroid = feature.geometry().centroid(maxError=1).getInfo()["coordinates"]
    centroid.reverse()
    m = geemap.Map(center=centroid, zoom=6)
    m.add_basemap("SATELLITE")

    try:
        layer = geemap.ee_tile_layer(ee_image, vis_params, name="Dados Climáticos")
        m.add_child(layer)
        m.addLayer(ee.Image().paint(feature, 0, 2),
                   {"palette": "black"}, "Contorno da Área")

        # Adiciona legenda
        cmap = LinearSegmentedColormap.from_list("custom", vis_params["palette"])
        fig, ax = plt.subplots(figsize=(4, 0.3))
        cb = plt.colorbar(
            plt.cm.ScalarMappable(norm=plt.Normalize(vmin=vis_params["min"], vmax=vis_params["max"]),
                                  cmap=cmap),
            cax=ax,
            orientation="horizontal"
        )
        cb.set_label(unit_label, fontsize=8)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        st.image(buf, caption="Legenda", use_container_width=False)

        st_folium(m, width=700, height=500)

    except Exception as e:
        st.error(f"⚠️ Falha ao adicionar camada do GEE: {e}")

# ==================================================================================
# MAPA ESTÁTICO (ERA5-LAND)
# ==================================================================================
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera e retorna URLs de imagens (PNG e JPEG) de alta qualidade."""
    try:
        region = feature.geometry().bounds().getInfo()["coordinates"]
        image_rgb = ee_image.visualize(**vis_params)
        url_png = image_rgb.getThumbURL({
            "region": region,
            "dimensions": 2048,
            "format": "png",
            "crs": "EPSG:4326"
        })
        url_jpg = image_rgb.getThumbURL({
            "region": region,
            "dimensions": 2048,
            "format": "jpg",
            "crs": "EPSG:4326"
        })

        # Cria colorbar (separada)
        cmap = LinearSegmentedColormap.from_list("custom", vis_params["palette"])
        fig, ax = plt.subplots(figsize=(4, 0.3))
        cb = plt.colorbar(
            plt.cm.ScalarMappable(norm=plt.Normalize(vmin=vis_params["min"], vmax=vis_params["max"]),
                                  cmap=cmap),
            cax=ax,
            orientation="horizontal"
        )
        cb.set_label(unit_label, fontsize=8)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        buf.seek(0)

        colorbar_img = buf.getvalue()
        return url_png, url_jpg, colorbar_img

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa estático: {e}")
        return None, None, None
