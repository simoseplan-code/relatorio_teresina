# Nota Técnica · Obras em Teresina

Painel interativo de **1.176 obras públicas** no município de Teresina-PI, com filtros, busca e mapa.

**Demo local:** abra `index.html` em qualquer navegador (sem build, sem servidor).

---

## Funcionalidades

- 🗺️ **Mapa interativo** (Leaflet + OpenStreetMap/CARTO) com clustering
- 🔎 **Filtros combinados** por origem, eixo, órgão, situação, zona e busca livre
- 📋 **Lista clicável** — clicar em um item centraliza o mapa e abre o popup da obra
- 📊 **Indicadores** no cabeçalho que se atualizam conforme os filtros
- 📱 **Responsivo** (desktop, tablet e mobile)
- 🎨 **Estética editorial** — tipografia Fraunces + IBM Plex, sem cara de template

## Fonte dos dados

A planilha original (`obras_teresina.xlsx`) consolida 5 fontes:

| Aba                  | Registros | Origem              |
| -------------------- | --------- | ------------------- |
| concluídas - SIMO    | 280       | SIMO – Concluída    |
| Execução - SIMO      | 60        | SIMO – Execução     |
| Convênio             | 16        | Convênios federais  |
| TD - Concluído       | 773       | Transferência Direta – Concluído |
| TD - Execução        | 47        | Transferência Direta – Execução  |

Apenas obras com município `TERESINA` são incluídas.

## Geocodificação

Os dados originais **não possuem latitude/longitude**. O posicionamento dos marcadores segue esta hierarquia:

1. **Centroide do bairro** (84% das obras) — dicionário curado com ~110 bairros de Teresina
2. **Centroide da zona** (6%) — quando o bairro não é reconhecido
3. **Centro do município** (10%) — fallback final

Para evitar marcadores empilhados, cada ponto recebe um pequeno offset pseudoaleatório semeado pelo índice (50–250 m). Esse offset é determinístico: rodar o build novamente gera as mesmas coordenadas.

> ⚠️ **Importante**: o posicionamento é **aproximado** e serve para visualização agregada, não para localização exata da intervenção física.

## Estrutura

```
.
├── index.html                  # página principal
├── css/
│   └── style.css               # estilos (editorial, sem framework)
├── js/
│   └── app.js                  # lógica do mapa, filtros e lista
├── data/
│   └── obras_teresina.geojson  # 1.176 features (gerado a partir do xlsx)
├── build_geojson.py            # script de conversão xlsx → geojson
└── docs/
    └── COMO_ATUALIZAR.md       # como atualizar os dados
```

## Como atualizar os dados

Veja `docs/COMO_ATUALIZAR.md`. Em resumo:

1. Substitua o `.xlsx` original
2. Rode `python build_geojson.py`
3. Commit do novo `data/obras_teresina.geojson` e push

## Como publicar no GitHub Pages

1. Crie um repositório no GitHub e faça push deste projeto
2. Vá em **Settings → Pages**
3. Em **Source**, escolha branch `main` e pasta `/ (root)`
4. Pronto — site disponível em `https://<seu-usuario>.github.io/<repo>`

## Stack

- **Leaflet 1.9.4** — mapa
- **Leaflet.markercluster** — agrupamento
- **CARTO Voyager** — base de tiles (estilo sóbrio)
- **Fraunces + IBM Plex** — tipografia
- **Sem build step, sem framework, sem dependências de servidor**

## Licença

MIT. Os dados das obras seguem a licença da fonte original.
