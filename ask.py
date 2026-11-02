"""Perguntas sobre a LGPD: busca os artigos mais relevantes e pede ao modelo
que responda somente com base neles, citando os artigos."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import ollama

ARQUIVO_INDICE = Path("data/index.json")
MODELO_EMBEDDING = "bge-m3"
MODELO_CHAT = "gemma3:12b"
QUANTIDADE_TRECHOS = 4

# Reconhece "artigo 18", "art. 18", "arts. 7", "Art 55-A"
PADRAO_CITACAO = re.compile(r"\bart(?:igos?|s?\.)?\s*(\d+)(?:-([A-Za-z])\b)?", re.I)

INSTRUCOES = (
    "Você é um assistente que responde perguntas sobre a LGPD (Lei nº 13.709/2018). "
    "Responda SOMENTE com base nos trechos da lei fornecidos pelo usuário. "
    "Cada trecho começa com um cabeçalho '--- TRECHO: Art. N ---'. "
    "Cite o artigo indicado no cabeçalho do trecho de onde veio a informação "
    "(por exemplo, 'Art. 18, II'). Nunca cite um artigo que não apareça em um cabeçalho. "
    "Se os trechos não trouxerem a resposta, diga exatamente: "
    "'Não encontrei isso nos trechos da LGPD fornecidos.' "
    "Não invente artigos, incisos ou números. Responda em português."
)


def numeros_de_artigos(texto):
    """Devolve os números de artigo mencionados em um texto, como {'18', '55-A'}."""
    achados = set()
    for numero, letra in PADRAO_CITACAO.findall(texto):
        achados.add(numero + (f"-{letra.upper()}" if letra else ""))
    return achados


def carregar_indice():
    pedacos = json.loads(ARQUIVO_INDICE.read_text(encoding="utf-8"))
    matriz = np.array([p["embedding"] for p in pedacos], dtype=float)
    # Normaliza cada vetor (comprimento 1): assim o produto escalar vira a
    # "similaridade de cosseno", que mede o quanto dois textos se parecem
    matriz = matriz / np.linalg.norm(matriz, axis=1, keepdims=True)
    return pedacos, matriz


def buscar(pergunta, pedacos, matriz, k=QUANTIDADE_TRECHOS):
    resposta = ollama.embed(model=MODELO_EMBEDDING, input=pergunta)
    vetor = np.array(resposta["embeddings"][0], dtype=float)
    vetor = vetor / np.linalg.norm(vetor)
    similaridades = matriz @ vetor
    ranking = [(pedacos[i], float(similaridades[i])) for i in np.argsort(similaridades)[::-1]]

    # Busca direta: artigos citados pelo número na pergunta vêm primeiro
    citados = numeros_de_artigos(pergunta)
    diretos = [(p, 1.0) for p in pedacos if p["artigo"] in citados]
    resto = [(p, s) for p, s in ranking if p["artigo"] not in citados]
    return (diretos + resto)[:k]


def montar_mensagem(pergunta, encontrados):
    trechos = "\n\n".join(
        f"--- TRECHO: Art. {p['artigo']} ---\n{p['texto']}" for p, _ in encontrados
    )
    return f"{trechos}\n\nPERGUNTA: {pergunta}"


def responder(pergunta, pedacos, matriz):
    encontrados = buscar(pergunta, pedacos, matriz)
    resposta = ollama.chat(
        model=MODELO_CHAT,
        messages=[
            {"role": "system", "content": INSTRUCOES},
            {"role": "user", "content": montar_mensagem(pergunta, encontrados)},
        ],
        options={"temperature": 0, "num_ctx": 8192},
    )
    return resposta["message"]["content"], encontrados


def citacoes_fora_dos_trechos(resposta, encontrados):
    """Artigos citados na resposta que não estavam nos trechos enviados nem são
    mencionados dentro deles (referências internas da própria lei)."""
    permitidos = {p["artigo"] for p, _ in encontrados}
    for p, _ in encontrados:
        permitidos |= numeros_de_artigos(p["texto"])
    return sorted(numeros_de_artigos(resposta) - permitidos)

def main():
    pergunta = " ".join(sys.argv[1:]) or input("Pergunta sobre a LGPD: ")
    pedacos, matriz = carregar_indice()
    texto, encontrados = responder(pergunta, pedacos, matriz)
    print("\n" + texto)

    suspeitas = citacoes_fora_dos_trechos(texto, encontrados)
    if suspeitas:
        print(
            f"\nATENÇÃO: a resposta cita artigos que não estavam nos trechos enviados: "
            f"{suspeitas}. Pode ser uma referência interna da lei ou um erro do modelo: confira."
        )

    citados = numeros_de_artigos(pergunta)
    print("\nTrechos usados:")
    for pedaco, nota in encontrados:
        origem = "citado na pergunta" if pedaco["artigo"] in citados else f"similaridade {nota:.2f}"
        print(f"  Art. {pedaco['artigo']} ({origem})")


if __name__ == "__main__":
    main()