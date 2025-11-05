# ==================================================================================
# map_visualizer.py — Clima-Cast-Crepaldi (versão final definitiva)
# ==================================================================================
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from PIL import Image
import requests
from branca.colormap import LinearColormap
from branca.element import Element

# -------------------------------------------------------------------------
# Cache de mapa base (para modo interativo)
# -------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _create_base_map(center, zoom, basemap='SATELLITE'):
    mapa = geemap.Map(center=center, zoom=zoom)
    mapa.add_basemap(basemap)
    return mapa

# -------------------------------------------------------------------------
# Colorbar HTML — usada apenas no mapa interativo
# -------------------------------------------------------------------------
def add_colorbar_with_background(mapa, vis_params, unit_label=""):
    try:
        cmap = LinearColormap(
            colors=vis_params["palette"],
            vmin=vis_params["min"],
            vmax=vis_params["max"]
        )
        label_html = f"<b>{unit_label}</b>" if unit_label else ""
        colorbar_html = f"""
        <div style="
            position: fixed;
            bottom: 18px;
            left: 18px;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 5px 8px;
            border-radius: 6px;
            box-shadow: 0 0 4px rgba(0, 0, 0, 0.25);
            text-align: center;
            z-index: 9999;
            font-size: 11px;">
            {cmap._repr_html_().replace('width="100%"', 'width="200px"')}
            <div style="font-size: 11px; font-weight: 600; margin-top: 2px;">{label_html}</div>
        </div>
        """
        mapa.get_root().html.add_child(Element(colorbar_html))
    except Exception as e:
        st.warning(f"⚠️ Falha ao adicionar colorbar: {e}")

# -------------------------------------------------------------------------
# MAPA INTERATIVO (modo Streamlit)
# -------------------------------------------------------------------------
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return
    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()
    mapa = _create_base_map(center=centroid, zoom=6)
    try:
        layer = geemap.ee_tile_layer(ee_image, vis_params, name="Dados ERA5-LAND")
        mapa.add_child(layer)
        mapa.addLayer(ee.Image().paint(feature, 0, 2),
                      {'palette': 'black'}, 'Contorno da Área')
        add_colorbar_with_background(mapa, vis_params, unit_label)
        mapa.to_streamlit(height=480)
    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa interativo: {e}")

# ==================================================================================
# SISTEMA DE MAPA ESTÁTICO — em 3 etapas independentes
# ==================================================================================

# 1️⃣ GERA O MAPA PURO (sem colorbar)
@st.cache_data(show_spinner=False)
def gerar_mapa_puro(ee_image, feature, vis_params):
    """Baixa o mapa do GEE com fundo branco e contorno, sem perda de qualidade."""
    if ee_image is None or feature is None:
        return None
    try:
        region = feature.geometry().bounds()
        fundo = ee.Image.constant(1).visualize(palette=["ffffff"], min=0, max=1)
        contorno = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        final_img = fundo.blend(ee_image.visualize(**vis_params)).blend(
            contorno.visualize(palette=["000000"])
        )
        url = final_img.getThumbURL({
            "region": region.getInfo()["coordinates"],
            "dimensions": 3072,
            "format": "png",
            "crs": "EPSG:4326"
        })
        r = requests.get(url, timeout=60)
        mapa_img = Image.open(io.BytesIO(r.content)).convert("RGB")
        return mapa_img
    except Exception as e:
        st.error(f"⚠️ Erro ao gerar mapa puro: {e}")
        return None

# 2️⃣ GERA A COLORBAR SEPARADA
@st.cache_data(show_spinner=False)
def gerar_colorbar(vis_params, unit_label=""):
    """Cria uma colorbar horizontal em alta definição."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import io
    from PIL import Image
    vmin, vmax = vis_params["min"], vis_params["max"]
    cores = vis_params["palette"]
    cmap = mpl.colors.LinearSegmentedColormap.from_list("custom", cores)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    fig, ax = plt.subplots(figsize=(5.5, 0.35))
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation="horizontal")
    cb.set_label(unit_label, fontsize=9, fontweight="bold")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, length=3)
    fig.patch.set_facecolor("white")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=250, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

# 3️⃣ JUNTA AS DUAS IMAGENS (sem reamostrar o mapa)
def juntar_mapa_e_colorbar(mapa_img, colorbar_img):
    """Combina o mapa e a colorbar sem alterar a resolução."""
    if mapa_img is None or colorbar_img is None:
        return None
    mapa_w, mapa_h = mapa_img.size
    cb_w, cb_h = colorbar_img.size
    novo_h = mapa_h + cb_h + 40
    imagem_final = Image.new("RGB", (mapa_w, novo_h), (255, 255, 255))
    imagem_final.paste(mapa_img, (0, 0))
    offset_x = (mapa_w - cb_w) // 2
    imagem_final.paste(colorbar_img, (offset_x, mapa_h + 20))
    return imagem_final

# -------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL (usada pelo main.py)
# -------------------------------------------------------------------------
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """
    Monta mapa estático completo (mapa + colorbar), sem recomputar o GEE.
    Retorna imagem final em bytes pronta para exibição/exportação.
    """
    try:
        mapa_puro = gerar_mapa_puro(ee_image, feature, vis_params)
        colorbar = gerar_colorbar(vis_params, unit_label)
        combinado = juntar_mapa_e_colorbar(mapa_puro, colorbar)
        if combinado is None:
            return None, None, None

        buf = io.BytesIO()
        combinado.save(buf, format="PNG", quality=98)
        buf.seek(0)
        final_bytes = buf.getvalue()
        return final_bytes, final_bytes, final_bytes

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa estático completo: {e}")
        return None, None, None
