# Como atualizar os dados das obras

Os dados exibidos no painel vêm do arquivo `data/obras_teresina.geojson`, que é **gerado** a partir de uma planilha Excel pelo script `build_geojson.py`.

## Pré-requisitos

- Python 3.8 ou superior
- Bibliotecas: `pandas` e `openpyxl`

Instalar:
```bash
pip install pandas openpyxl
```

## Passo a passo

### 1. Atualizar a planilha

Mantenha a planilha com **as mesmas 5 abas** e **as mesmas colunas** do arquivo original:

| Aba | Colunas obrigatórias |
| --- | --- |
| `concluídas - SIMO` | ID SIMO, Municipios, UG, Descricão, Valor Contrato, Valor Pago, Execução%, Data Recebimento, Bairro, Zona |
| `Execução - SIMO` | ID SIMO, Municipios, Status, UG, Descricão, Celebracão, Valor Contrato, Valor Pago, Execução%, Bairro, Zona |
| `Convênio` | Nº Instrumento, Órgão Concedente, Objeto, Municípios, Valor Global, Valor Desembolsado Acumulado, BAIRRO, ZONA, Situação Instrumento, Data Início de Vigência Conv., Link Externo, Execução Financeira do Concedente |
| `TD - Concluído` | Eixo Balanço, ÓRGÃO, Descrição, Municipios, ValorPago, Bairro, Zona, Recebimento |
| `TD - Execução` | ÓRGÃO, Descrição, Municipio, Valor Pago, Bairro, Zona |

> Se você renomear uma coluna ou aba, será necessário ajustar o `build_geojson.py`.

### 2. Salvar a planilha

Salve o arquivo na pasta de uploads ou em qualquer caminho que você prefira. Em seguida, ajuste a linha do `build_geojson.py`:

```python
fonte = "/caminho/para/sua/planilha.xlsx"
```

### 3. Rodar o conversor

```bash
python build_geojson.py
```

Saída esperada:
```
GeoJSON gerado: data/obras_teresina.geojson | 1234 obras

Bairros NÃO mapeados (95) — caíram no centroide da zona:
  - ASSENTAMENTO XYZ
  - ...
```

### 4. Commit e push

```bash
git add data/obras_teresina.geojson
git commit -m "Atualizar dados de obras"
git push
```

O GitHub Pages atualiza em ~1 minuto.

---

## Ajustando o dicionário de bairros

Se houver bairros não mapeados que você queira posicionar mais precisamente, edite o dicionário `BAIRROS_COORDS` no topo do `build_geojson.py`:

```python
BAIRROS_COORDS = {
    "MEU BAIRRO": (-5.1234, -42.7890),  # (latitude, longitude)
    ...
}
```

Para obter coordenadas aproximadas de um bairro:
1. Acesse [OpenStreetMap](https://www.openstreetmap.org/)
2. Busque pelo nome do bairro
3. Clique com botão direito no centro → "Mostrar endereço" → copie as coordenadas

---

## Automatização opcional (GitHub Actions)

Se quiser que o GeoJSON seja regenerado automaticamente a cada commit da planilha, você pode adicionar `.github/workflows/build.yml`:

```yaml
name: Atualizar GeoJSON
on:
  push:
    paths: ['obras_teresina.xlsx']
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install pandas openpyxl
      - run: python build_geojson.py
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Auto: regenerar GeoJSON"
          file_pattern: data/obras_teresina.geojson
```

Aí basta substituir a planilha no repo e o GeoJSON é regenerado sozinho.
