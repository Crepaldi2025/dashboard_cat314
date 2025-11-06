# ==================================================================================
# map_visualizer.py — Funções de visualização do Clima-Cast-Crepaldi
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
from streamlit_folium import st_folium
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm


# ==================================================================================
# MAPA INTERATIVO — COMPATÍVEL COM main.py
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Exibe o mapa interativo com fundo de satélite e colorbar discreta."""
    try:
        centroid = feature.geometry().centroid(maxError=1).getInfo()["coordinates"]
        centroid.reverse()  # (lon, lat) → (lat, lon)

        mapa = geemap.Map(center=centroid, zoom=7)
        mapa.add_basemap("SATELLITE")  # garante fundo de imagem real
        mapa.addLayer(ee_image, vis_params, "Dados ERA5-Land")
        mapa.addLayer(
            ee.Image().paint(feature, 0, 2),
            {"palette": "black"},
            "Contorno da Área"
        )

        _add_colorbar_bottomleft(mapa, vis_params, unit_label)
        mapa.to_streamlit(height=500)
    except Exception as e:
        st.error(f"Erro ao renderizar mapa interativo: {e}")


# ==================================================================================
# MAPA ESTÁTICO — GERAÇÃO DE IMAGEM
# ==================================================================================
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera o mapa estático (PNG/JPG) e colorbar compacta."""
    try:
        url = ee_image.getThumbURL({
            "region": feature.geometry(),
            "dimensions": 800,
            "format": "png",
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"]
        })

        import requests
        img_bytes = requests.get(url).content
        b64_png = base64.b64encode(img_bytes).decode("ascii")
        png_url = f"data:image/png;base64,{b64_png}"

        # --- Versão JPEG ---
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        jpg_buffer = io.BytesIO()
        img.convert("RGB").save(jpg_buffer, format="JPEG")
        jpg_b64 = base64.b64encode(jpg_buffer.getvalue()).decode("ascii")
        jpg_url = f"data:image/jpeg;base64,{jpg_b64}"

        # --- Colorbar compacta ---
        palette = vis_params.get("palette", ["#FFFFFF", "#000000"])
        vmin = vis_params.get("min", 0)
        vmax = vis_params.get("max", 1)
        label = unit_label or ""
        ul = label.lower()

        if "mm" in ul:
            ticks = [0, 100, 200, 300, 400, 500]
        elif "°" in ul or "c" in ul:
            ticks = [0, 10, 20, 30, 40]
        elif "m/s" in ul or "vento" in ul:
            ticks = [0, 5, 10, 15, 20, 25, 30]
        else:
            ticks = None

        colorbar_img = _make_compact_colorbar(palette, vmin, vmax, label, ticks)

        return png_url, jpg_url, colorbar_img

    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
        return None, None, None


# ==================================================================================
# COLORBAR (INTERATIVO E ESTÁTICO)
# ==================================================================================
def _add_colorbar_bottomleft(mapa, vis_params, unit_label):
    """Colorbar no canto inferior esquerdo do mapa interativo."""
    from branca.colormap import LinearColormap
    from branca.element import Template, MacroElement

    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette:
        return

    ul = (unit_label or "").lower()
    if "°" in ul or "temp" in ul:
        label = "Temperatura (°C)"
    elif "mm" in ul:
        label = "Precipitação (mm)"
    elif "m/s" in ul or "vento" in ul:
        label = "Vento (m/s)"
    elif unit_label:
        label = str(unit_label)
    else:
        label = ""

    colormap = LinearColormap(colors=palette, vmin=vmin, vmax=vmax)
    colormap.caption = label
    html = colormap._repr_html_()
    template = Template(f"""
    {{% macro html(this, kwargs) %}}
    <div style="position: fixed; bottom: 12px; left: 12px; z-index: 9999;
                background: rgba(255,255,255,0.85); padding: 6px 8px;
                border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3);">
        {html}
    </div>
    {{% endmacro %}}
    """)
    macro = MacroElement()
    macro._template = template
    mapa.get_root().add_child(macro)


def _make_compact_colorbar(palette, vmin, vmax, label, ticks=None):
    """Gera uma colorbar compacta (horizontal) como data URL PNG."""
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    cmap = LinearSegmentedColormap.from_list("custom", palette, N=256)
    norm = cm.colors.Normalize(vmin=vmin, vmax=vmax)
    cb = ColorbarBase(ax, cmap=cmap, norm=norm, orientation="horizontal")
    if ticks is not None:
        cb.set_ticks(ticks)
    cb.set_label(label, fontsize=7)
    cb.ax.tick_params(labelsize=6, length=2, pad=1)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", pad_inches=0.05, transparent=True)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"

# ==================================================================================
# === FIM ===
# ==================================================================================
