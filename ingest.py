"""Ingestão da LGPD: quebra o texto por artigo e gera os embeddings com o bge-m3."""
import json
import re
from pathlib import Path

import ollama

ARQUIVO_LEI = Path("data/lgpd.txt")
ARQUIVO_INDICE = Path("data/index.json")
MODELO_EMBEDDING = "bge-m3"
TAMANHO_LOTE = 16

# Começo de artigo no início da linha: "Art. 1º ", "Art. 10. " ou "Art. 55-A. "
PADRAO_ARTIGO = re.compile(r"^Art\.\s*(\d+)(?:\s*[º°])?(-[A-Z])?\.?\s", re.M)
# Títulos de capítulo e de seção ocupam duas linhas: "CAPÍTULO II" + o nome
PADRAO_CAPITULO = re.compile(r"^(CAPÍTULO\s+[IVXLC]+)[ \t]*\n+([^\n]+)", re.M)
PADRAO_SECAO = re.compile(r"^(Seção\s+[IVXLC]+)[ \t]*\n+([^\n]+)\n?", re.M)


def ler_texto() -> str:
    texto = ARQUIVO_LEI.read_text(encoding="utf-8")
    # Remove a palavra "Vigência" que o site deixa no fim das linhas (era um link)
    texto = re.sub(r"[ \t]*Vigência[ \t]*$", "", texto, flags=re.M)
    # Troca sequências de espaços por um espaço só
    return re.sub(r"[ \t]+", " ", texto)


def quebrar_por_artigo(texto: str) -> list:
    capitulos = [
        (m.start(), f"{m.group(1)} - {m.group(2).strip()}")
        for m in PADRAO_CAPITULO.finditer(texto)
    ]
    achados = list(PADRAO_ARTIGO.finditer(texto))
    pedacos = []
    for i, achado in enumerate(achados):
        inicio = achado.start()
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        corpo = texto[inicio:fim]
        # Tira títulos de capítulo/seção que ficam no fim do artigo anterior
        corpo = PADRAO_CAPITULO.sub("", corpo)
        corpo = PADRAO_SECAO.sub("", corpo)
        # Tira o rodapé (data e assinaturas) do último artigo
        corpo = re.split(r"\nBrasília, \d", corpo)[0].strip()
        # Descobre em qual capítulo o artigo está
        capitulo = ""
        for posicao, titulo in capitulos:
            if posicao < inicio:
                capitulo = titulo
        numero = achado.group(1) + (achado.group(2) or "")
        pedacos.append({"artigo": numero, "capitulo": capitulo, "texto": corpo})
    return pedacos


def gerar_embeddings(textos: list) -> list:
    vetores = []
    for i in range(0, len(textos), TAMANHO_LOTE):
        lote = textos[i : i + TAMANHO_LOTE]
        resposta = ollama.embed(model=MODELO_EMBEDDING, input=lote)
        vetores.extend(resposta["embeddings"])
        print(f"  embeddings: {len(vetores)}/{len(textos)}")
    return vetores


def main():
    texto = ler_texto()
    pedacos = quebrar_por_artigo(texto)
    ids = [p["artigo"] for p in pedacos]
    repetidos = sorted({a for a in ids if ids.count(a) > 1})
    print(f"Artigos encontrados: {len(pedacos)} (primeiro: {ids[0]}, último: {ids[-1]})")
    if repetidos:
        print(f"ATENÇÃO: artigos repetidos: {repetidos}")

    vetores = gerar_embeddings([f"{p['capitulo']}\n{p['texto']}" for p in pedacos])
    for pedaco, vetor in zip(pedacos, vetores):
        pedaco["embedding"] = vetor

    ARQUIVO_INDICE.write_text(json.dumps(pedacos, ensure_ascii=False), encoding="utf-8")
    print(f"Índice salvo em {ARQUIVO_INDICE} ({len(pedacos)} pedaços)")

    art18 = next((p for p in pedacos if p["artigo"] == "18"), None)
    if art18:
        print("\nPré-visualização do Art. 18:\n" + art18["texto"][:600])


if __name__ == "__main__":
    main()