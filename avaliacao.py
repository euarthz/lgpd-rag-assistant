"""Avaliação da busca: o artigo esperado aparece entre os trechos encontrados?
Também compara as notas de perguntas da lei com as de perguntas sem relação."""
from ask import QUANTIDADE_TRECHOS, buscar, carregar_indice

# (pergunta, artigos que contêm a resposta). Basta um deles aparecer para contar.
PERGUNTAS = [
    ("O que é dado pessoal?", {"5"}),
    ("O que é dado pessoal sensível?", {"5", "11"}),
    ("O que é anonimização?", {"5", "12"}),
    ("O que é consentimento?", {"5", "8"}),
    ("Quem é o controlador e quem é o operador?", {"5"}),
    ("O que faz o encarregado pelo tratamento de dados?", {"5", "41"}),
    ("Quais são os princípios que devem ser observados no tratamento de dados?", {"6"}),
    ("Em quais hipóteses o tratamento de dados pessoais pode ser realizado?", {"7"}),
    ("Quando o tratamento de dados sensíveis é permitido?", {"11"}),
    ("Como deve ser feito o tratamento de dados de crianças e adolescentes?", {"14"}),
    ("Quando os dados pessoais devem ser eliminados?", {"15", "16"}),
    ("O titular pode pedir a revisão de decisões automatizadas?", {"20"}),
    ("Quando é permitida a transferência internacional de dados?", {"33"}),
    ("O que o controlador deve fazer se houver um incidente de segurança?", {"48"}),
    ("Quais medidas de segurança os agentes de tratamento devem adotar?", {"46"}),
    ("Quais são as sanções administrativas previstas na lei?", {"52"}),
    ("Quem responde pelos danos causados pelo tratamento de dados?", {"42"}),
    ("A lei vale para uso de dados por pessoa física para fins particulares?", {"4"}),
    ("Como o poder público pode tratar dados pessoais?", {"23"}),
    ("O que é a ANPD?", {"5", "55-A"}),
]

FORA_DO_ESCOPO = [
    "Qual é a capital da França?",
    "Como fazer bolo de cenoura?",
    "Quem ganhou a Copa do Mundo de 2022?",
    "Qual a melhor linguagem de programação?",
    "Como funciona a fotossíntese?",
    # Perguntas próximas do tema, mas que o texto da LGPD não responde:
    "O que é o GDPR europeu?",
    "Quais são os direitos do consumidor no Código de Defesa do Consumidor?",
    "Como proteger meu computador contra vírus?",
    "O que é um ataque de phishing?",
    "O que diz o Marco Civil da Internet sobre neutralidade da rede?",
    "Qual é o prazo de prescrição para ações trabalhistas?",
    "Quanto uma empresa deve gastar com segurança da informação?",
]


def main():
    pedacos, matriz = carregar_indice()

    print("PERGUNTAS DENTRO DO ESCOPO\n")
    acertos_k = 0
    acertos_1 = 0
    notas_acertos = []
    for pergunta, esperados in PERGUNTAS:
        encontrados = buscar(pergunta, pedacos, matriz)
        ids = [p["artigo"] for p, _ in encontrados]
        acerto_k = any(a in ids for a in esperados)
        acerto_1 = ids[0] in esperados
        acertos_k += acerto_k
        acertos_1 += acerto_1
        nota = encontrados[0][1]
        if acerto_k:
            notas_acertos.append(nota)
        marca = "OK  " if acerto_k else "ERRO"
        print(f"[{marca}] {pergunta}")
        print(f"       esperado: {sorted(esperados)} | encontrados: {ids} | nota do 1º: {nota:.2f}")

    total = len(PERGUNTAS)
    print(f"\nAcerto entre os {QUANTIDADE_TRECHOS} trechos: {acertos_k}/{total}")
    print(f"Acerto no 1º trecho: {acertos_1}/{total}")

    print("\nPERGUNTAS FORA DO ESCOPO\n")
    notas_fora = []
    for pergunta in FORA_DO_ESCOPO:
        nota = buscar(pergunta, pedacos, matriz)[0][1]
        notas_fora.append(nota)
        print(f"  nota do 1º: {nota:.2f}  {pergunta}")

    print("\nSEPARAÇÃO ENTRE AS NOTAS")
    if notas_acertos:
        print(f"  Menor nota entre as perguntas da lei que acertaram: {min(notas_acertos):.2f}")
    print(f"  Maior nota entre as perguntas fora do escopo:       {max(notas_fora):.2f}")


if __name__ == "__main__":
    main()