# ==================================================================================
# lightning_module.py
# Módulo independente para cálculo de densidade de raios (GOES-16/19 GLM)
# ==================================================================================
import ee

def get_lightning_config():
    """
    Retorna as configurações de visualização (cores, min, max) para este módulo.
    Assim você não suja o seu app.py com configurações de raios.
    """
    return {
        "min": 0,
        "max": 100, # Ajustável: representa qtde de flashes no período
        "palette": ['transparent', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#FFFFFF'],
        "caption": "Densidade de Raios (Total de Flashes)"
    }

def compute_lightning_density(roi: ee.Geometry, start_date: str, end_date: str) -> ee.Image:
    """
    Busca, funde e processa dados de raios do GOES-16 e GOES-19.
    Retorna uma imagem pronta para ser plotada no mapa.
    """
    
    # 1. Definição das Coleções (Tentativa de buscar ambas)
    # A coleção LCFA (Lightning Cast Flash Area) contém eventos de raios
    
    # Coleção GOES-16 (Histórico/Atual East)
    glm_16 = ee.ImageCollection('NOAA/GOES/16/GLM/L2/LCFA') \
        .filterDate(start_date, end_date) \
        .filterBounds(roi)

    # Coleção GOES-17/18 (West) - Opcional, caso queira cobrir oeste da AM
    # glm_west = ee.ImageCollection('NOAA/GOES/17/GLM/L2/LCFA')...

    # Coleção GOES-19 (Novo East)
    # Nota: Se o ID exato '19' ainda não estiver indexado publicamente no GEE,
    # o código segue rodando apenas com o 16 sem quebrar.
    try:
        glm_19 = ee.ImageCollection('NOAA/GOES/19/GLM/L2/LCFA') \
            .filterDate(start_date, end_date) \
            .filterBounds(roi)
        
        # Funde as coleções se ambas existirem
        glm_combined = glm_16.merge(glm_19)
    except:
        # Fallback: Se der erro ao chamar o 19, usa só o 16
        glm_combined = glm_16

    # 2. Processamento (Redução)
    # A banda 'flash_area' possui valores onde houve raio.
    # Criamos uma máscara binária (1 onde tem raio, 0 onde não tem)
    def map_flashes(image):
        # gt(0) retorna 1 se houve flash, 0 se não.
        return image.select('flash_area').gt(0).unmask(0).rename('flash_count')

    # Somamos todos os "1s" ao longo do tempo selecionado
    lightning_sum = glm_combined.map(map_flashes).sum().clip(roi)
    
    # 3. Limpeza Visual
    # Mascaramos o valor 0 para ficar transparente no mapa (não cobrir o satélite de fundo)
    lightning_final = lightning_sum.updateMask(lightning_sum.gt(0))

    return lightning_final

def get_lightning_chart_data(roi: ee.Geometry, start_date: str, end_date: str):
    """
    (Opcional) Se quiser gerar gráfico de linha temporal de raios no futuro.
    """
    # Lógica similar à de cima, mas retornando FeatureCollection para gráfico
    pass