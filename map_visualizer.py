# ==================================================================================
# map_visualizer.py — Clima-Cast-Crepaldi (versão científica final)
# ==================================================================================
import streamlit as st
import ee
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from PIL import Image
import geemap.foliumap as geemap
from branca.colormap import LinearColormap
from branca.element import Element

# ------------------------------------------------------------------------------
# Mapa interativo (permanece o mesmo)
# ------------------------------------------------------------------------------
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Renderiza mapa interativo normal (via geemap)."""
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return

    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()
    mapa = geemap.Map(center=centroid, zoom=6)
    mapa.add_basemap("SATELLITE")

    try:
        layer = geemap.ee_tile_layer(ee_image, vis_params, name="Dados ERA5-LAND")
        mapa.add_child(layer)
        mapa.addLayer(ee.Image().paint(feature, 0, 2),
                      {'palette': 'black'}, 'Contorno da Área')

        # Colorbar HTML interativa
        cmap = LinearColormap(
            colors=vis_params["palette"],
            vmin=vis_params["min"],
            vmax=vis_params["max"]
        )
        label_html = f"<b>{unit_label}</b>" if unit_label else ""
        colorbar_html = f"""
        <div style="position: fixed; bottom: 18px; left: 18px;
                    background-color: rgba(255, 255, 255, 0.8);
                    padding: 5px 8px; border-radius: 6px;
                    box-shadow: 0 0 4px rgba(0,0,0,0.25);
                    text-align: center; z-index:9999; font-size:11px;">
            {cmap._repr_html_().replace('width="100%"','width="200px"')}
            <div style="font-weight:600;margin-top:2px;">{label_html}</div>
        </div>
        """
        mapa.get_root().html.add_child(Element(colorbar_html))
        mapa.to_streamlit(height=480)
    except Exception as e:
        st.error(f"⚠️ Falha ao adicionar camada do GEE: {e}")

# ------------------------------------------------------------------------------
# MAPA ESTÁTICO (nova versão via Matplotlib)
# ------------------------------------------------------------------------------
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """
    Gera mapa estático em alta definição via Matplotlib:
    - sem fundo preto
    - interpolação bilinear
    - colorbar integrada
    """
    import requests

    try:
        # 1️⃣ Baixa imagem raster pura (com fundo branco)
        region = feature.geometry().bounds()
        fundo = ee.Image.constant(1).visualize(palette=["ffffff"], min=0, max=1)
        outline = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        final_img = fundo.blend(ee_image.visualize(**vis_params)).blend(
            outline.visualize(palette=["000000"])
        )
        url = final_img.getThumbURL({
            "region": region.getInfo()["coordinates"],
            "dimensions": 1024,  # resolução controlada
            "format": "png",
            "crs": "EPSG:4326"
        })
        r = requests.get(url, timeout=60)
        mapa_img = Image.open(io.BytesIO(r.content)).convert("RGB")
        mapa_array = np.array(mapa_img)

        # 2️⃣ Plotagem com Matplotlib
        fig, ax = plt.subplots(figsize=(7, 6), dpi=200)
        ax.imshow(mapa_array, origin="upper", interpolation="bilinear")
        ax.set_facecolor("white")
        ax.set_axis_off()

        # 3️⃣ Colorbar
        cmap = mpl.colors.LinearSegmentedColormap.from_list("custom", vis_params["palette"])
        norm = mpl.colors.Normalize(vmin=vis_params["min"], vmax=vis_params["max"])
        cb = plt.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                          ax=ax, orientation="horizontal", pad=0.04)
        cb.set_label(unit_label, fontsize=10, weight="bold")
        cb.ax.tick_params(labelsize=8)
        cb.outline.set_visible(False)

        # 4️⃣ Fundo branco e exportação
        fig.patch.set_facecolor("white")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        final_bytes = buf.getvalue()

        return final_bytes, final_bytes, final_bytes

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa estático: {e}")
        return None, None, None
