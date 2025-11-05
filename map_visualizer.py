# ==================================================================================
# map_visualizer.py — Versão final otimizada (Clima-Cast-Crepaldi)
# ==================================================================================
# Melhorias:
#   ✅ Compatível com Streamlit Cloud (sem dependência obrigatória de Cartopy)
#   ✅ Cache de mapas e colorbars (uso de @st.cache_resource / @st.cache_data)
#   ✅ Lazy loading de mapas interativos (geemap/folium)
#   ✅ Redução do tempo de carregamento inicial
# ==================================================================================

import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import io
from streamlit_folium import st_folium
import numpy as np

# ------------------------------------------------------------------------------
# Cartopy (opcional, usado apenas em execução local)
# ------------------------------------------------------------------------------
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib import patheffects
except ModuleNotFoundError:
    ccrs = None
    cfeature = None
    patheffects = None

# ------------------------------------------------------------------------------
# FUNÇÕES CACHEADAS — Criação e reuso de objetos pesados
# ------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _create_base_map(center, zoom, basemap='SATELLITE'):
    """Cria e retorna um mapa base do geemap cacheado."""
    mapa = geemap.Map(center=center, zoom=zoom)
    mapa.add_basemap(basemap)
    return mapa


@st.cache_data(show_spinner=False)
def create_colorbar(vis_params, unit_label=""):
    """Cria e cacheia a imagem de colorbar horizontal com gradiente contínuo."""
    fig, ax = plt.subplots(figsize=(6, 0.5))
    cmap = LinearSegmentedColormap.from_list("custom_gradient", vis_params['palette'])
    norm = matplotlib.colors.Normalize(vmin=vis_params['min'], vmax=vis_params['max'])
    cb = matplotlib.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')
    cb.set_label(unit_label, rotation=0, labelpad=5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()

# ------------------------------------------------------------------------------
# MAPA: CÍRCULO
# ------------------------------------------------------------------------------
def display_circle_map(latitude, longitude, radius_km):
    """Exibe um mapa de conferência interativo com fundo de satélite."""
    st.subheader("🗺️ Mapa de Conferência: Círculo")

    mapa = _create_base_map(center=[latitude, longitude], zoom=11)
    folium.Circle(
        location=[latitude, longitude],
        radius=radius_km * 1000,
        color="#ffc107",
        fill=True,
        fill_color="#ffc107",
        fill_opacity=0.3
    ).add_to(mapa)

    mapa.add_marker(location=[latitude, longitude], popup="Centro da Área")
    mapa.to_streamlit(height=400)

# ------------------------------------------------------------------------------
# MAPA: BASE COM LATITUDE E LONGITUDE (SEM GEE)
# ------------------------------------------------------------------------------
def display_latlon_map(lat_min=-23.5, lat_max=-14.5, lon_min=-52, lon_max=-39):
    """Exibe mapa simples com linhas de latitude/longitude (para conferência rápida)."""
    try:
        lon = np.linspace(lon_min, lon_max, 8)
        lat = np.linspace(lat_min, lat_max, 6)
        fig, ax = plt.subplots(figsize=(8, 6))

        for l in lon:
            ax.plot([l, l], [lat_min, lat_max], color='lightgray', linestyle='--', linewidth=0.8)
        for l in lat:
            ax.plot([lon_min, lon_max], [l, l], color='lightgray', linestyle='--', linewidth=0.8)

        ax.set_xticks(lon)
        ax.set_yticks(lat)
        ax.set_xlabel("Longitude (°)")
        ax.set_ylabel("Latitude (°)")
        ax.set_title("Mapa Base – Coordenadas Geográficas", fontsize=13, weight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        st.image(buf, caption="Mapa simples com coordenadas geográficas", use_container_width=True)
        plt.close(fig)
    except Exception as e:
        st.error(f"❌ Erro ao gerar o mapa de lat/lon: {e}")

# ------------------------------------------------------------------------------
# MAPA: POLÍGONO DESENHADO
# ------------------------------------------------------------------------------
def display_polygon_draw_map():
    """Exibe um mapa interativo com ferramentas de desenho compatível com st_folium."""
    st.subheader("🖊️ Mapa de Conferência: Polígono")

    mapa = _create_base_map(center=[-15, -55], zoom=4)
    st.info("Use as ferramentas de desenho no canto esquerdo do mapa. Após desenhar, clique em **Validar Área**.")

    output = st_folium(mapa, height=500, width="100%")
    drawn_geom = None

    if output:
        if "all_drawings" in output and output["all_drawings"]:
            drawn_geom = output["all_drawings"][-1].get("geometry")
        elif "last_active_drawing" in output and output["last_active_drawing"]:
            drawn_geom = output["last_active_drawing"].get("geometry")
        elif "last_drawn" in output and output["last_drawn"]:
            drawn_geom = output["last_drawn"].get("geometry")

    if drawn_geom:
        st.session_state["drawn_geometry"] = drawn_geom
        st.success("✅ Polígono capturado com sucesso! Agora você pode validar a área.")
    else:
        st.session_state.pop("drawn_geometry", None)
        st.warning("Nenhum polígono foi desenhado até o momento.")

# ------------------------------------------------------------------------------
# MAPA ESTÁTICO (ERA5-LAND)
# ------------------------------------------------------------------------------
def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera URLs para o mapa estático (PNG/JPG) e colorbar correspondente."""
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente. Verifique se a área foi validada e o período contém dados.")
        return None, None, None

    try:
        region = feature.geometry().bounds()
        background = ee.Image(1).visualize(palette=['ffffff'], min=0, max=1)
        outline = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        final_image = background.blend(ee_image.visualize(**vis_params)).blend(outline)

        png_url = final_image.getThumbURL({
            'region': region.getInfo()['coordinates'],
            'dimensions': 512,
            'format': 'png'
        })
        jpg_url = final_image.getThumbURL({
            'region': region.getInfo()['coordinates'],
            'dimensions': 1024,
            'format': 'jpg'
        })
        colorbar_img = create_colorbar(vis_params, unit_label)

        if not png_url or not jpg_url:
            st.error("⚠️ Erro: o GEE não retornou as URLs do mapa. Tente outro período ou variável.")
            return None, None, None

        return png_url, jpg_url, colorbar_img
    except Exception as e:
        st.error(f"⚠️ Falha ao gerar o mapa estático: {e}")
        return None, None, None

# ------------------------------------------------------------------------------
# MAPA INTERATIVO (ERA5-LAND)
# ------------------------------------------------------------------------------
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """
    Gera e exibe um mapa interativo leve e compatível com Streamlit Cloud,
    garantindo que a camada GEE fique visível sobre o basemap.
    """
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente.")
        return

    # 🔹 Calcula o centroide da geometria
    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()

    # 🔹 Cria o mapa base (sem camada inicial)
    mapa = geemap.Map(center=centroid, zoom=6)
    mapa.add_basemap('SATELLITE')

       # 🔹 Cria explicitamente o tile layer do GEE (garante renderização)
    try:
        # Cria camada a partir da imagem GEE
        layer = geemap.ee_tile_layer(ee_image, vis_params, name="Dados Climáticos")
        
        # Adiciona corretamente o TileLayer no mapa (folium)
        mapa.add_child(layer)

        # Adiciona contorno e legenda
        mapa.addLayer(ee.Image().paint(feature, 0, 2), {'palette': 'black'}, 'Contorno da Área')
        add_colorbar_with_background(mapa, vis_params, unit_label)

        # Exibe o mapa no Streamlit
        mapa.to_streamlit(height=550)

    except Exception as e:
        st.error(f"⚠️ Falha ao adicionar camada do GEE: {e}")

from branca.colormap import LinearColormap
from branca.element import Element

from branca.colormap import LinearColormap
from branca.element import Element

def add_colorbar_with_background(mapa, vis_params, unit_label=""):
    """
    Adiciona uma colorbar compacta e elegante no canto inferior esquerdo,
    com fundo branco translúcido e sombra suave.
    """
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
            bottom: 15px;
            left: 15px;
            background-color: rgba(255, 255, 255, 0.75);
            padding: 4px 7px;
            border-radius: 5px;
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

