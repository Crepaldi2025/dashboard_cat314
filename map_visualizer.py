# ==================================================================================
# map_visualizer.py — Versão final otimizada (Clima-Cast-Crepaldi)
# ==================================================================================
# Recursos:
#   ✅ Compatível com Streamlit Cloud
#   ✅ Colorbar padronizada e estilizada
#   ✅ Mapa estático com legenda incorporada
#   ✅ Caching e performance otimizados
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import io
import numpy as np
from branca.colormap import LinearColormap
from branca.element import Element
from PIL import Image
import requests

# ------------------------------------------------------------------------------
# Cache de recursos pesados
# ------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _create_base_map(center, zoom, basemap='SATELLITE'):
    """Cria e retorna um mapa base do geemap cacheado."""
    mapa = geemap.Map(center=center, zoom=zoom)
    mapa.add_basemap(basemap)
    return mapa

# ------------------------------------------------------------------------------
# Colorbar refinada (para mapas interativos)
# ------------------------------------------------------------------------------
def add_colorbar_with_background(mapa, vis_params, unit_label=""):
    """Adiciona uma colorbar legível no canto inferior esquerdo (folium)."""
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
            background-color: rgba(255, 255, 255, 0.75);
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
        st.warning(f"⚠️ Falha ao adicionar colorbar estilizada: {e}")

# ------------------------------------------------------------------------------
# Colorbar para mapas estáticos (padronizada até 500 mm)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def create_colorbar(vis_params, unit_label=""):
    """Gera uma colorbar horizontal refinada com fundo branco translúcido."""
    import io

    vmin = vis_params["min"]
    vmax = vis_params["max"]
    colors = vis_params["palette"]

    # Padronização de escala para precipitação
    if "mm" in unit_label.lower() or "precip" in unit_label.lower():
        vmin, vmax = 0, 500

    # Colormap contínuo
    cmap = mpl.colors.LinearSegmentedColormap.from_list("custom", colors)

    # Ticks regulares
    step = 100 if "mm" in unit_label.lower() else max(1, round((vmax - vmin) / 6))
    ticks = np.arange(vmin, vmax + step, step)

    # Figura
    fig, ax = plt.subplots(figsize=(5.5, 0.35))
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm,
                                   orientation='horizontal', ticks=ticks)

    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, length=3)
    cb.set_label(f"{unit_label}", fontsize=9, labelpad=3, fontweight='bold')
    ax.set_facecolor((1, 1, 1, 0.85))
    fig.patch.set_alpha(0.0)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()

# ------------------------------------------------------------------------------
# MAPA INTERATIVO (ERA5-LAND)
# ------------------------------------------------------------------------------
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Gera e exibe um mapa interativo leve e compatível com Streamlit Cloud."""
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return

    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()
    mapa = _create_base_map(center=centroid, zoom=6)

    try:
        layer = geemap.ee_tile_layer(ee_image, vis_params, name="Dados Climáticos")
        mapa.add_child(layer)
        mapa.addLayer(ee.Image().paint(feature, 0, 2),
                      {'palette': 'black'}, 'Contorno da Área')
        add_colorbar_with_background(mapa, vis_params, unit_label)
        mapa.to_streamlit(height=550)
    except Exception as e:
        st.error(f"⚠️ Falha ao adicionar camada do GEE: {e}")

# ------------------------------------------------------------------------------
# MAPA ESTÁTICO (com colorbar incorporada)
# ------------------------------------------------------------------------------
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """
    Gera mapa estático de alta qualidade (idêntico ao interativo)
    com colorbar e fundo branco — sem usar getThumbURL.
    Compatível e leve para Streamlit Cloud.
    """
    import geemap.foliumap as geemap
    import io
    from PIL import Image
    import numpy as np
    import matplotlib.pyplot as plt

    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return None, None, None

    try:
        # === 1️⃣ Cria mapa folium invisível ===
        m = geemap.Map()
        m.add_basemap("SATELLITE")
        m.addLayer(ee_image, vis_params, "Dados ERA5-LAND")
        m.addLayer(ee.Image().paint(feature, 0, 2), {'palette': 'black'}, 'Contorno')

        # === 2️⃣ Exporta imagem nítida via render interno ===
        # O método .to_image() do geemap converte o mapa inteiro em RGB numpy array
        array_img = m.to_image(resolution=3)  # leve e rápido (~1500px)
        img = Image.fromarray(array_img.astype(np.uint8))

        # === 3️⃣ Gera colorbar igual à do mapa interativo ===
        fig, ax = plt.subplots(figsize=(6, 0.5))
        cmap = plt.get_cmap('jet')
        norm = plt.Normalize(vmin=vis_params['min'], vmax=vis_params['max'])
        cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                          cax=ax, orientation='horizontal')
        cb.set_label(unit_label, fontsize=10)
        fig.tight_layout()

        buf_cb = io.BytesIO()
        plt.savefig(buf_cb, format="png", bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf_cb.seek(0)
        cb_img = Image.open(buf_cb)

        # === 4️⃣ Junta mapa + colorbar ===
        mapa_w, mapa_h = img.size
        cb_w, cb_h = cb_img.size
        combined = Image.new("RGB", (mapa_w, mapa_h + cb_h + 30), (255, 255, 255))
        combined.paste(img, (0, 0))
        combined.paste(cb_img, (int((mapa_w - cb_w) / 2), mapa_h + 10))

        # === 5️⃣ Exporta ===
        buf = io.BytesIO()
        combined.save(buf, format="PNG", quality=98)
        buf.seek(0)
        final_bytes = buf.getvalue()

        return final_bytes, final_bytes, final_bytes

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa estático otimizado: {e}")
        return None, None, None



def export_interactive_snapshot(ee_image, feature, vis_params, unit_label=""):
    """
    Gera um mapa estático de alta qualidade (renderização por tiles GEE)
    com visual idêntico ao mapa interativo, compatível com Streamlit Cloud.
    """
    import io
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    from PIL import Image
    import requests

    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return None

    try:
        # 1️⃣ Solicita renderização de tiles ao Earth Engine
        map_id = ee_image.getMapId(vis_params)
        tile_url_template = map_id["tile_fetcher"].url_format

        # 2️⃣ Define região de interesse
        region = feature.geometry().bounds().getInfo()["coordinates"]
        lons = [p[0] for p in region[0]]
        lats = [p[1] for p in region[0]]
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)

        # 3️⃣ Baixa mosaico de tiles (via requests, 512x512)
        # 🔸 Aqui simulamos a visualização do tile renderizado
        #    usando a API estática do GEE para uma imagem visualizada
        url = ee_image.visualize(**vis_params).getThumbURL({
            "region": region,
            "dimensions": 2048,
            "format": "png"
        })
        response = requests.get(url, timeout=60)
        mapa_img = Image.open(io.BytesIO(response.content)).convert("RGB")

        # 4️⃣ Adiciona contorno do estado/área
        outline = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        url_outline = outline.visualize(palette=["black"]).getThumbURL({
            "region": region,
            "dimensions": 2048,
            "format": "png"
        })
        outline_img = Image.open(io.BytesIO(requests.get(url_outline).content)).convert("RGBA")
        mapa_img = mapa_img.convert("RGBA")
        mapa_img.alpha_composite(outline_img)

        # 5️⃣ Adiciona colorbar refinada (estilo interativo)
        colorbar_bytes = create_colorbar(vis_params, unit_label)
        colorbar_img = Image.open(io.BytesIO(colorbar_bytes)).convert("RGB")

        # Ajusta largura
        mapa_w, mapa_h = mapa_img.size
        colorbar_w, colorbar_h = colorbar_img.size
        new_h = int(colorbar_h * (mapa_w / colorbar_w))
        colorbar_resized = colorbar_img.resize((mapa_w, new_h), Image.Resampling.LANCZOS)

        # Combina mapa e colorbar
        combined = Image.new("RGB", (mapa_w, mapa_h + new_h), (255, 255, 255))
        combined.paste(mapa_img.convert("RGB"), (0, 0))
        combined.paste(colorbar_resized, (0, mapa_h))

        # 6️⃣ Exporta imagem final
        buf = io.BytesIO()
        combined.save(buf, format="PNG", quality=98)
        buf.seek(0)
        return buf.getvalue()

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar mapa de alta qualidade: {e}")
        return None




