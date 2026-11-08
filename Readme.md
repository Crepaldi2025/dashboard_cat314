# Clima-Cast-Crepaldi

Plataforma interativa para consulta, análise e visualização de dados meteorológicos históricos no Brasil, com foco didático e científico, integrando ERA5-Land via Google Earth Engine.

---

## Sobre o Aplicativo

O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido como parte do projeto da disciplina **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**, do curso de Ciências Atmosféricas da **Universidade Federal de Itajubá (UNIFEI)**. O aplicativo tem como propósito integrar dados meteorológicos provenientes de fontes de reanálise global e disponibilizá-los em uma plataforma visual, dinâmica e acessível, favorecendo tanto a análise científica quanto o uso didático.

## Objetivo

O principal objetivo do sistema é proporcionar uma interface intuitiva e interativa para consulta, análise e visualização de dados meteorológicos históricos dos municípios brasileiros, a partir da base de dados **ERA5-Land**, disponibilizada pelo **European Centre for Medium-Range Weather Forecasts (ECMWF)** por meio da plataforma **Google Earth Engine (GEE)**.

---

## Fontes de dados e plataformas

O Clima-Cast-Crepaldi utiliza diferentes fontes e ferramentas para obtenção, processamento e visualização de informações meteorológicas.

- **ERA5-Land (ECMWF/C3S):** produto de reanálise atmosférica de superfície terrestre, com resolução espacial aproximada de 9 km e disponibilidade temporal horária. É utilizado na análise de variáveis meteorológicas históricas e na elaboração de mapas e séries temporais.

- **Google Earth Engine (GEE):** plataforma de computação geoespacial em nuvem utilizada para acessar, processar e agregar os dados ERA5-Land nas regiões e nos períodos selecionados pelo usuário.

- **Open-Meteo:** plataforma de acesso a dados meteorológicos de modelos numéricos, utilizada para obter perfis verticais de temperatura, umidade e vento nos níveis de pressão disponíveis, empregados na construção dos diagramas Skew-T/log-P.

- **MetPy:** biblioteca científica Python utilizada no processamento termodinâmico dos perfis atmosféricos e no cálculo de parâmetros de estabilidade e instabilidade.

### Referências e documentação

- [ERA5-Land — ECMWF/Copernicus](https://doi.org/10.5194/essd-13-4349-2021)
- [ERA5-Land Hourly — Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY)
- [ERA5-Land Daily Aggregated — Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR)
- [Open-Meteo — Documentação da API](https://open-meteo.com/en/docs)
- [MetPy — Documentação oficial](https://unidata.github.io/MetPy/latest/)

---

## Funcionalidades

O Clima-Cast-Crepaldi oferece recursos para consulta, processamento e visualização de informações meteorológicas, incluindo:

- **Seleção geográfica:** escolha de estados e municípios brasileiros, além da delimitação de áreas por polígonos e círculos.
- **Séries temporais:** visualização da evolução das variáveis meteorológicas, acompanhada de estatísticas descritivas.
- **Mapas interativos e estáticos:** representação espacial de variáveis meteorológicas, com ferramentas de navegação e análise.
- **Análise de dados ERA5-Land:** processamento de informações meteorológicas históricas por meio do Google Earth Engine.
- **Diagramas Skew-T/log-P:** representação de perfis verticais da atmosfera obtidos por meio da plataforma Open-Meteo, com cálculos termodinâmicos utilizando a biblioteca MetPy.
- **Índices de instabilidade atmosférica:** cálculo de parâmetros como CAPE, CIN, LCL, LFC, EL, Lifted Index e K-Index, conforme a disponibilidade dos dados necessários.
- **Exportação de resultados:** disponibilização de dados e produtos gráficos para análises complementares.

Os perfis provenientes do Open-Meteo representam dados de modelos meteorológicos, não radiossondagens observacionais. Portanto, seus resultados devem ser interpretados considerando as limitações de representação da atmosfera pelos modelos numéricos.

---

## Requisitos

- **Python 3.12:** versão utilizada como referência no ambiente de publicação do aplicativo.
- **Google Earth Engine:** acesso a um projeto do Google Cloud habilitado para utilização da API do Earth Engine, com autenticação e permissões adequadas.
- **Bibliotecas Python:** dependências especificadas no arquivo `requirements.txt`.
- **Conexão com a internet:** necessária para acessar os serviços do Google Earth Engine e do Open-Meteo.

A execução local requer a configuração das credenciais do Google Earth Engine. Na publicação pelo Streamlit Community Cloud, essas credenciais devem ser configuradas de maneira segura, sem inclusão de informações sigilosas no repositório público.

---

## Instalação (execução local)

**1. Clone o repositório:**

```bash
git clone https://github.com/Crepaldi2025/dashboard_cat314.git
cd dashboard_cat314
```

**2. Crie e ative um ambiente virtual Python 3.12:**

No Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3. Instale as dependências:**

```bash
python -m pip install -r requirements.txt
```

**4. Configure o Google Earth Engine:**

A execução local requer autenticação no Google Earth Engine e acesso a um projeto do Google Cloud habilitado para sua utilização.

```bash
earthengine authenticate
```

A configuração do projeto e das credenciais deve ser compatível com o mecanismo de inicialização implementado no aplicativo.

**5. Execute o ClimaCast:**

```bash
streamlit run main.py
```

O Streamlit disponibilizará o endereço local da aplicação, normalmente `http://localhost:8501`.

**Observação:** não publique arquivos de credenciais ou informações sigilosas no repositório GitHub.

## Estrutura do repositório

O código-fonte e os recursos do Clima-Cast-Crepaldi estão organizados da seguinte forma:

```text
dashboard_cat314/
│
├── assets/                  # Imagens e recursos gráficos
├── data/                    # Dados auxiliares e municípios do IBGE
├── docs/                    # Documentação técnica e de usuário
├── src/                     # Módulos Python da aplicação
│   ├── __init__.py
│   ├── charts_visualizer.py
│   ├── gee_handler.py
│   ├── map_visualizer.py
│   ├── shapefile_handler.py
│   ├── skewt_handler.py
│   ├── skewt_visualizer.py
│   ├── ui.py
│   └── utils.py
│
├── main.py                  # Ponto de entrada do Streamlit
├── requirements.txt         # Dependências Python
├── packages.txt             # Dependências de sistema
└── runtime.txt              # Configuração do ambiente Python
```

A pasta `src/` concentra a implementação dos recursos de processamento e visualização. Os demais diretórios separam dados auxiliares, recursos gráficos e documentos de referência.

O arquivo `main.py`, localizado na raiz, é o ponto de entrada da aplicação Streamlit.

## Acesso ao aplicativo e à documentação

O Clima-Cast-Crepaldi está disponível publicamente por meio do Streamlit Community Cloud.

**Aplicativo:** [Clima-Cast-Crepaldi](https://climacastcrepaldiv2.streamlit.app/)

**Código-fonte:** [Repositório GitHub](https://github.com/Crepaldi2025/dashboard_cat314)

### Documentação complementar

Os documentos estão disponíveis na pasta [`docs/`](https://github.com/Crepaldi2025/dashboard_cat314/tree/main/docs) do repositório:

- `Clima_Cast_Manual_Tecnico.pdf` — Manual técnico da aplicação.
- `Clima_Cast_Manual_Usuario.pdf` — Manual de utilização.
- `Guia_Deploy.pdf` — Orientações para publicação.
- `ApresentacaoClimaCast.pptx` — Apresentação do projeto.
- `sobre.docx` — Documento descritivo original do aplicativo.

A documentação complementa as informações apresentadas neste README e permite compreender os recursos, a arquitetura e a utilização do sistema.



