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


def remover_vetados(pedacos: list) -> list:
    """Artigos vetados só têm '(VETADO).' e nenhum conteúdo: não entram no índice."""
    return [p for p in pedacos if not (len(p["texto"]) < 40 and "VETADO" in p["texto"])]


def manter_versao_mais_recente(pedacos: list) -> list:
    """O site mostra as redações antigas dos artigos alterados, da mais antiga
    para a mais nova. Ficamos com a última ocorrência de cada artigo."""
    ultimos = {}
    for p in pedacos:
        ultimos[p["artigo"]] = p  # a última ocorrência sobrescreve as anteriores
    return list(ultimos.values())


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
    brutos = quebrar_por_artigo(texto)
    sem_vetados = remover_vetados(brutos)
    ids = [p["artigo"] for p in sem_vetados]
    repetidos = {a for a in ids if ids.count(a) > 1}
    pedacos = manter_versao_mais_recente(sem_vetados)
    print(
        f"Pedaços brutos: {len(brutos)} | sem vetados: {len(sem_vetados)} "
        f"| um por artigo: {len(pedacos)}"
    )

    print("\nVersão escolhida dos artigos que tinham várias versões (final do texto):")
    for p in pedacos:
        if p["artigo"] in repetidos:
            print(f"  Art. {p['artigo']}: ...{p['texto'][-110:]!r}")

    print()
    vetores = gerar_embeddings([f"{p['capitulo']}\n{p['texto']}" for p in pedacos])
    for pedaco, vetor in zip(pedacos, vetores):
        pedaco["embedding"] = vetor

    ARQUIVO_INDICE.write_text(json.dumps(pedacos, ensure_ascii=False), encoding="utf-8")
    print(f"Índice salvo em {ARQUIVO_INDICE} ({len(pedacos)} pedaços)")


if __name__ == "__main__":
    main()