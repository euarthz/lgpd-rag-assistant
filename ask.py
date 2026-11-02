"""Perguntas sobre a LGPD: busca os artigos mais parecidos e pede ao modelo
que responda somente com base neles, citando os artigos."""
import json
import sys
from pathlib import Path

import numpy as np
import ollama

ARQUIVO_INDICE = Path("data/index.json")
MODELO_EMBEDDING = "bge-m3"
MODELO_CHAT = "gemma3:12b"
QUANTIDADE_TRECHOS = 4

INSTRUCOES = (
    "Você é um assistente que responde perguntas sobre a LGPD (Lei nº 13.709/2018). "
    "Responda SOMENTE com base nos trechos da lei fornecidos pelo usuário. "
    "Cite sempre o número do artigo (por exemplo, 'Art. 18'). "
    "Se os trechos não trouxerem a resposta, diga exatamente: "
    "'Não encontrei isso nos trechos da LGPD fornecidos.' "
    "Não invente artigos, incisos ou números. Responda em português."
)


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
    melhores = np.argsort(similaridades)[::-1][:k]
    return [(pedacos[i], float(similaridades[i])) for i in melhores]


def montar_mensagem(pergunta, encontrados):
    trechos = "\n\n".join(p["texto"] for p, _ in encontrados)
    return f"TRECHOS DA LEI:\n{trechos}\n\nPERGUNTA: {pergunta}"


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


def main():
    pergunta = " ".join(sys.argv[1:]) or input("Pergunta sobre a LGPD: ")
    pedacos, matriz = carregar_indice()
    texto, encontrados = responder(pergunta, pedacos, matriz)
    print("\n" + texto)
    print("\nTrechos usados:")
    for pedaco, nota in encontrados:
        print(f"  Art. {pedaco['artigo']} (similaridade {nota:.2f})")


if __name__ == "__main__":
    main()