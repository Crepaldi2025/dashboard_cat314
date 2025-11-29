# ==================================================================================
# map_visualizer.py
# ==================================================================================

# ------------------------
# - Bibliotecas importadas
# ------------------------

import streamlit as st
import geemap.foliumap as geemap
import ee
import io
import base64
import requests
from PIL import Image
import numpy as np
import matplotlib.ticker as ticker
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.colorbar import ColorbarBase
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 
import folium 

# ---------------
# MAPA INTERATIVO
# ---------------

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = ""):
    try:
        # Tenta obter os limites do polígono para ajustar o zoom
        coords = feature.geometry().bounds().getInfo()['coordinates'][0]
        lon_min = coords[0][0]
        lat_min = coords[0][1]
        lon_max = coords[2][0]
        lat_max = coords[2][1]
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        
        # Tenta obter o centroide para colocar o marcador
        centro = feature.geometry().centroid().getInfo()['coordinates'] # [lon, lat]
        lon_c, lat_c = centro[0], centro[1]
    except Exception:
        bounds = None
        lat_c, lon_c = -15.78, -47.93

    # 1. Cria o mapa vazio
    mapa = geemap.Map(center=[lat_c, lon_c], zoom=4)
    
    # 2. Adiciona explicitamente o Google Hybrid (Satélite + Ruas/Cidades)
    # Isso garante que o visual seja igual ao da ferramenta de desenho
    mapa.add_tile_layer(
        url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        name="Google Hybrid",
        attribution="Google"
    )

    # 3. Adiciona as camadas do Earth Engine
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "black"}, "Contorno")
    
    # 4. Adiciona o Marcador no Centro (Lat/Lon)
    folium.Marker(
        location=[lat_c, lon_c],
        tooltip=f"Centro: Lat {lat_c:.4f}, Lon {lon_c:.4f}",
        popup=f"📍 Centro da Área<br><b>Lat:</b> {lat_c:.5f}<br><b>Lon:</b> {lon_c:.5f}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(mapa)
    
    # 5. Adiciona Legenda
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    # 6. Ajusta o Zoom
    if bounds:
        mapa.fit_bounds(bounds)
    
    # 7. Renderiza no Streamlit
    mapa.to_streamlit(height=500, use_container_width=True)

# -------------------
# COLORBAR INTERATIVO 
# -------------------

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette or len(palette) == 0: return 

    N_STEPS = len(palette) 
    step = (vmax - vmin) / N_STEPS
    if step == 0: step = 1 # Proteção
    
    # Cria índices
    index = np.linspace(vmin, vmax, N_STEPS + 1).tolist()

    # Formatação
    if (vmax - vmin) < 10: fmt = '%.2f'
    else: fmt = '%.0f'

    colormap = StepColormap(colors=palette, index=index, vmin=vmin, vmax=vmax)
    colormap.fmt = fmt

    # Tenta caption ou usa unit_label
    custom_caption = vis_params.get("caption")
    label = custom_caption if custom_caption else unit_label

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

# -------------
# MAPA ESTÁTICO
# -------------

def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    """
    Gera uma imagem estática leve (sem Sentinel) com fundo branco,
    dados climáticos, contorno e um ponto vermelho no centro.
    """
    try:
        # 1. Visualizar os Dados Climáticos
        visualized_data = ee_image.visualize(
            min=vis_params["min"], 
            max=vis_params["max"], 
            palette=vis_params["palette"]
        )
        
        # 2. Visualizar o Contorno (Linha preta)
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        outline_vis = outline.visualize(palette='000000')

        # 3. Visualizar o Ponto Central (Vermelho)
        # Cria um feature point no centroide
        center_pt = ee.FeatureCollection([ee.Feature(feature.geometry().centroid())])
        # Pinta o ponto (color=1) com espessura (width=3)
        center_img = ee.Image().paint(center_pt, 1, 3)
        center_vis = center_img.visualize(palette=['FF0000']) # Vermelho

        # 4. Composição Final: Dados -> Contorno -> Centro
        final = visualized_data.blend(outline_vis).blend(center_vis)

        # 5. Definir a região de recorte
        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1])) * 111000 
            # Buffer de 5%
            region = feature.geometry().buffer(dim * 0.05)
        except: 
            region = feature.geometry()

        # 6. Gerar URL e baixar imagem
        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img_bytes = requests.get(url).content
        
        # 7. Processamento seguro da imagem (Correção de "bad transparency mask")
        # .convert("RGBA") é crucial aqui!
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        
        # Cria fundo branco limpo
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf = io.BytesIO()
        bg.convert('RGB').save(buf, format="JPEG")
        jpg = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        png = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('ascii')}"
        
        # Legenda Estática
        lbl = vis_params.get("caption", unit_label)
        pal = vis_params.get("palette", ["#FFF", "#000"])
        cbar = _make_compact_colorbar(pal, vis_params.get("min", 0), vis_params.get("max", 1), lbl)

        return png, jpg, cbar
    except Exception as e:
        st.error(f"Erro estático: {e}")
        return None, None, None

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, label: str) -> str:
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    
    try:
        N_STEPS = len(palette)
        boundaries = np.linspace(vmin, vmax, N_STEPS + 1)
        
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=N_STEPS)
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
                
        cb = ColorbarBase(
            ax, 
            cmap=cmap, 
            norm=norm, 
            boundaries=boundaries, 
            spacing='proportional', 
            orientation="horizontal"
        )
        
        cb.set_label(label, fontsize=7)
        locator = ticker.MaxNLocator(nbins=6)
        cb.locator = locator
                
        if (vmax - vmin) < 10:
            formatter = ticker.FormatStrFormatter('%.2f')
        else:
            formatter = ticker.FormatStrFormatter('%.0f')
            
        cb.formatter = formatter
        cb.update_ticks()
        cb.ax.tick_params(labelsize=6, length=2, pad=1)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", pad_inches=0.05, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('ascii')}"
        
    except Exception as e:
        st.error(f"Erro legenda: {e}")
        plt.close(fig)
        return None

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
