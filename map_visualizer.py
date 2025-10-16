# map_visualizer.py
import streamlit as st
import geemap.foliumap as geemap
import folium
import ee
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import io
from streamlit_folium import st_folium # <-- NOVA IMPORTAÇÃO

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
    
    mapa.add_marker(location=[latitude, longitude], popup="Centro da Area")
    mapa.to_streamlit(height=400)

# --- INÍCIO DA ATUALIZAÇÃO ---
def display_polygon_draw_map():
    """Exibe um mapa interativo com ferramentas de desenho usando st_folium."""
    st.subheader("Mapa de Conferência: Polígono")
    
    mapa = geemap.Map(center=[-15, -55], zoom=4)
    mapa.add_basemap('SATELLITE')
    
    st.info("Utilize as ferramentas de desenho no canto esquerdo do mapa para criar seu polígono. Após desenhar, clique em 'Validar Área'.")
    
    # Usa st_folium para renderizar o mapa e capturar o output
    output = st_folium(mapa, height=500, width="100%")

    # Verifica se o usuário desenhou algo e salva a geometria no estado da sessão
    if output and output.get("last_drawn") and output["last_drawn"].get("geometry"):
        st.session_state['drawn_geometry'] = output["last_drawn"]["geometry"]
    else:
        # Garante que geometrias antigas sejam limpas se nada for desenhado
        if 'drawn_geometry' in st.session_state:
            del st.session_state['drawn_geometry']
# --- FIM DA ATUALIZAÇÃO ---

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

def create_static_map(ee_image, feature, vis_params, unit_label=""):
    """Gera URLs para o mapa estático (PNG/JPG) e uma imagem da colorbar."""
    try:
        region = feature.geometry().bounds()
        background = ee.Image(1).visualize(palette=['ffffff'], min=0, max=1)
        outline = ee.Image().byte().paint(featureCollection=feature, color=1, width=2)
        final_image = background.blend(ee_image.visualize(**vis_params)).blend(outline)
        png_url = final_image.getThumbURL({'region': region.getInfo()['coordinates'], 'dimensions': 512, 'format': 'png'})
        jpg_url = final_image.getThumbURL({'region': region.getInfo()['coordinates'], 'dimensions': 1024, 'format': 'jpg'})
        colorbar_img = create_colorbar(vis_params, unit_label)
        return png_url, jpg_url, colorbar_img
    except Exception as e:
        st.error(f"Erro ao gerar a imagem do mapa: {e}")
        return None, None, None

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