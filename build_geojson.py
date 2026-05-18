"""
Conversor: planilha de obras Teresina -> GeoJSON normalizado.

Estratégia para geocodificação:
- Cada obra é posicionada no centroide do bairro (dicionário curado).
- Se o bairro não for reconhecido, usa centroide da zona.
- Pequeno offset pseudoaleatório (semeado pelo ID/index) para evitar marcadores empilhados.
"""
import json
import math
import random
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ===== Centroides aproximados de bairros de Teresina (lat, lon) =====
# Coordenadas aproximadas — não substituem cadastro oficial.
BAIRROS_COORDS = {
    # Centro / Sul
    "CENTRO": (-5.0892, -42.8019),
    "PIÇARRA": (-5.0975, -42.7989),
    "SÃO PEDRO": (-5.1042, -42.7964),
    "VERMELHA": (-5.0908, -42.7864),
    "MORADA DO SOL": (-5.1135, -42.7872),
    "CRISTO REI": (-5.1142, -42.7967),
    "MONTE CASTELO": (-5.1018, -42.7905),
    "TABULETA": (-5.1075, -42.7836),
    "SÃO CRISTÓVÃO": (-5.1153, -42.8147),
    "ILHOTAS": (-5.0838, -42.8067),
    "CABRAL": (-5.0825, -42.8014),
    "MARQUÊS": (-5.0789, -42.7967),
    "MARQUES": (-5.0789, -42.7967),
    "PORENQUANTO": (-5.0703, -42.7889),
    "ACARAPE": (-5.0533, -42.7700),
    "MEMORARE": (-5.0511, -42.7639),
    "REAL COPAGRE": (-5.0589, -42.7592),
    "MOCAMBINHO": (-5.0319, -42.7806),
    "BUENOS AIRES": (-5.0428, -42.7811),
    "POTI VELHO": (-5.0214, -42.7733),
    "OLARIAS": (-5.0497, -42.7825),
    "AEROPORTO": (-5.0586, -42.8233),
    "ALTO ALEGRE": (-5.0314, -42.7972),
    "MATADOURO": (-5.0531, -42.8089),
    "PRIMAVERA": (-5.0506, -42.7969),
    "BOA ESPERANÇA": (-5.0364, -42.7892),
    "PARQUE ALVORADA": (-5.0392, -42.7964),
    "SÃO JOAQUIM": (-5.0644, -42.7747),
    # Leste
    "FÁTIMA": (-5.0822, -42.7833),
    "FATIMA": (-5.0822, -42.7833),
    "HORTO": (-5.0742, -42.7758),
    "JÓQUEI": (-5.0775, -42.7706),
    "JOQUEI": (-5.0775, -42.7706),
    "ININGA": (-5.0594, -42.7942),
    "PLANALTO ININGA": (-5.0556, -42.7872),
    "SATÉLITE": (-5.0625, -42.7706),
    "SATELITE": (-5.0625, -42.7706),
    "SAMAPI": (-5.0428, -42.7758),
    "URUGUAI": (-5.0461, -42.7706),
    "MORROS": (-5.0497, -42.7567),
    "RECANTO DAS PALMEIRAS": (-5.0539, -42.7592),
    "GURUPI": (-5.0644, -42.7553),
    "VALE DO GAVIÃO": (-5.0508, -42.7536),
    "VALE QUEM TEM": (-5.0594, -42.7497),
    # Sul
    "PARQUE PIAUÍ": (-5.1456, -42.7903),
    "PARQUE PIAUI": (-5.1456, -42.7903),
    "PROMORAR": (-5.1547, -42.7847),
    "ANGELIM": (-5.1572, -42.7794),
    "DIRCEU ARCOVERDE": (-5.1450, -42.7794),
    "DIRCEU": (-5.1450, -42.7794),
    "ITARARÉ": (-5.1378, -42.7758),
    "ITARARE": (-5.1378, -42.7758),
    "ESPLANADA": (-5.1311, -42.7886),
    "BELA VISTA": (-5.1561, -42.7869),
    "SACI": (-5.1233, -42.7886),
    "CATARINA": (-5.1322, -42.7858),
    "TODOS OS SANTOS": (-5.1483, -42.7958),
    "REDONDA": (-5.1547, -42.8014),
    "TRÊS ANDARES": (-5.1611, -42.7942),
    "TRES ANDARES": (-5.1611, -42.7942),
    "DISTRITO INDUSTRIAL": (-5.1700, -42.8067),
    "PIO XII": (-5.1336, -42.7811),
    "CIDADE JARDIM": (-5.1219, -42.7997),
    "TORQUATO NETO": (-5.1397, -42.7714),
    # Norte
    "SANTA MARIA DA CODIPI": (-5.0119, -42.7892),
    "SANTA MARIA": (-5.0119, -42.7892),
    "PARQUE WALL FERRAZ": (-5.0042, -42.7847),
    "VILA SÃO FRANCISCO": (-5.0186, -42.7833),
    "JACINTA ANDRADE": (-4.9956, -42.7811),
    "PARQUE BRASIL": (-5.0044, -42.7972),
    "PORTO DO CENTRO": (-5.0892, -42.8086),
    "NOVO HORIZONTE": (-5.0247, -42.7869),
    "JORNALISTA": (-5.0156, -42.7733),
    "PARQUE JURITI": (-4.9925, -42.7906),
    "GRANDE SANTO ANTÔNIO": (-5.0089, -42.7644),
    "ALEGRE": (-5.0150, -42.7969),
    "EMBRAPA": (-5.0083, -42.7508),
    # Sudeste
    "VERDE LAR": (-5.1322, -42.7642),
    "PEDRA MIÚDA": (-5.1414, -42.7619),
    "PEDRA MIUDA": (-5.1414, -42.7619),
    "ZULMIRA": (-5.1483, -42.7672),
    "SÃO LOURENÇO": (-5.1564, -42.7706),
    "POLO SUL INDUSTRIAL": (-5.1736, -42.7853),
    "LIVRAMENTO": (-5.1192, -42.7706),
    # Bairros adicionais frequentes nos dados
    "SANTA TERESA": (-5.1581, -42.7717),
    "SANTA TEREZA": (-5.1581, -42.7717),
    "LOURIVAL PARENTE": (-5.1361, -42.7906),
    "RENASCENÇA": (-5.0686, -42.7853),
    "RENASCENCA": (-5.0686, -42.7853),
    "RENASCENÇA II": (-5.0719, -42.7811),
    "RENASCENCA II": (-5.0719, -42.7811),
    "RENASCENÇA III": (-5.0750, -42.7775),
    "PEDRA MOLE": (-5.1267, -42.7619),
    "MOCAMBINHO III": (-5.0289, -42.7775),
    "SOCOPO": (-5.0664, -42.7494),
    "SOCOPÓ": (-5.0664, -42.7494),
    "DIRCEU I": (-5.1431, -42.7822),
    "DIRCEU II": (-5.1469, -42.7767),
    "DIRCEU ARCOVERDE I": (-5.1431, -42.7822),
    "DIRCEU ARCOVERDE II": (-5.1469, -42.7767),
    "SÃO RAIMUNDO": (-5.1106, -42.8033),
    "SAO RAIMUNDO": (-5.1106, -42.8033),
    "SÃO JOÃO": (-5.1175, -42.8064),
    "SAO JOAO": (-5.1175, -42.8064),
    "SÃO SEBASTIÃO": (-5.1419, -42.8131),
    "SÃO FRANCISCO": (-5.0653, -42.8014),
    "SAO FRANCISCO": (-5.0653, -42.8014),
    "SANTO ANTÔNIO": (-5.0986, -42.7944),
    "SANTO ANTONIO": (-5.0986, -42.7944),
    "TABAJARAS": (-5.1294, -42.7700),
    "MACAÚBA": (-5.1056, -42.7728),
    "MACAUBA": (-5.1056, -42.7728),
    "CIDADE NOVA": (-5.0944, -42.8156),
    "CIDADE INDUSTRIAL": (-4.9931, -42.7689),
    "TRIUNFO": (-5.1392, -42.7889),
    "MORADA NOVA": (-5.1156, -42.7822),
    "ALVORADA": (-5.0397, -42.7728),
    "ÁGUA MINERAL": (-5.0214, -42.7950),
    "AGUA MINERAL": (-5.0214, -42.7950),
    "PIRAJÁ": (-5.0386, -42.7986),
    "PIRAJA": (-5.0386, -42.7986),
    "AREIAS": (-5.0689, -42.7997),
    "AROEIRAS": (-5.0814, -42.7572),
    "AROEIRA": (-5.0814, -42.7572),
    "PIÇARREIRA": (-5.0436, -42.7625),
    "PICARREIRA": (-5.0436, -42.7625),
    "CHAPADINHA SUL": (-5.1764, -42.7806),
    "PARQUE JACINTA": (-4.9956, -42.7811),
    "PARQUE VITÓRIA": (-5.0117, -42.7867),
    "PARQUE VITORIA": (-5.0117, -42.7867),
    "PARQUE BRASIL II": (-5.0083, -42.7944),
    "PARQUE BRASIL 3": (-5.0072, -42.8003),
    "PARQUE SÃO JOÃO": (-5.1153, -42.7986),
    "PARQUE SUL": (-5.1672, -42.7958),
    "PARQUE IDEAL": (-5.0317, -42.7919),
    "PARQUE POTI": (-5.0258, -42.7847),
    "ZOOBOTÂNICO": (-5.0958, -42.7997),
    "ZOOBOTANICO": (-5.0958, -42.7997),
    "VILA IRMÃ DULCE": (-5.1336, -42.7794),
    "VILA IRMA DULCE": (-5.1336, -42.7794),
    "IRMÃ DULCE": (-5.1336, -42.7794),
    "VILA OPERÁRIA": (-5.0625, -42.7906),
    "VILA OPERARIA": (-5.0625, -42.7906),
    "BRASILAR": (-5.1672, -42.7906),
    "PALITOLANDIA": (-5.1614, -42.7842),
    "PALITOLÂNDIA": (-5.1614, -42.7842),
    "PIMENTA": (-5.0822, -42.7958),
    "MATINHA": (-5.0989, -42.7847),
    "MAFRENSE": (-5.1581, -42.7869),
    "CACIMBA VELHA": (-5.0306, -42.8133),
    "MONTE VERDE": (-5.0294, -42.7958),
    "MONTE ALEGRE": (-5.1483, -42.8050),
    "PLANALTO": (-5.0556, -42.7872),
    "TANCREDO NEVES": (-5.0561, -42.7906),
    "VERDE CAP": (-5.0792, -42.7553),
    "EXTREMA": (-5.0064, -42.8056),
    "POTY VELHO": (-5.0214, -42.7733),
    "MUNDO NOVO": (-5.1422, -42.7894),
}

# Centroides aproximados de Zonas (fallback quando o bairro não é reconhecido)
ZONAS_COORDS = {
    "ZONA NORTE": (-5.0250, -42.7850),
    "NORTE": (-5.0250, -42.7850),
    "CENTRO NORTE": (-5.0500, -42.7900),
    "ZONA SUL": (-5.1450, -42.7900),
    "SUL": (-5.1450, -42.7900),
    "ZONA LESTE": (-5.0700, -42.7700),
    "LESTE": (-5.0700, -42.7700),
    "ZONA SUDESTE": (-5.1300, -42.7650),
    "SUDESTE": (-5.1300, -42.7650),
    "ZONA CENTRO": (-5.0900, -42.8000),
    "CENTRO": (-5.0900, -42.8000),
}

CENTRO_TERESINA = (-5.0892, -42.8019)


def normalizar(txt):
    if pd.isna(txt) or txt is None:
        return ""
    s = str(txt).strip().upper()
    # remove acentos para matching
    s_norm = unicodedata.normalize("NFD", s)
    s_norm = "".join(c for c in s_norm if unicodedata.category(c) != "Mn")
    return s, s_norm


def buscar_coord_bairro(bairro_raw):
    """Busca o centroide do bairro. Aceita 'A, B' pegando o primeiro."""
    if pd.isna(bairro_raw) or bairro_raw is None:
        return None
    s = str(bairro_raw).strip()
    if not s or s in ("-", "nan"):
        return None
    # se vier "MEMORARE, BELA VISTA" pega o primeiro
    primeiro = re.split(r"[,;/]", s)[0].strip().upper()
    if primeiro in BAIRROS_COORDS:
        return BAIRROS_COORDS[primeiro]
    # tenta sem acento
    primeiro_sem_acento = unicodedata.normalize("NFD", primeiro)
    primeiro_sem_acento = "".join(c for c in primeiro_sem_acento if unicodedata.category(c) != "Mn")
    for k, v in BAIRROS_COORDS.items():
        k_sem = unicodedata.normalize("NFD", k)
        k_sem = "".join(c for c in k_sem if unicodedata.category(c) != "Mn")
        if k_sem == primeiro_sem_acento:
            return v
    return None


def buscar_coord_zona(zona_raw):
    if pd.isna(zona_raw) or zona_raw is None:
        return None
    s = str(zona_raw).strip().upper()
    if not s or s in ("-", "NAN"):
        return None
    primeiro = re.split(r"[,;/]", s)[0].strip()
    return ZONAS_COORDS.get(primeiro)


def coord_com_offset(base, seed_int):
    """Aplica offset determinístico (~50–250 m) para não empilhar marcadores."""
    if base is None:
        return None
    rng = random.Random(seed_int)
    # ~0.0005 grau ≈ 55 m. Usamos raio de ~0.0005 a 0.0025
    raio = rng.uniform(0.0005, 0.0025)
    ang = rng.uniform(0, 2 * math.pi)
    return (base[0] + raio * math.cos(ang), base[1] + raio * math.sin(ang))


def parse_valor(v):
    """Converte string/num com possíveis 'R$' e separadores PT-BR para float."""
    if pd.isna(v) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in ("-", "nan"):
        return None
    s = s.replace("R$", "").replace(" ", "").strip()
    # se tem vírgula como decimal: "1.234,56" -> "1234.56"
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_data(v):
    """Tenta normalizar para YYYY-MM-DD. Aceita serial Excel."""
    if pd.isna(v) or v is None:
        return None
    if isinstance(v, (int, float)):
        # serial date Excel
        try:
            ts = pd.to_datetime(v, unit="D", origin="1899-12-30")
            return ts.strftime("%Y-%m-%d")
        except Exception:
            return None
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s or s in ("-", "nan"):
        return None
    try:
        ts = pd.to_datetime(s, dayfirst=False, errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def construir_features(df, origem, mapeamento, seed_base):
    features = []
    bairros_nao_mapeados = set()
    for idx, row in df.iterrows():
        bairro_raw = row.get(mapeamento["bairro"]) if mapeamento["bairro"] else None
        zona_raw = row.get(mapeamento["zona"]) if mapeamento["zona"] else None

        base = buscar_coord_bairro(bairro_raw)
        precisao = "bairro"
        if base is None:
            base = buscar_coord_zona(zona_raw)
            precisao = "zona"
            if bairro_raw and str(bairro_raw).strip() not in ("-", "nan", ""):
                bairros_nao_mapeados.add(str(bairro_raw).strip().upper())
        if base is None:
            base = CENTRO_TERESINA
            precisao = "municipio"

        seed = seed_base + idx
        coord = coord_com_offset(base, seed)

        props = {
            "origem": origem,
            "categoria": mapeamento["categoria"](row),
            "descricao": str(row.get(mapeamento["descricao"], "")).strip(),
            "orgao": str(row.get(mapeamento["orgao"], "")).strip() if mapeamento["orgao"] else "",
            "bairro": str(bairro_raw).strip() if bairro_raw and not pd.isna(bairro_raw) else "",
            "zona": str(zona_raw).strip() if zona_raw and not pd.isna(zona_raw) else "",
            "valor_contrato": parse_valor(row.get(mapeamento["valor_contrato"])) if mapeamento["valor_contrato"] else None,
            "valor_pago": parse_valor(row.get(mapeamento["valor_pago"])) if mapeamento["valor_pago"] else None,
            "execucao_pct": parse_valor(row.get(mapeamento["execucao"])) if mapeamento["execucao"] else None,
            "data": parse_data(row.get(mapeamento["data"])) if mapeamento["data"] else None,
            "id_externo": str(row.get(mapeamento["id"], "")).strip() if mapeamento["id"] else "",
            "status": str(row.get(mapeamento["status"], "")).strip() if mapeamento["status"] else mapeamento["status_padrao"],
            "link": str(row.get(mapeamento["link"], "")).strip() if mapeamento["link"] else "",
            "precisao_localizacao": precisao,
        }

        # normalizar execução percentual (alguns vem como 0..1, outros 0..100)
        if props["execucao_pct"] is not None and 0 <= props["execucao_pct"] <= 1:
            props["execucao_pct"] = round(props["execucao_pct"] * 100, 2)

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [coord[1], coord[0]]},  # lon, lat
            "properties": props,
        }
        features.append(feature)
    return features, bairros_nao_mapeados


def main():
    fonte = "obras_teresina.xlsx"
    sheets = pd.read_excel(fonte, sheet_name=None)

    todas_features = []
    todos_nao_mapeados = set()

    # 1. Concluídas SIMO
    df = sheets["concluídas - SIMO"]
    df = df[df["Municipios"].astype(str).str.contains("TERESINA", na=False)]
    feats, nm = construir_features(
        df, "SIMO - Concluída",
        {
            "categoria": lambda r: "Obra SIMO",
            "descricao": "Descricão",
            "orgao": "UG",
            "bairro": "Bairro",
            "zona": "Zona",
            "valor_contrato": "Valor Contrato",
            "valor_pago": "Valor Pago",
            "execucao": "Execução%",
            "data": "Data Recebimento",
            "id": "ID SIMO",
            "status": None,
            "status_padrao": "Concluída",
            "link": None,
        },
        seed_base=1000,
    )
    todas_features.extend(feats)
    todos_nao_mapeados |= nm

    # 2. Execução SIMO
    df = sheets["Execução - SIMO"]
    df = df[df["Municipios"].astype(str).str.contains("TERESINA", na=False)]
    feats, nm = construir_features(
        df, "SIMO - Execução",
        {
            "categoria": lambda r: "Obra SIMO",
            "descricao": "Descricão",
            "orgao": "UG",
            "bairro": "Bairro",
            "zona": "Zona",
            "valor_contrato": "Valor Contrato",
            "valor_pago": "Valor Pago",
            "execucao": "Execução%",
            "data": "Celebracão",
            "id": "ID SIMO",
            "status": "Status",
            "status_padrao": "Em execução",
            "link": None,
        },
        seed_base=2000,
    )
    todas_features.extend(feats)
    todos_nao_mapeados |= nm

    # 3. Convênios
    df = sheets["Convênio"]
    df = df[df["Municípios"].astype(str).str.contains("TERESINA", na=False)]
    feats, nm = construir_features(
        df, "Convênio",
        {
            "categoria": lambda r: "Convênio Federal",
            "descricao": "Objeto",
            "orgao": "Nome Proponente",
            "bairro": "BAIRRO",
            "zona": "ZONA",
            "valor_contrato": "Valor Global",
            "valor_pago": "Valor Desembolsado Acumulado",
            "execucao": "Execução Financeira do Concedente",
            "data": "Data Início de Vigência Conv.",
            "id": "Nº Instrumento",
            "status": "Situação Instrumento",
            "status_padrao": "Em execução",
            "link": "Link Externo",
        },
        seed_base=3000,
    )
    todas_features.extend(feats)
    todos_nao_mapeados |= nm

    # 4. TD Concluído
    df = sheets["TD - Concluído"]
    df = df[df["Municipios"].astype(str).str.contains("TERESINA", na=False)]
    feats, nm = construir_features(
        df, "TD - Concluído",
        {
            "categoria": lambda r: (str(r.get("Eixo Balanço", "")).strip() if pd.notna(r.get("Eixo Balanço")) and str(r.get("Eixo Balanço")).strip() not in ("", "nan") else "Outros"),
            "descricao": "Descrição",
            "orgao": "ÓRGÃO",
            "bairro": "Bairro",
            "zona": "Zona",
            "valor_contrato": None,
            "valor_pago": "ValorPago",
            "execucao": None,
            "data": "Recebimento",
            "id": None,
            "status": None,
            "status_padrao": "Concluída",
            "link": None,
        },
        seed_base=4000,
    )
    todas_features.extend(feats)
    todos_nao_mapeados |= nm

    # 5. TD Execução
    df = sheets["TD - Execução"]
    df = df[df["Municipio"].astype(str).str.contains("TERESINA", na=False)]
    feats, nm = construir_features(
        df, "TD - Execução",
        {
            "categoria": lambda r: "TD - Em execução",
            "descricao": "Descrição",
            "orgao": "ÓRGÃO",
            "bairro": "Bairro",
            "zona": "Zona",
            "valor_contrato": None,
            "valor_pago": "Valor Pago",
            "execucao": None,
            "data": None,
            "id": None,
            "status": None,
            "status_padrao": "Em execução",
            "link": None,
        },
        seed_base=5000,
    )
    todas_features.extend(feats)
    todos_nao_mapeados |= nm

    geojson = {"type": "FeatureCollection", "features": todas_features}

    out = Path("/home/claude/obras-municipio/data/obras_teresina.geojson")
    out.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"GeoJSON gerado: {out} | {len(todas_features)} obras")
    if todos_nao_mapeados:
        print(f"\nBairros NÃO mapeados ({len(todos_nao_mapeados)}) — caíram no centroide da zona:")
        for b in sorted(todos_nao_mapeados):
            print(f"  - {b}")


if __name__ == "__main__":
    main()
