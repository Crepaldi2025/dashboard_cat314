# ==================================================================================
# map_visualizer.py
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import ee
import io
import base64
import requests
from PIL import Image, ImageDraw, ImageFont 
import numpy as np
import matplotlib.ticker as ticker
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 
import folium 
import gee_handler # Para pegar configurações de visualização

# ------------------------------------------------------------------
# 0. MAPA DE SOBREPOSIÇÃO (OVERLAY) - NOVO
# ------------------------------------------------------------------

def create_overlay_map(img1: ee.Image, name1: str, img2: ee.Image, name2: str, feature: ee.Feature):
    try:
        coords = feature.geometry().bounds().getInfo()['coordinates'][0]
        lon_min, lat_min = coords[0][0], coords[0][1]
        lon_max, lat_max = coords[2][0], coords[2][1]
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        centro = feature.geometry().centroid(maxError=1).getInfo()['coordinates'] 
        lon_c, lat_c = centro[0], centro[1]
    except Exception:
        bounds = None
        lat_c, lon_c = -15.78, -47.93

    mapa = geemap.Map(center=[lat_c, lon_c], zoom=4, add_google_map=False, tiles=None)
    
    esri_layer = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    )
    esri_layer.add_to(mapa)

    vis1 = gee_handler.obter_vis_params_interativo(name1)
    vis2 = gee_handler.obter_vis_params_interativo(name2)

    # Camada Base (Opaca)
    mapa.addLayer(img1, vis1, f"Base: {name1}")
    
    # Camada Topo (Transparente)
    mapa.addLayer(img2, vis2, f"Topo: {name2}", opacity=0.6)

    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "red"}, "Contorno")
    
    # Adiciona a legenda da camada superior
    _add_colorbar_bottomleft(mapa, vis2, name2)

    if bounds:
        mapa.fit_bounds(bounds)
    
    mapa.to_streamlit(height=600, use_container_width=True)

# ------------------------------------------------------------------
# 1. MAPA INTERATIVO
# ------------------------------------------------------------------

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = ""):
    try:
        coords = feature.geometry().bounds().getInfo()['coordinates'][0]
        lon_min, lat_min = coords[0][0], coords[0][1]
        lon_max, lat_max = coords[2][0], coords[2][1]
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        centro = feature.geometry().centroid(maxError=1).getInfo()['coordinates'] 
        lon_c, lat_c = centro[0], centro[1]
    except Exception:
        bounds = None
        lat_c, lon_c = -15.78, -47.93

    mapa = geemap.Map(center=[lat_c, lon_c], zoom=4, add_google_map=False, tiles=None)
    
    esri_layer = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    )
    esri_layer.add_to(mapa)

    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "red"}, "Contorno")
    
    tipo_local = st.session_state.get('tipo_localizacao', '')
    if tipo_local == "Círculo (Lat/Lon/Raio)":
        folium.Marker(
            location=[lat_c, lon_c],
            tooltip=f"Centro: {lat_c:.4f}, {lon_c:.4f}",
            popup=folium.Popup(f"<b>Centro</b><br>Lat: {lat_c:.5f}<br>Lon: {lon_c:.5f}", max_width=200),
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(mapa)
    
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    if bounds:
        mapa.fit_bounds(bounds)
    
    mapa.to_streamlit(height=500, use_container_width=True)

# ------------------------------------------------------------------
# 2. MAPA ESTÁTICO
# ------------------------------------------------------------------

def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    try:
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        outline_vis = outline.visualize(palette='000000')
        final = visualized_data.blend(outline_vis)

        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1])) * 111000 
            region = feature.geometry().buffer(dim * 0.05)
        except: region = feature.geometry()

        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img_bytes = requests.get(url).content
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        
        tipo_local = st.session_state.get('tipo_localizacao', '')
        if tipo_local == "Círculo (Lat/Lon/Raio)":
            try:
                centro = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
                lon_txt, lat_txt = centro[0], centro[1]
                draw = ImageDraw.Draw(img)
                w, h = img.size
                cx, cy = w / 2, h / 2
                r = 5
                draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="black", outline="white", width=1)
                
                try: font = ImageFont.truetype("arial.ttf", 24)
                except: 
                    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                    except: font = ImageFont.load_default()

                texto = f"lat={lat_txt:.4f}\nlon={lon_txt:.4f}"
                tx, ty = cx + 12, cy - 25
                draw.text((tx-2, ty), texto, font=font, fill="white")
                draw.text((tx+2, ty), texto, font=font, fill="white")
                draw.text((tx, ty-2), texto, font=font, fill="white")
                draw.text((tx, ty+2), texto, font=font, fill="white")
                draw.text((tx, ty), texto, font=font, fill="black")
            except Exception as e: print(f"Erro desenho: {e}")

        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf = io.BytesIO()
        bg.convert('RGB').save(buf, format="JPEG")
        jpg = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        
        buf_png = io.BytesIO()
        img.save(buf_png, format="PNG")
        png = f"data:image/png;base64,{base64.b64encode(buf_png.getvalue()).decode('ascii')}"

        lbl = vis_params.get("caption", unit_label)
        pal = vis_params.get("palette", ["#FFF", "#000"])
        cbar = _make_compact_colorbar(pal, vis_params.get("min", 0), vis_params.get("max", 1), lbl)

        return png, jpg, cbar
    except Exception as e:
        st.error(f"Erro estático: {e}")
        return None, None, None

# ------------------------------------------------------------------
# 3. FUNÇÕES AUXILIARES
# ------------------------------------------------------------------

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette: return 
    N_STEPS = len(palette) 
    index = np.linspace(vmin, vmax, N_STEPS + 1).tolist()
    fmt = '%.2f' if (vmax - vmin) < 10 else '%.0f'
    colormap = StepColormap(colors=palette, index=index, vmin=vmin, vmax=vmax)
    colormap.fmt = fmt
    colormap.caption = vis_params.get("caption", unit_label)
    html = colormap._repr_html_()
    template = Template(f"""{{% macro html(this, kwargs) %}}<div style="position: fixed; bottom: 12px; left: 12px; z-index: 9999; background: rgba(255,255,255,0.85); padding: 6px 8px; border-radius: 6px; box_shadow: 0 1px 4px rgba(0,0,0,0.3);">{html}</div>{{% endmacro %}}""")
    macro = MacroElement()
    macro._template = template
    mapa.get_root().add_child(macro)

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, label: str) -> str:
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    try:
        N_STEPS = len(palette)
        boundaries = np.linspace(vmin, vmax, N_STEPS + 1)
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=N_STEPS)
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
        cb = ColorbarBase(ax, cmap=cmap, norm=norm, boundaries=boundaries, spacing='proportional', orientation="horizontal")
        cb.set_label(label, fontsize=7)
        cb.locator = ticker.MaxNLocator(nbins=6)
        formatter = ticker.FormatStrFormatter('%.2f' if (vmax - vmin) < 10 else '%.0f')
        cb.formatter = formatter
        cb.update_ticks()
        cb.ax.tick_params(labelsize=6, length=2, pad=1)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", pad_inches=0.05, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('ascii')}"
    except: return None

def _make_title_image(title_text: str, width: int, height: int = 50) -> bytes:
    try:
        fig = plt.figure(figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('white')
        plt.text(0.5, 0.5, title_text, ha='center', va='center', fontsize=14, fontweight='bold', wrap=True)
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0.05, facecolor='white')
        plt.close(fig)
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
