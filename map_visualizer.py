# ==================================================================================
# map_visualizer.py (Corrigido v80 - Legendas Decimais e Inteiras)
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
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 

# ==================================================================================
# MAPA INTERATIVO
# ==================================================================================

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = ""):
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
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "black"}, "Contorno")
    
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    if bounds:
        mapa.fit_bounds(bounds)
    
    mapa.to_streamlit(height=500, use_container_width=True)

# ==================================================================================
# COLORBAR INTELIGENTE (Corrigido)
# ==================================================================================

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette or len(palette) == 0: return 

    n_colors = len(palette)
    
    # --- CORREÇÃO: Lógica para Decimais vs Inteiros ---
    # Se a diferença for pequena (ex: Umidade Solo 0.0 a 0.6), usa decimais.
    # Se for grande (ex: Temp 0 a 40), usa inteiros.
    is_small_scale = (vmax - vmin) <= 10
    
    if is_small_scale:
        # Cria passos decimais exatos
        index = np.linspace(vmin, vmax, n_colors + 1).tolist()
        fmt = '%.2f' # Formato 0.00
    else:
        # Cria passos inteiros
        step = (vmax - vmin) / n_colors
        if step < 1: step = 1
        index = np.arange(vmin, vmax + step, step).tolist()
        fmt = '%.0f' # Formato 0

    # Garante que o StepColormap receba cores e índices alinhados
    # Às vezes o np.arange gera um indice a mais que cores, precisamos ajustar
    if len(index) > len(palette) + 1:
        index = index[:len(palette)+1]
    
    # Criação da Legenda
    try:
        colormap = StepColormap(
            colors=palette, 
            index=index, 
            vmin=vmin, 
            vmax=vmax,
            caption=vis_params.get("caption", unit_label)
        )
        colormap.fmt = fmt
        
        # Injeta HTML/CSS para fixar no canto inferior esquerdo
        macro = MacroElement()
        macro._template = Template(f"""
        {{% macro html(this, kwargs) %}}
        <div style="position: fixed; bottom: 15px; left: 15px; z-index: 9999;
                    background-color: rgba(255, 255, 255, 0.85);
                    padding: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
            {colormap._repr_html_()}
        </div>
        {{% endmacro %}}
        """)
        mapa.get_root().add_child(macro)
        
    except Exception as e:
        print(f"Erro ao gerar colorbar: {e}")

# ==================================================================================
# MAPA ESTÁTICO (Geração de Imagens)
# ==================================================================================

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, label: str) -> str:
    fig = plt.figure(figsize=(4, 0.4), dpi=150) # Levemente maior
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    try:
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=100)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cb = ColorbarBase(ax, cmap=cmap, norm=norm, orientation="horizontal")
        cb.set_label(label, fontsize=8)
        cb.ax.tick_params(labelsize=7)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('ascii')}"
    except: return None

def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    try:
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        final = visualized_data.blend(outline.visualize(palette='000000'))

        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            # Buffer dinâmico baseado no tamanho da área
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1]))
            region = feature.geometry().buffer(dim * 10000) # Ajuste de buffer
        except: region = feature.geometry()

        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img_bytes = requests.get(url).content
        
        img = Image.open(io.BytesIO(img_bytes))
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf = io.BytesIO()
        bg.convert('RGB').save(buf, format="JPEG")
        jpg = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        png = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('ascii')}"
        
        lbl = vis_params.get("caption", unit_label)
        cbar = _make_compact_colorbar(vis_params.get("palette", ["#FFF", "#000"]), vis_params.get("min", 0), vis_params.get("max", 1), lbl)

        return png, jpg, cbar
    except Exception as e:
        st.error(f"Erro estático: {e}")
        return None, None, None

def _make_title_image(title_text: str, width: int, height: int = 50) -> bytes:
    try:
        dpi = 100
        fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        fig.patch.set_facecolor('white')
        plt.text(0.5, 0.5, title_text, ha='center', va='center', fontsize=14, fontweight='bold', wrap=True)
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05, facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except: return None

def _stitch_images_to_bytes(title_bytes: bytes, map_bytes: bytes, colorbar_bytes: bytes, format: str = 'PNG') -> bytes:
    try:
        t = Image.open(io.BytesIO(title_bytes)).convert("RGBA")
        m = Image.open(io.BytesIO(map_bytes)).convert("RGBA")
        c = Image.open(io.BytesIO(colorbar_bytes)).convert("RGBA")
        
        w = m.width
        def rz(im, tw): return im if im.width == tw else im.resize((tw, int(im.height * (tw/im.width))), Image.Resampling.LANCZOS)
        t = rz(t, w)
        c = rz(c, w)

        final = Image.new('RGBA', (w, t.height + m.height + c.height), (255, 255, 255, 255))
        final.paste(t, (0, 0), t)
        final.paste(m, (0, t.height), m)
        final.paste(c, (0, t.height + m.height), c)
        
        buf = io.BytesIO()
        final.convert('RGB').save(buf, format='JPEG', quality=95) if format.upper() == 'JPEG' else final.save(buf, format='PNG')
        return buf.getvalue()
    except: return None
