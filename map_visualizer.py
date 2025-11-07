# ==================================================================================
# map_visualizer.py
# 
# Módulo: Clima-Cast-Crepaldi
# Autor: Paulo C. Crepaldi
#
# Descrição:
# (v36) - REMOVIDA a lógica do título HTML flutuante. O título
#         agora é renderizado diretamente pelo main.py (st.subheader).
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import ee
import io
import base64
import requests
from PIL import Image
import numpy as np 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 


# ==================================================================================
# MAPA INTERATIVO (Resultado da Análise)
# ==================================================================================

# --- INÍCIO DA CORREÇÃO v36 ---
def create_interactive_map(ee_image: ee.Image, 
                           feature: ee.Feature, 
                           vis_params: dict, 
                           unit_label: str = ""):
# --- FIM DA CORREÇÃO v36 ---
    """
    (v34) Cria e exibe um mapa interativo que se centraliza e 
    dá zoom automaticamente na área de interesse.
    """
    
    try:
        coords = feature.geometry().bounds().getInfo()['coordinates'][0]
        lon_min = coords[0][0]
        lat_min = coords[0][1]
        lon_max = coords[2][0]
        lat_max = coords[2][1]
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
    except Exception:
        bounds = None

    mapa = geemap.Map(center=[-15.78, -47.93], zoom=4, basemap="HYBRID")
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {"palette": "black"}, "Contorno da Área")
    
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)
    
    # --- INÍCIO DA CORREÇÃO v36 ---
    # Bloco de código do Título HTML foi REMOVIDO daqui
    # --- FIM DA CORREÇÃO v36 ---

    if bounds:
        mapa.fit_bounds(bounds)
    
    mapa.to_streamlit(height=500, use_container_width=True)


# ==================================================================================
# COLORBAR PARA MAPAS INTERATIVOS (Idêntico v31)
# ==================================================================================
# (Nenhuma alteração nesta seção)

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    """
    (v31) Adiciona legenda discreta com valores inteiros.
    """
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette or len(palette) == 0:
        return 

    N_STEPS = len(palette) 
    index = np.linspace(vmin, vmax, N_STEPS + 1).astype(int) 

    colormap = StepColormap(
        colors=palette, 
        index=index, 
        vmin=vmin, 
        vmax=vmax
    )
    
    colormap.tick_labels = [f'{i:.0f}' for i in colormap.index]

    ul = (unit_label or "").lower()
    if "°" in unit_label or "temp" in ul:
        label = "Temperatura (°C)"
    elif "mm" in ul:
        label = "Precipitação (mm)"
    elif "m/s" in ul or "vento" in ul:
        label = "Vento (m/s)"
    else:
        label = str(unit_label) if unit_label else ""

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
# COLORBAR COMPACTA (MAPA ESTÁTICO) (Idêntico v29)
# ==================================================================================
# (Nenhuma alteração nesta seção)

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, 
                           label: str) -> str:
    """
    (v29) Gera legenda horizontal discreta (Matplotlib).
    """
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    
    try:
        N_STEPS = len(palette)
        boundaries = np.linspace(vmin, vmax, N_STEPS + 1)
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=N_STEPS)
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
    except Exception as e:
        st.error(f"Erro ao criar colormap: {e}")
        plt.close(fig)
        return None

    cb = ColorbarBase(
        ax, 
        cmap=cmap, 
        norm=norm, 
        boundaries=boundaries,
        ticks=boundaries,
        spacing='proportional',
        orientation="horizontal"
    )
        
    cb.set_label(label, fontsize=7)
    cb.ax.set_xticklabels([f'{t:g}' for t in boundaries])
    cb.ax.tick_params(labelsize=6, length=2, pad=1)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", pad_inches=0.05, transparent=True)
    plt.close(fig)
    buf.seek(0)
    
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ==================================================================================
# MAPA ESTÁTICO — GERAÇÃO DE IMAGENS (Idêntico v17)
# ==================================================================================
# (Nenhuma alteração nesta seção)

def create_static_map(ee_image: ee.Image, 
                      feature: ee.Feature, 
                      vis_params: dict, 
                      unit_label: str = "") -> tuple[str, str, str]:
    """
    Gera o mapa estático (PNG/JPG) e a legenda (colorbar) discreta.
    """
    try:
        visualized_data = ee_image.visualize(
            min=vis_params["min"],
            max=vis_params["max"],
            palette=vis_params["palette"]
        )
        outline = ee.Image().paint(featureCollection=feature, color=0, width=2)
        visualized_outline = outline.visualize(palette='000000')
        final_image_with_outline = visualized_data.blend(visualized_outline)

        url = final_image_with_outline.getThumbURL({
            "region": feature.geometry(),
            "dimensions": 800,
            "format": "png"
        })

        img_bytes = requests.get(url).content
        b64_png = base64.b64encode(img_bytes).decode("ascii")
        png_url = f"data:image/png;base64,{b64_png}"

        img = Image.open(io.BytesIO(img_bytes))
        jpg_buffer = io.BytesIO()
        img.convert("RGB").save(jpg_buffer, format="JPEG")
        jpg_b64 = base64.b64encode(jpg_buffer.getvalue()).decode("ascii")
        jpg_url = f"data:image/jpeg;base64,{jpg_b64}"

        palette = vis_params.get("palette", ["#FFFFFF", "#000000"])
        vmin = vis_params.get("min", 0)
        vmax = vis_params.get("max", 1)
        label = unit_label or ""
        
        colorbar_img = _make_compact_colorbar(palette, vmin, vmax, label)

        return png_url, jpg_url, colorbar_img

    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
        return None, None, None
# ==================================================================================
# FUNÇÕES DE COSTURA DE IMAGEM (Idênticas v31)
# ==================================================================================
# (Nenhuma alteração nesta seção)

def _make_title_image(title_text: str, width: int, height: int = 50) -> bytes:
    """
    Cria uma imagem PNG (como bytes) a partir de um texto de título usando Matplotlib.
    """
    try:
        dpi = 100
        fig_width = width / dpi
        fig_height = height / dpi
        fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
        fig.patch.set_facecolor('white')
        plt.text(0.5, 0.5, title_text, 
                 ha='center', va='center', 
                 fontsize=14, 
                 fontweight='bold',
                 wrap=True)
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05, facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        st.error(f"Erro ao criar imagem do título: {e}")
        return None

def _stitch_images_to_bytes(title_bytes: bytes, map_bytes: bytes, 
                            colorbar_bytes: bytes, format: str = 'PNG') -> bytes:
    """
    Costura verticalmente três imagens (título, mapa, colorbar) em uma única imagem.
    """
    try:
        title_img = Image.open(io.BytesIO(title_bytes))
        map_img = Image.open(io.BytesIO(map_bytes))
        colorbar_img = Image.open(io.BytesIO(colorbar_bytes))

        width = map_img.width
        
        def resize_to_width(img, target_width):
            if img.width == target_width:
                return img
            ratio = target_width / img.width
            target_height = int(img.height * ratio)
            return img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        title_img = resize_to_width(title_img, width)
        colorbar_img = resize_to_width(colorbar_img, width)

        total_height = title_img.height + map_img.height + colorbar_img.height
        final_img = Image.new('RGB', (width, total_height), 'white')

        final_img.paste(title_img, (0, 0))
        final_img.paste(map_img, (0, title_img.height))
        final_img.paste(colorbar_img, (0, title_img.height + map_img.height))

        final_buffer = io.BytesIO()
        save_format = 'JPEG' if format.upper() == 'JPEG' else 'PNG'
        final_img.save(final_buffer, format=save_format)
        
        return final_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Erro ao costurar imagens: {e}")
        return None
