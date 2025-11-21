# ==================================================================================
# map_visualizer.py (v97 - Correção Definitiva: Backend Agg e OO)
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import ee
import io
import base64
import requests
from PIL import Image
import numpy as np 

# --- CONFIGURAÇÃO CRÍTICA PARA SERVIDORES (STREAMLIT CLOUD) ---
import matplotlib
matplotlib.use('Agg') # Força o modo sem interface gráfica (evita erros de display)
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
import matplotlib.colors as mcolors 
# --------------------------------------------------------------

from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 

# ==================================================================================
# MAPA INTERATIVO (Mantido Igual)
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
# COLORBAR INTELIGENTE (Para o Mapa Interativo)
# ==================================================================================

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette or len(palette) == 0: return 

    n_steps = len(palette)
    # Garante que os passos da legenda coincidam com as cores
    index = np.linspace(vmin, vmax, n_steps + 1).tolist()
    
    # Formatação inteligente (decimais para umidade, inteiros para temperatura)
    if (vmax - vmin) < 10: fmt = '%.2f' 
    else: fmt = '%.0f' 
    
    try:
        colormap = StepColormap(
            colors=palette, index=index, vmin=vmin, vmax=vmax,
            caption=vis_params.get("caption", unit_label)
        )
        colormap.fmt = fmt
        
        macro = MacroElement()
        macro._template = Template(f"""{{% macro html(this, kwargs) %}}<div style="position: fixed; bottom: 15px; left: 15px; z-index: 9999; background-color: rgba(255, 255, 255, 0.85); padding: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">{colormap._repr_html_()}</div>{{% endmacro %}}""")
        mapa.get_root().add_child(macro)
    except: pass

# ==================================================================================
# MAPA ESTÁTICO (Geração Robusta de Imagens)
# ==================================================================================

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, label: str) -> str:
    """
    Gera a barra de cores estática usando a abordagem Orientada a Objetos (Thread-Safe).
    Isso impede que a barra suma em execuções paralelas ou no servidor.
    """
    try:
        # 1. Cria uma figura isolada na memória (não usa plt global)
        # Tamanho (6, 1.2) garante espaço suficiente para texto e números
        fig = Figure(figsize=(6, 1.2), dpi=150)
        FigureCanvasAgg(fig) # Acopla o canvas Agg
        
        # 2. Define a área do eixo [left, bottom, width, height]
        # Bottom=0.4 deixa espaço para os números não serem cortados
        ax = fig.add_axes([0.05, 0.4, 0.90, 0.3])
        
        # 3. Desenha a barra
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=256)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cb = ColorbarBase(ax, cmap=cmap, norm=norm, orientation="horizontal")
        
        # 4. Estilização (Preto sobre fundo transparente/branco)
        cb.set_label(label, fontsize=10, color='black', labelpad=5)
        cb.ax.tick_params(labelsize=9, color='black', labelcolor='black')
        cb.outline.set_edgecolor('black')
        cb.outline.set_linewidth(1)
        
        # 5. Formatação dos números (Ticks)
        if (vmax - vmin) < 10:
            cb.ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.2f'))
        else:
            cb.ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f'))
        
        # 6. Salva no buffer de memória
        buf = io.BytesIO()
        # facecolor='white' garante que o fundo não fique transparente (melhor leitura)
        fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1, facecolor='white')
        buf.seek(0)
        
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('ascii')}"
        
    except Exception as e:
        st.error(f"Erro ao gerar legenda: {e}")
        return None

def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    try:
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        final = visualized_data.blend(outline.visualize(palette='000000'))

        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1]))
            region = feature.geometry().buffer(dim * 10000) 
        except: 
            region = feature.geometry()

        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img_bytes = requests.get(url).content
        
        # Tratamento de imagem (Fundo Branco)
        img = Image.open(io.BytesIO(img_bytes))
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf = io.BytesIO()
        bg.convert('RGB').save(buf, format="JPEG")
        jpg = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        png = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('ascii')}"
        
        # Gera a legenda usando a função robusta acima
        lbl = vis_params.get("caption", unit_label)
        pal = vis_params.get("palette", ["#FFFFFF", "#000000"])
        cbar = _make_compact_colorbar(pal, vis_params.get("min", 0), vis_params.get("max", 1), lbl)

        return png, jpg, cbar
    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
        return None, None, None

def _make_title_image(title_text: str, width: int, height: int = 50) -> bytes:
    """Gera o título como imagem usando a mesma abordagem segura (OO)."""
    try:
        dpi = 100
        fig = Figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        FigureCanvasAgg(fig)
        fig.patch.set_facecolor('white')
        
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')
        ax.text(0.5, 0.5, title_text, ha='center', va='center', fontsize=14, fontweight='bold', wrap=True)
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05, facecolor='white')
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
