# ==================================================================================
# map_visualizer.py — Funções de visualização do Clima-Cast-Crepaldi
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

# ==================================================================================
# MAPA: CÍRCULO
# ==================================================================================
def display_circle_map(latitude, longitude, radius_km):
    """Exibe um mapa de conferência interativo com fundo de satélite."""
    st.subheader("Mapa de Conferência: Círculo")
    mapa = geemap.Map(center=[latitude, longitude], zoom=11)
    mapa.add_basemap('SATELLITE')
    
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


# ==================================================================================
# MAPA: BASE COM LATITUDE E LONGITUDE (SEM GEE)
# ==================================================================================
def display_latlon_map(lat_min=-23.5, lat_max=-14.5, lon_min=-52, lon_max=-39):
    """
    Exibe um mapa simples com linhas de latitude e longitude.
    Útil para conferência rápida da área sem depender do Google Earth Engine.

    Parâmetros
    ----------
    lat_min, lat_max : float
        Limites de latitude da área (graus decimais)
    lon_min, lon_max : float
        Limites de longitude da área (graus decimais)
    """
    try:
        # Geração da grade de coordenadas
        lon = np.linspace(lon_min, lon_max, 8)
        lat = np.linspace(lat_min, lat_max, 6)

        fig, ax = plt.subplots(figsize=(8, 6))

        # Desenhar linhas verticais (longitudes)
        for l in lon:
            ax.plot([l, l], [lat_min, lat_max], color='lightgray', linestyle='--', linewidth=0.8)
        # Desenhar linhas horizontais (latitudes)
        for l in lat:
            ax.plot([lon_min, lon_max], [l, l], color='lightgray', linestyle='--', linewidth=0.8)

        # Configurações visuais
        ax.set_xticks(lon)
        ax.set_yticks(lat)
        ax.set_xlabel("Longitude (°)")
        ax.set_ylabel("Latitude (°)")
        ax.set_title("Mapa Base – Coordenadas Geográficas de Minas Gerais", fontsize=13, weight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        # Exibir no Streamlit
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        st.image(buf, caption="Mapa simples com coordenadas geográficas", use_container_width=True)
        plt.close(fig)

    except Exception as e:
        st.error(f"❌ Erro ao gerar o mapa de lat/lon: {e}")


# ==================================================================================
# MAPA: POLÍGONO DESENHADO
# ==================================================================================
def display_polygon_draw_map():
    """Exibe um mapa interativo com ferramentas de desenho compatível com várias versões do st_folium."""
    st.subheader("Mapa de Conferência: Polígono")

    mapa = geemap.Map(center=[-15, -55], zoom=4)
    mapa.add_basemap('SATELLITE')

    st.info("Use as ferramentas de desenho no canto esquerdo do mapa. Após desenhar, clique em 'Validar Área'.")

    # Renderiza o mapa e captura o retorno
    output = st_folium(mapa, height=500, width="100%")

    # Detecta o formato correto do retorno
    drawn_geom = None
    if output:
        if "all_drawings" in output and output["all_drawings"]:
            drawn_geom = output["all_drawings"][-1].get("geometry")
        elif "last_active_drawing" in output and output["last_active_drawing"]:
            drawn_geom = output["last_active_drawing"].get("geometry")
        elif "last_drawn" in output and output["last_drawn"]:
            drawn_geom = output["last_drawn"].get("geometry")

    # Atualiza o estado da sessão
    if drawn_geom:
        st.session_state["drawn_geometry"] = drawn_geom
        st.success("✅ Polígono capturado com sucesso! Agora você pode validar a área.")
    else:
        if "drawn_geometry" in st.session_state:
            del st.session_state["drawn_geometry"]
        st.warning("Nenhum polígono foi desenhado até o momento.")


# ==================================================================================
# COLORBAR
# ==================================================================================
def create_colorbar(vis_params, unit_label=""):
    """Cria uma imagem de colorbar horizontal com um gradiente contínuo."""
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


# ==================================================================================
# MAPA ESTÁTICO (ERA5-LAND)
# ==================================================================================
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib import patheffects

def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """
    Gera URLs para o mapa estático (PNG/JPG) e uma imagem da colorbar correspondente.
    """
    if ee_image is None or feature is None:
        st.error("❌ Imagem ou geometria ausente. Verifique se a área foi validada e o período contém dados.")
        return None, None, None

    try:
        region = feature.geometry().bounds()
        background = ee.Image(1).visualize(palette=['ffffff'], min=0, max=1)
        outline = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        final_image = background.blend(ee_image.visualize(**vis_params)).blend(outline)

        png_url = final_image.getThumbURL({'region': region.getInfo()['coordinates'], 'dimensions': 512, 'format': 'png'})
        jpg_url = final_image.getThumbURL({'region': region.getInfo()['coordinates'], 'dimensions': 1024, 'format': 'jpg'})
        colorbar_img = create_colorbar(vis_params, unit_label)

        if not png_url or not jpg_url:
            st.error("⚠️ Erro: o Google Earth Engine não retornou as URLs do mapa. Tente outro período ou variável.")
            return None, None, None

        return png_url, jpg_url, colorbar_img

    except Exception as e:
        st.error(f"⚠️ Falha ao gerar o mapa estático: {e}")
        return None, None, None


# ==================================================================================
# MAPA INTERATIVO (ERA5-LAND)
# ==================================================================================
def create_interactive_map(ee_image, feature, vis_params, unit_label=""):
    """Gera e exibe um mapa interativo com a legenda padrão do geemap."""
    centroid = feature.geometry().centroid(maxError=1).getInfo()['coordinates']
    centroid.reverse()
    mapa = geemap.Map(center=centroid, zoom=7)
    mapa.add_basemap('SATELLITE')
    mapa.addLayer(ee_image, vis_params, 'Dados Climáticos')
    mapa.addLayer(ee.Image().paint(feature, 0, 2), {'palette': 'black'}, 'Contorno da Área')
    mapa.add_colorbar(vis_params, label=unit_label, layer_name='Dados Climáticos')
    mapa.to_streamlit(height=500)
