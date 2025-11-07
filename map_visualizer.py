# ==================================================================================
# map_visualizer.py
# 
# Módulo: Clima-Cast-Crepaldi
# Autor: Paulo C. Crepaldi
#
# Descrição:
# (v29) - Atualiza as funções de colorbar para renderização discreta (10 passos).
#       - Importa `StepColormap` (para interativo) e `mcolors` (para estático).
#       - Remove a lógica de 'ticks' antiga de `create_static_map`.
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import ee
import io
import base64
import requests
from PIL import Image
import numpy as np # <-- ADICIONADO para linspace
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.colorbar import ColorbarBase
from matplotlib import cm
import matplotlib.colors as mcolors # <-- ADICIONADO para BoundaryNorm

# --- INÍCIO DA CORREÇÃO v29 ---
from branca.colormap import StepColormap # <-- ADICIONADO para legenda discreta
# --- FIM DA CORREÇÃO v29 ---


# ==================================================================================
# MAPA INTERATIVO (Resultado da Análise)
# ==================================================================================

def create_interactive_map(ee_image: ee.Image, 
                           feature: ee.Feature, 
                           vis_params: dict, 
                           unit_label: str = ""):
    """
    Cria e exibe um mapa interativo com os dados do GEE e o contorno da área.
    """
    try:
        centroid = feature.geometry().centroid(maxError=1).getInfo()["coordinates"]
        centroid.reverse()
        zoom = 7
    except Exception:
        centroid = [-15.78, -47.93] 
        zoom = 4

    mapa = geemap.Map(center=centroid, zoom=zoom, basemap="HYBRID")
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos")
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {"palette": "black"}, "Contorno da Área")
    
    # Atualizado para chamar a nova função de legenda discreta
    _add_colorbar_bottomleft(mapa, vis_params, unit_label)
    
    mapa.to_streamlit(height=500, use_container_width=True)


# ==================================================================================
# COLORBAR PARA MAPAS INTERATIVOS (Modificado)
# ==================================================================================

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str):
    """
    (v29) Função auxiliar interna para adicionar uma legenda (colorbar) 
    DISCRETA flutuante no canto inferior esquerdo.
    """
    from branca.element import Template, MacroElement
    
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    
    if not palette or len(palette) == 0:
        return 

    # --- INÍCIO DA CORREÇÃO v29 ---
    # Gera 11 valores (para 10 intervalos) entre o min e o max
    N_STEPS = len(palette) # O número de passos é definido pelo n° de cores
    index = np.linspace(vmin, vmax, N_STEPS + 1)
    
    # Usa StepColormap em vez de LinearColormap
    colormap = StepColormap(
        colors=palette, 
        index=index, 
        vmin=vmin, 
        vmax=vmax
    )
    # --- FIM DA CORREÇÃO v29 ---

    # Formata a etiqueta da legenda
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
    
    # HTML/CSS para posicionar a legenda
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
# COLORBAR COMPACTA (MAPA ESTÁTICO) (Modificado)
# ==================================================================================

def _make_compact_colorbar(palette: list, vmin: float, vmax: float, 
                           label: str) -> str:
    """
    (v29) Função auxiliar interna para gerar uma imagem de legenda (colorbar) 
    horizontal DISCRETA usando Matplotlib.

    Args:
        palette (list): A lista de 10 cores.
        vmin (float): O valor mínimo da escala.
        vmax (float): O valor máximo da escala.
        label (str): A etiqueta da unidade (ex: "Temperatura (°C)").

    Returns:
        str: Uma string de Data URL (base64) da imagem PNG da legenda.
    """
    fig = plt.figure(figsize=(3.6, 0.35), dpi=220)
    ax = fig.add_axes([0.05, 0.4, 0.90, 0.35])
    
    # --- INÍCIO DA CORREÇÃO v29 ---
    try:
        N_STEPS = len(palette)
        # Cria os 11 limites (boundaries) para os 10 intervalos
        boundaries = np.linspace(vmin, vmax, N_STEPS + 1)
        
        # Cria o colormap discreto
        cmap = LinearSegmentedColormap.from_list("custom", palette, N=N_STEPS)
        
        # Cria a normalização discreta
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
        
    except Exception as e:
        st.error(f"Erro ao criar colormap: {e}")
        plt.close(fig)
        return None

    # Gera a colorbar usando a normalização discreta
    cb = ColorbarBase(
        ax, 
        cmap=cmap, 
        norm=norm, 
        boundaries=boundaries,
        ticks=boundaries, # Define os ticks nos limites
        spacing='proportional',
        orientation="horizontal"
    )
    # --- FIM DA CORREÇÃO v29 ---
        
    cb.set_label(label, fontsize=7)
    # Formata os ticks para serem legíveis (ex: 500.0 -> 500)
    cb.ax.set_xticklabels([f'{t:g}' for t in boundaries])
    cb.ax.tick_params(labelsize=6, length=2, pad=1)
    
    # Salva a figura em um buffer de bytes em memória
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=220, bbox_inches="tight", pad_inches=0.05, transparent=True)
    plt.close(fig)
    buf.seek(0)
    
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ==================================================================================
# MAPA ESTÁTICO — GERAÇÃO DE IMAGENS (Modificado)
# ==================================================================================

def create_static_map(ee_image: ee.Image, 
                      feature: ee.Feature, 
                      vis_params: dict, 
                      unit_label: str = "") -> tuple[str, str, str]:
    """
    Gera o mapa estático (PNG/JPG) e a legenda (colorbar) discreta.
    """
    try:
        # Lógica de mesclagem (v17) - Idêntica
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

        # ===============================================
        # 7. Geração da Colorbar (Legenda)
        # ===============================================
        
        palette = vis_params.get("palette", ["#FFFFFF", "#000000"])
        vmin = vis_params.get("min", 0)
        vmax = vis_params.get("max", 1)
        label = unit_label or ""
        
        # --- INÍCIO DA CORREÇÃO v29 ---
        # REMOVIDA a lógica antiga de 'ticks'
        # A nova função _make_compact_colorbar agora cuida dos ticks.
        # --- FIM DA CORREÇÃO v29 ---
        
        colorbar_img = _make_compact_colorbar(palette, vmin, vmax, label)

        return png_url, jpg_url, colorbar_img

    except Exception as e:
        st.error(f"Erro ao gerar mapa estático: {e}")
        return None, None, None
