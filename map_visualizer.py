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
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
import matplotlib.colors as mcolors 
from branca.colormap import StepColormap 
from branca.element import Template, MacroElement 
import folium 

# ------------------------------------------------------------------
# 1. MAPA INTERATIVO (Geemap com Satélite Padrão)
# ------------------------------------------------------------------

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = ""):
    try:
        # Obtém limites para zoom
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

    # --- CRIAÇÃO DO MAPA (Geemap com Toolbar) ---
    # Não definimos 'basemap' aqui para evitar o BoxKeyError.
    mapa = geemap.Map(center=[lat_c, lon_c], zoom=4, add_google_map=False)
    
    # 1. Limpa o OpenStreetMap padrão (remove o fundo cinza/branco)
    mapa.clear_layers()
    
    # 2. Adiciona Satélite (Esri) manualmente como camada BASE
    esri_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    mapa.add_tile_layer(
        url=esri_url,
        name="Satélite (Esri)",
        attribution="Esri",
        shown=True
    )

    # 3. Adiciona Dados Climáticos (Overlay)
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    
    # 4. Adiciona Contorno
    try:
        outline = ee.Image().paint(ee.FeatureCollection([feature]), 0, 2)
        mapa.addLayer(outline, {"palette": "black"}, "Contorno")
    except: pass
    
    # --- Marcador (Apenas para Círculo) ---
    tipo_local = st.session_state.get('tipo_localizacao', '')
    if tipo_local == "Círculo (Lat/Lon/Raio)":
        folium.Marker(
            location=[lat_c, lon_c],
            tooltip=f"Centro: {lat_c:.4f}, {lon_c:.4f}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(mapa)
    
    # Legenda e Zoom
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)

    if bounds:
        mapa.fit_bounds(bounds)
    
    # Renderiza com a toolbar completa do geemap
    mapa.to_streamlit(height=500, use_container_width=True)

# ------------------------------------------------------------------
# 2. MAPA ESTÁTICO (Mantido igual - Funciona bem)
# ------------------------------------------------------------------

def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    try:
        # Visualização
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        final = visualized_data.blend(outline.visualize(palette='000000'))

        # Recorte
        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            region = feature.geometry().buffer(max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1])) * 5500)
        except: region = feature.geometry()

        # Download
        url = final.getThumbURL({"region": region, "dimensions": 800, "format": "png"})
        img = Image.open(io.BytesIO(requests.get(url).content)).convert("RGBA")
        
        # Desenho (Marcador no Estático)
        tipo_local = st.session_state.get('tipo_localizacao', '')
        if tipo_local == "Círculo (Lat/Lon/Raio)":
            try:
                centro = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
                draw = ImageDraw.Draw(img)
                w, h = img.size
                cx, cy = w / 2, h / 2
                
                # Bolinha
                draw.ellipse((cx-5, cy-5, cx+5, cy+5), fill="black", outline="white")
                
                # Texto
                try: font = ImageFont.truetype("arial.ttf", 24)
                except: font = ImageFont.load_default()
                
                texto = f"lat={centro[1]:.4f}\nlon={centro[0]:.4f}"
                # Contorno do texto
                for off in [(-2,0), (2,0), (0,-2), (0,2)]:
                    draw.text((cx+12+off[0], cy-25+off[1]), texto, font=font, fill="white")
                draw.text((cx+12, cy-25), texto, font=font, fill="black")
            except: pass

        # Conversão para JPEG/PNG de saída
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)
        
        buf_jpg = io.BytesIO()
        bg.convert('RGB').save(buf_jpg, format="JPEG")
        jpg_str = f"data:image/jpeg;base64,{base64.b64encode(buf_jpg.getvalue()).decode('ascii')}"
        
        buf_png = io.BytesIO()
        img.save(buf_png, format="PNG")
        png_str = f"data:image/png;base64,{base64.b64encode(buf_png.getvalue()).decode('ascii')}"

        # Legenda
        lbl = vis_params.get("caption", unit_label)
        pal = vis_params.get("palette", ["#FFF", "#000"])
        cbar = _make_compact_colorbar(pal, vis_params.get("min", 0), vis_params.get("max", 1), lbl)

        return png_str, jpg_str, cbar
    except Exception as e:
        st.error(f"Erro estático: {e}")
        return None, None, None

# ------------------------------------------------------------------
# 3. FUNÇÕES AUXILIARES (Legenda e Títulos)
# ------------------------------------------------------------------

def _add_colorbar_bottomleft(mapa, vis_params: dict, unit_label: str):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette: return 

    N_STEPS = len(palette) 
    index = np.linspace(vmin, vmax, N_STEPS + 1).tolist()
    fmt = '%.2f' if (vmax - vmin) < 10 else '%.0f'

    # Cria Colormap HTML
    colormap = StepColormap(colors=palette, index=index, vmin=vmin, vmax=vmax)
    colormap.fmt = fmt
    colormap.caption = vis_params.get("caption", unit_label)
    
    # Injeta HTML no mapa
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

def _make_compact_colorbar(palette, vmin, vmax, label):
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    try:
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=len(palette))
        norm = mcolors.BoundaryNorm(np.linspace(vmin, vmax, len(palette) + 1), cmap.N)
        cb = ColorbarBase(ax, cmap=cmap, norm=norm, orientation="horizontal")
        cb.set_label(label, fontsize=7)
        cb.ax.tick_params(labelsize=6)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", transparent=True)
        plt.close(fig)
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
    except: return None

def _make_title_image(text, width, height=50):
    fig = plt.figure(figsize=(width/100, height/100), dpi=100)
    plt.text(0.5, 0.5, text, ha='center', va='center', fontsize=14, fontweight='bold')
    plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return buf.getvalue()

def _stitch_images_to_bytes(title, map_img, cbar, format='PNG'):
    try:
        t = Image.open(io.BytesIO(title))
        m = Image.open(io.BytesIO(map_img))
        c = Image.open(io.BytesIO(cbar))
        w = m.width
        # Redimensiona mantendo proporção
        t = t.resize((w, int(t.height * w/t.width)))
        c = c.resize((w, int(c.height * w/c.width)))
        
        h = t.height + m.height + c.height
        final = Image.new('RGB', (w, h), (255, 255, 255))
        final.paste(t, (0, 0))
        final.paste(m, (0, t.height))
        final.paste(c, (0, t.height + m.height))
        
        buf = io.BytesIO()
        final.save(buf, format=format)
        return buf.getvalue()
    except: return None
