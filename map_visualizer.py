# ==================================================================================
# map_visualizer.py — Funções de visualização do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import matplotlib.pyplot as plt
import io
from streamlit_folium import st_folium
import numpy as np

# ==================================================================================
# FUNÇÃO DE LEGENDA (COLORBAR)
# ==================================================================================
def add_colorbar_to_map(Map, title, palette, vmin, vmax):
    """Adiciona uma colorbar (legenda) personalizada ao mapa."""
    gradient_html = "".join(
        [f"<div style='flex:1;background:{c}'></div>" for c in palette]
    )
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 35px;
        left: 15px;
        z-index:9999;
        background: rgba(255, 255, 255, 0.85);
        padding: 10px;
        border-radius: 10px;
        font-size: 13px;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    ">
        <div style='text-align:center; font-weight:bold; margin-bottom:5px'>{title}</div>
        <div style='display:flex; height:10px; width:160px; border-radius:5px; overflow:hidden'>
            {gradient_html}
        </div>
        <div style='display:flex; justify-content:space-between; font-size:12px;'>
            <span>{vmin:.1f}</span>
            <span>{vmax:.1f}</span>
        </div>
    </div>
    """
    Map.get_root().html.add_child(folium.Element(legend_html))

# ==================================================================================
# MAPA INTERATIVO (geral para círculo, município ou polígono)
# ==================================================================================
def display_interactive_map(dataset, vis_params, latitude, longitude, title="Mapa Interativo"):
    """Exibe um mapa interativo com camada do Earth Engine e legenda dinâmica."""
    try:
        st.subheader(title)

        Map = geemap.Map(
            basemap="SATELLITE",
            center=[latitude, longitude],
            zoom=7,
            Draw_export=False,
            locate_control=False,
        )

        Map.addLayer(dataset, vis_params, title)

        # Adiciona legenda dinâmica (colorbar)
        add_colorbar_to_map(
            Map,
            title=title,
            palette=vis_params["palette"],
            vmin=vis_params["min"],
            vmax=vis_params["max"],
        )

        st_folium(Map, width=900, height=550)

    except Exception as e:
        st.error(f"Erro ao gerar mapa interativo: {e}")

# ==================================================================================
# MAPA ESTÁTICO (gera imagem via getThumbURL)
# ==================================================================================
def display_static_map(image, vis_params, region, title="Mapa Estático"):
    """Gera um mapa estático via URL e exibe a imagem."""
    try:
        st.subheader(title)

        url = image.getThumbURL({
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"],
            "region": region,
            "dimensions": 600,
        })

        st.image(url, caption="Visualização estática", use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
