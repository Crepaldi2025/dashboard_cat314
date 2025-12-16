# Clima-Cast-Crepaldi

Plataforma interativa para consulta, análise e visualização de dados meteorológicos históricos no Brasil, com foco didático e científico, integrando ERA5-Land via Google Earth Engine.

---

## Sobre o Aplicativo – Clima-Cast-Crepaldi

O **Clima-Cast-Crepaldi** é um sistema interativo desenvolvido como parte do projeto da disciplina **CAT314 – Ferramentas de Previsão de Curtíssimo Prazo (Nowcasting)**, do curso de Ciências Atmosféricas da **Universidade Federal de Itajubá (UNIFEI)**. O aplicativo tem como propósito integrar dados meteorológicos provenientes de fontes de reanálise global e disponibilizá-los em uma plataforma visual, dinâmica e acessível, favorecendo tanto a análise científica quanto o uso didático.

## Objetivo

O principal objetivo do sistema é proporcionar uma interface intuitiva e interativa para consulta, análise e visualização de dados meteorológicos históricos dos municípios brasileiros, a partir da base de dados **ERA5-Land**, disponibilizada pelo **European Centre for Medium-Range Weather Forecasts (ECMWF)** por meio da plataforma **Google Earth Engine (GEE)**.

---

## Fontes de dados e plataforma

- **ERA5-Land (ECMWF/C3S)**: reanálise com foco em aplicações terrestres, disponibilizada publicamente a partir de 1950, com defasagem típica de poucos dias em relação ao presente (dependendo do canal de distribuição).
- **Google Earth Engine (GEE)**: plataforma em nuvem para processamento e análise geoespacial em escala planetária.

---

## Funcionalidades (visão geral)

Dependendo da versão do aplicativo no repositório, o sistema pode incluir:

- Seleção de **área de interesse** (por exemplo: Estado, Município, Polígono, Círculo).
- Visualização de **séries temporais** (com estatísticas descritivas e interação no gráfico).
- Mapas interativos para **campos espaciais** e inspeção visual.
- Execução local e publicação via **Streamlit Community Cloud**.

---

## Requisitos

- Python 3.10+ (recomendado alinhar a versão local com a usada no deploy).
- Conta no Google com acesso ao **Earth Engine** (e credenciais quando necessário).
- Dependências Python descritas em `requirements.txt`.

---

## Instalação (execução local)

1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   cd SEU_REPOSITORIO
