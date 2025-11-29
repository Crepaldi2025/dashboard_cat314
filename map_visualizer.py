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
from matplotlib import cm
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 
import folium

# ---------------
# MAPA INTERATIVO
# ---------------

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = ""):
    try:
        coords = feature.geometry().bounds().getInfo()['coordinates'][0]
        lon_min = coords[0][0]
        lat_min = coords[0][1]
        lon_max = coords[2][0]
        lat_max = coords[2][1]
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        
        # Centro
        centro = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
        lon_c, lat_c = centro[0], centro[1]
    except Exception:
        bounds = None
        lat_c, lon_c = -15.78, -47.93

    # 1. Cria o mapa SEM basemap definido (para não dar erro de chave/BoxKeyError)
    mapa = geemap.Map(center=[lat_c, lon_c], zoom=4)
    
    # 2. Adiciona o Fundo ESRI WORLD IMAGERY manualmente (Satélite Verde Escuro)
    mapa.add_tile_layer(
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="Esri World Imagery",
        attribution="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    )

    # 3. Adiciona Dados e Contorno
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "black"}, "Contorno")
    
    # 4. Lógica do Marcador (Apenas para Círculo)
    tipo_local = st.session_state.get('tipo_localizacao', '')
    if tipo_local == "Círculo (Lat/Lon/Raio)":
        folium.Marker(
            location=[lat_c, lon_c],
            tooltip=f"Centro: {lat_c:.4f}, {lon_c:.4f}",
            popup=folium.Popup(f"<b>Centro da Área</b><br>Lat: {lat_c:.5f}<br>Lon: {lon_c:.5f}", max_width=200),
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(mapa)
    
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    if bounds:
        mapa.fit_bounds(bounds)
    
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
    try:
        # 1. Dados
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        
        # 2. Contorno
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        outline_vis = outline.visualize(palette='000000')
        
        # Composição Base
        final = visualized_data.blend(outline_vis)

        # 3. Lógica do Ponto Vermelho (Apenas para Círculo)
        tipo_local = st.session_state.get('tipo_localizacao', '')
        if tipo_local == "Círculo (Lat/Lon/Raio)":
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            width_deg = abs(b[2][0] - b[0][0]) 
            radius_m = max(50, (width_deg * 111000) * 0.015)

            center_geom = feature.geometry().centroid(maxError=1).buffer(radius_m)
            center_feat = ee.FeatureCollection([ee.Feature(center_geom)])
            center_vis = ee.Image().paint(center_feat, 0, 0).visualize(palette=['FF0000'])
            
            final = final.blend(center_vis)

        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1])) * 111000 
            region = feature.geometry().buffer(dim * 0.05)
        except: region = feature.geometry()

        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img_bytes = requests.get(url).content
        
        # Processamento seguro da imagem
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf = io.BytesIO()
        bg.convert('RGB').save(buf, format="JPEG")
        jpg = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        png = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('ascii')}"
        
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
