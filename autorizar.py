import ee

# Inicializa explicitamente o projeto Earth Engine
ee.Initialize(project='gee-crepaldi-2025')

# Teste simples para confirmar a conexão
info = ee.Image('NASA/NASADEM_HGT/001').getInfo()
print("✅ Conexão estabelecida com sucesso!")
print("Imagem de teste:", info['id'])
