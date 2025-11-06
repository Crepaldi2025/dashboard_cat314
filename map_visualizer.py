# ==================================================================================
# map_visualizer.py — Funções de visualização (Corrigido v2)
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import ee
# 'st_folium' não é mais usado neste arquivo
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm
import requests
from PIL import Image

# ==================================================================================
# MAPA INTERATIVO — COMPATÍVEL COM main.py
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Exibe o mapa interativo com colorbar discreta no canto inferior esquerdo."""
    try:
        centroid = feature.geometry().centroid(maxError=1).getInfo()["coordinates"]
        centroid.reverse()  # (lon, lat) → (lat, lon)
        zoom = 7
    except Exception:
        centroid = [-15.78, -47.93] # Centro do Brasil
        zoom = 4

    mapa = geemap.Map(center=centroid, zoom=zoom)
    mapa.add_basemap("SATELLITE")
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {"palette": "black"}, "Contorno da Área")
    
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)
    
    # ----------------------------------------------------------------------------------
    # CORREÇÃO DE TYPEERROR: Revertido de st_folium() para mapa.to_streamlit()
    # geemap.Map deve ser renderizado com seu próprio método .to_streamlit()
    # ----------------------------------------------------------------------------------
    return mapa.to_streamlit(height=500, use_container_width=True)


# ==================================================================================
# COLORBAR PARA MAPAS INTERATIVOS
# ==================================================================================
def _add_colorbar_discreto(mapa, vis_params, unidade):
    """(Função auxiliar) Colorbar discreto padrão."""
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


def _add_colorbar_bottomleft(mapa, vis_params, unit_label):
    """(Função auxiliar) Colorbar no canto inferior esquerdo do mapa interativo."""
    from branca.colormap import LinearColormap
    from branca.element import Template, MacroElement
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette:
        return
    ul = (unit_label or "").lower()
    if "°" in unit_label or "temp" in ul:
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
                border-radius: 6px; box_shadow: 0 1px 4px rgba(0,0,0,0.3);">
        {html}
    </div>
    {{% endmacro %}}
    """)
    macro = MacroElement()
    macro._template = template
    mapa.get_root().add_child(macro)


# ==================================================================================
# COLORBAR COMPACTA (MAPA ESTÁTICO)
# ==================================================================================
def _make_compact_colorbar(palette, vmin, vmax, label, ticks=None):
    """(Função auxiliar) Gera uma colorbar compacta (horizontal) como data URL PNG."""
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    
    try:
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=256)
        norm = cm.colors.Normalize(vmin=vmin, vmax=vmax)
    except Exception as e:
        st.error(f"Erro ao criar colormap: {e}")
        plt.close(fig)
        return None

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
# MAPA ESTÁTICO — GERAÇÃO DE IMAGENS
# ==================================================================================
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera o mapa estático (PNG/JPG) e colorbar compacta."""
    try:
        region_geometry = feature.geometry()

        url = ee_image.getThumbURL({
            "region": region_geometry,
            "dimensions": 800,
            "format": "png",
            "min": vis_params["min"],
            "max": vis_params["max"],
            "palette": vis_params["palette"]
        })

        img_bytes = requests.get(url).content
        b64_png = base64.b64encode(img_bytes).decode("ascii")
        png_url = f"data:image/png;base64,{b64_png}"

        img = Image.open(io.BytesIO(img_bytes))
        jpg_buffer = io.BytesIO()
        img.convert("RGB").save(jpg_buffer, format="JPEG")
        jpg_b64 = base64.b64encode(jpg_buffer.getvalue()).decode("ascii")
        jpg_url = f"data:image/jpeg;base64,{jpg_b64}"

        # --- Geração da Colorbar (Corrigida na v1) ---
        palette = vis_params.get("palette", ["#FFFFFF", "#000000"])
        vmin = vis_params.get("min", 0)
        vmax = vis_params.get("max", 1)
        label = unit_label or ""
        ul = label.lower()

        ticks = None 
        if "mm" in ul and vmin == 0 and vmax == 500:
            ticks = [0, 100, 200, 300, 400, 500]
        elif ("°" in ul or "c" in ul) and vmin == 0 and vmax == 40:
            ticks = [0, 10, 20, 30, 40]
        elif ("m/s" in ul or "vento" in ul) and vmin == 0 and vmax == 30:
            ticks = [0, 5, 10, 15, 20, 25, 30]
        
        colorbar_img = _make_compact_colorbar(palette, vmin, vmax, label, ticks)

        return png_url, jpg_url, colorbar_img

    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
        return None, None, None
