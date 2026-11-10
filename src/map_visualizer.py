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
from src import gee_handler

# ------------------------------------------------------------------
# 0. MAPA DE SOBREPOSIÇÃO (OVERLAY + SPLIT MAP)
# ------------------------------------------------------------------

def create_overlay_map(img1, name1, img2, name2, feature, opacity1=1.0, opacity2=0.6, mode="Transparência"):
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
    
    # Base ESRI
    esri_layer = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    )
    esri_layer.add_to(mapa)

    vis1 = gee_handler.obter_vis_params_interativo(name1)
    vis2 = gee_handler.obter_vis_params_interativo(name2)

    # Lógica do Split Map (Cortina)
    if mode == "Split Map (Cortina)":
        left_layer = geemap.ee_tile_layer(img1, vis1, name=f"Esq: {name1}")
        right_layer = geemap.ee_tile_layer(img2, vis2, name=f"Dir: {name2}")
        
        mapa.split_map(left_layer=left_layer, right_layer=right_layer)
        
        _add_colorbar_bottomleft(mapa, vis1, f"Esq: {name1}", index=0)
        _add_colorbar_bottomleft(mapa, vis2, f"Dir: {name2}", index=1)

    else:
        # Modo Transparência (Tradicional)
        mapa.addLayer(img1, vis1, f"Base: {name1}", opacity=opacity1)
        mapa.addLayer(img2, vis2, f"Topo: {name2}", opacity=opacity2)
        
        _add_colorbar_bottomleft(mapa, vis1, f"Base: {name1}", index=0)
        _add_colorbar_bottomleft(mapa, vis2, f"Topo: {name2}", index=1)

    # Contorno sempre visível
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "red"}, "Contorno")

    if bounds:
        mapa.fit_bounds(bounds)
    
    mapa.to_streamlit(height=500, use_container_width=True)

# ------------------------------------------------------------------
# 1. MAPA INTERATIVO PADRÃO
# ------------------------------------------------------------------

def create_interactive_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "", opacity: float = 1.0):
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
        attr="Tiles &copy; Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    )
    esri_layer.add_to(mapa)

    # Adiciona a camada com a opacidade correta
    mapa.addLayer(ee_image, vis_params, "Dados Climáticos", opacity=opacity)
    
    mapa.addLayer(ee.Image().paint(ee.FeatureCollection([feature]), 0, 2), {"palette": "red"}, "Contorno")
    
    tipo_local = st.session_state.get('tipo_localizacao', '')
    if tipo_local == "Círculo (Lat/Lon/Raio)":
        folium.Marker(
            location=[lat_c, lon_c],
            tooltip=f"Centro: {lat_c:.2f}, {lon_c:.2f}",
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


def _add_vertical_colorbar(img, palette, vmin, vmax, unit):
    """Acrescenta uma legenda vertical fora da área do mapa."""

    from matplotlib import ticker

    cmap = LinearSegmentedColormap.from_list(
        "climacast_vertical", palette, N=256
    )
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig = plt.figure(figsize=(1.1, 3.0), dpi=150)
    fig.patch.set_alpha(0)

    ax = fig.add_axes([0.22, 0.12, 0.18, 0.77])

    cb = ColorbarBase(
        ax,
        cmap=cmap,
        norm=norm,
        orientation="vertical"
    )

    cb.locator = ticker.MaxNLocator(
        nbins=6,
        steps=[1, 2, 2.5, 5, 10]
    )
    cb.update_ticks()

    cb.ax.yaxis.set_minor_locator(ticker.NullLocator())

    cb.ax.tick_params(
        which="major",
        labelsize=10,
        length=3,
        width=0.8
    )

    amplitude = vmax - vmin
    formato = "%.1f" if amplitude < 10 else "%.0f"

    cb.ax.yaxis.set_major_formatter(
        ticker.FormatStrFormatter(formato)
    )

    cb.ax.set_title(unit, fontsize=11, pad=10)
    cb.outline.set_linewidth(0.8)

    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        transparent=True,
        dpi=150
    )
    plt.close(fig)

    buffer.seek(0)
    legenda = Image.open(buffer).convert("RGBA")

    altura = max(1, int(img.height * 0.75))
    largura = max(
        1, round(legenda.width * altura / legenda.height)
    )

    legenda = legenda.resize(
        (largura, altura),
        Image.Resampling.LANCZOS
    )

    margem = 12
    largura_painel = largura + 2 * margem

    resultado = Image.new(
        "RGBA",
        (img.width + largura_painel, img.height),
        (255, 255, 255, 255)
    )

    resultado.paste(img, (0, 0), img)

    pos_x = img.width + margem
    pos_y = (img.height - altura) // 2

    resultado.paste(
        legenda,
        (pos_x, pos_y),
        legenda
    )

    return resultado


def create_static_map(ee_image: ee.Image, feature: ee.Feature, vis_params: dict, unit_label: str = "") -> tuple[str, str, str]:
    try:
        visualized_data = ee_image.visualize(min=vis_params["min"], max=vis_params["max"], palette=vis_params["palette"])
        outline = ee.Image().paint(featureCollection=ee.FeatureCollection([feature]), color=0, width=2)
        outline_vis = outline.visualize(palette='000000')
        final = visualized_data.blend(outline_vis)

        try:
            b = feature.geometry().bounds().getInfo()['coordinates'][0]
            dim = max(abs(b[2][0]-b[0][0]), abs(b[2][1]-b[0][1])) * 111000 
            region = feature.geometry().buffer(dim * 0.01)
        except: region = feature.geometry()

        # Dimensions controla a resolução da imagem gerada
        url = final.getThumbURL({"region": region, "dimensions": 400, "format": "png"})
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
                
                try: font = ImageFont.truetype("arial.ttf", 14)
                except: 
                    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                    except: font = ImageFont.load_default()

                texto = f"lat={lat_txt:.2f}\nlon={lon_txt:.2f}"
                tx, ty = cx + 12, cy - 25
                draw.text((tx-2, ty), texto, font=font, fill="white")
                draw.text((tx+2, ty), texto, font=font, fill="white")
                draw.text((tx, ty-2), texto, font=font, fill="white")
                draw.text((tx, ty+2), texto, font=font, fill="white")
                draw.text((tx, ty), texto, font=font, fill="black")
            except Exception as e: print(f"Erro desenho: {e}")

        
        # Legenda vertical integrada à imagem
        pal = vis_params.get(
            "palette", ["#FFFFFF", "#000000"]
        )

        vmin = float(vis_params.get("min", 0))
        vmax = float(vis_params.get("max", 1))

        unidade = unit_label or ""

        img = _add_vertical_colorbar(
            img,
            pal,
            vmin,
            vmax,
            unidade
        )

        # JPEG com fundo branco
        bg = Image.new("RGBA", img.size, "WHITE")
        bg.paste(img, (0, 0), img)

        buf_jpg = io.BytesIO()
        bg.convert("RGB").save(
            buf_jpg,
            format="JPEG",
            quality=95
        )

        jpg = (
            "data:image/jpeg;base64,"
            + base64.b64encode(
                buf_jpg.getvalue()
            ).decode("ascii")
        )

        # PNG com legenda incorporada
        buf_png = io.BytesIO()
        img.save(buf_png, format="PNG")

        png = (
            "data:image/png;base64,"
            + base64.b64encode(
                buf_png.getvalue()
            ).decode("ascii")
        )

        # Não há legenda horizontal separada
        cbar = None

        return png, jpg, cbar

    except Exception as e:
        st.error(f"Erro estático: {e}")
        return None, None, None

# ------------------------------------------------------------------
# 3. FUNÇÕES AUXILIARES
# ------------------------------------------------------------------

def _add_colorbar_bottomleft(mapa: geemap.Map, vis_params: dict, unit_label: str, index: int = 0):
    palette = vis_params.get("palette", None)
    vmin = vis_params.get("min", 0)
    vmax = vis_params.get("max", 1)
    if not palette: return 
    
    bottom_offset = 12 + (index * 60)
    N_STEPS = len(palette) 
    index_vals = np.linspace(vmin, vmax, N_STEPS + 1).tolist()
    fmt = '%.2f' if (vmax - vmin) < 10 else '%.0f'
    colormap = StepColormap(colors=palette, index=index_vals, vmin=vmin, vmax=vmax)
    colormap.fmt = fmt
    colormap.caption = vis_params.get("caption", unit_label)
    html = colormap._repr_html_()
    
    style = f"position: fixed; bottom: {bottom_offset}px; left: 12px; z-index: 9999; background: rgba(255,255,255,0.85); padding: 6px 8px; border-radius: 6px; box_shadow: 0 1px 4px rgba(0,0,0,0.3);"
    template = Template(f"""{{% macro html(this, kwargs) %}}<div style="{style}">{html}</div>{{% endmacro %}}""")
    macro = MacroElement()
    macro._template = template
    mapa.get_root().add_child(macro)


def _make_compact_colorbar(
    palette: list,
    vmin: float,
    vmax: float,
    label: str
) -> str:

    fig = plt.figure(figsize=(2.8, 0.55), dpi=220)
    ax = fig.add_axes([0.07, 0.48, 0.86, 0.22])

    try:
        # Escala contínua com interpolação entre as cores
        cmap = LinearSegmentedColormap.from_list(
            "climacast_continuous",
            palette,
            N=256
        )

        norm = mcolors.Normalize(
            vmin=vmin,
            vmax=vmax
        )

        cb = ColorbarBase(
            ax,
            cmap=cmap,
            norm=norm,
            orientation="horizontal"
        )

        # Valores principais arredondados
        locator = ticker.MaxNLocator(
            nbins=7,
            steps=[1, 2, 2.5, 5, 10]
        )

        ticks = locator.tick_values(vmin, vmax)
        ticks = ticks[
            (ticks >= vmin - 1e-9) &
            (ticks <= vmax + 1e-9)
        ]

        cb.set_ticks(ticks)

        cb.ax.xaxis.set_minor_locator(
            ticker.NullLocator()
        )

        # Formatação dos números
        amplitude = vmax - vmin

        if amplitude < 10:
            cb.ax.xaxis.set_major_formatter(
                ticker.FormatStrFormatter("%.2f")
            )
        else:
            cb.ax.xaxis.set_major_formatter(
                ticker.FormatStrFormatter("%.0f")
            )

        cb.ax.tick_params(
            axis="x",
            which="major",
            labelsize=6,
            length=3,
            width=0.7,
            pad=2
        )

        cb.ax.tick_params(
            axis="x",
            which="minor",
            bottom=False,
            top=False
        )

        cb.set_label(
            label,
            fontsize=8,
            labelpad=4
        )

        cb.outline.set_linewidth(0.8)

        buf = io.BytesIO()

        fig.savefig(
            buf,
            format="png",
            dpi=220,
            bbox_inches="tight",
            pad_inches=0.08,
            transparent=True
        )

        plt.close(fig)
        buf.seek(0)

        return (
            "data:image/png;base64,"
            + base64.b64encode(buf.read()).decode("ascii")
        )

    except Exception as e:
        plt.close(fig)
        st.error(f"Erro na barra de cores: {e}")
        return None



def _make_title_image(
    title_text: str,
    width: int,
    height: int = 90
) -> bytes:
    try:
        linhas = title_text.split("\n", 1)

        titulo = linhas[0].strip()
        subtitulo = (
            linhas[1].strip()
            if len(linhas) > 1 else ""
        )

        img = Image.new(
            "RGB", (width, height), "white"
        )
        draw = ImageDraw.Draw(img)

        fonte_path = (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        )
        fonte_bold_path = (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        )

        try:
            tamanho = 20

            while tamanho >= 12:
                fonte_titulo = ImageFont.truetype(
                    fonte_bold_path, tamanho
                )

                largura_texto = draw.textbbox(
                    (0, 0), titulo, font=fonte_titulo
                )[2]

                if largura_texto <= width - 40:
                    break

                tamanho -= 1

            fonte_subtitulo = ImageFont.truetype(
                fonte_path, 15
            )

        except OSError:
            fonte_titulo = ImageFont.load_default()
            fonte_subtitulo = ImageFont.load_default()

        cor_titulo = "#25364B"
        cor_subtitulo = "#64748B"

        draw.text(
            (width // 2, 18),
            titulo,
            font=fonte_titulo,
            fill=cor_titulo,
            anchor="mt"
        )

        if subtitulo:
            draw.text(
                (width // 2, 52),
                subtitulo,
                font=fonte_subtitulo,
                fill=cor_subtitulo,
                anchor="mt"
            )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return buffer.getvalue()

    except Exception as e:
        st.error(f"Erro ao gerar título: {e}")
        return None



def _stitch_images_to_bytes(
    title_bytes,
    map_bytes,
    colorbar_bytes,
    format="PNG"
):
    try:
        m = Image.open(
            io.BytesIO(map_bytes)
        ).convert("RGBA")

        partes = []

        if title_bytes:
            t = Image.open(
                io.BytesIO(title_bytes)
            ).convert("RGBA")
            partes.append(t)

        partes.append(m)

        if colorbar_bytes:
            c = Image.open(
                io.BytesIO(colorbar_bytes)
            ).convert("RGBA")
            partes.append(c)

        largura = m.width

        def redimensionar(im):
            if im.width == largura:
                return im
            altura = round(
                im.height * largura / im.width
            )
            return im.resize(
                (largura, altura),
                Image.Resampling.LANCZOS
            )

        partes = [redimensionar(p) for p in partes]

        altura_total = sum(p.height for p in partes)

        final = Image.new(
            "RGBA",
            (largura, altura_total),
            (255, 255, 255, 255)
        )

        y = 0
        for parte in partes:
            final.paste(parte, (0, y), parte)
            y += parte.height

        buf = io.BytesIO()

        if format.upper() == "JPEG":
            final.convert("RGB").save(
                buf, format="JPEG", quality=95
            )
        else:
            final.save(buf, format="PNG")

        return buf.getvalue()

    except Exception as e:
        st.error(f"Erro ao exportar mapa: {e}")
        return None
















