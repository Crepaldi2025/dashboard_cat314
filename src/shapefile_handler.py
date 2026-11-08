# ==================================================================================
# shapefile_handler.py
# ==================================================================================
import streamlit as st
import ee
import os
import tempfile
import zipfile
import json
import geopandas as gpd

def process_uploaded_shapefile(uploaded_file):
    """
    Processa o ZIP contendo Shapefile (Fazenda, Bacia, etc.), 
    simplifica a geometria e converte para EE.
    """
    if uploaded_file is None:
        return None, None

    try:
        # Cria diretório temporário
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "upload.zip")
            
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
            except zipfile.BadZipFile:
                st.error("O arquivo não é um ZIP válido.")
                return None, None
            
            # Procura o .shp
            shp_file = None
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    if f.lower().endswith(".shp"):
                        shp_file = os.path.join(root, f)
                        break
            
            if not shp_file:
                st.error("Nenhum arquivo .shp encontrado no ZIP.")
                return None, None

            # Lê com GeoPandas
            gdf = gpd.read_file(shp_file)
            if gdf.empty:
                st.error("Shapefile vazio.")
                return None, None

            # Garante projeção correta (Lat/Lon)
            if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            
            # Simplifica geometria (Essencial para não travar o GEE)
            # 0.005 graus ~ 500m de precisão (ajuste fino se necessário)
            gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005, preserve_topology=True)

            # Combina geometrias e pega o GeoJSON
            merged = gdf.unary_union
            geojson = json.loads(gpd.GeoSeries([merged]).to_json())
            coords = geojson['features'][0]['geometry']['coordinates']
            g_type = geojson['features'][0]['geometry']['type']

            if g_type == 'Polygon':
                ee_geom = ee.Geometry.Polygon(coords)
            elif g_type == 'MultiPolygon':
                ee_geom = ee.Geometry.MultiPolygon(coords)
            else:
                st.error(f"Geometria {g_type} não suportada.")
                return None, None
            
            # Label genérico para o mapa
            ee_feat = ee.Feature(ee_geom, {'label': 'Shapefile Personalizado'})
            
            return ee_geom, ee_feat

    except Exception as e:
        st.error(f"Erro ao processar Shapefile: {e}")
        return None, None
