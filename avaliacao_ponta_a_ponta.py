"""Avaliação de ponta a ponta: o assistente recusa o que não está na lei
e responde, citando artigos, o que está?"""
from ask import carregar_indice, citacoes_fora_dos_trechos, numeros_de_artigos, responder
from avaliacao import FORA_DO_ESCOPO, PERGUNTAS


def recusou(resposta: str) -> bool:
    # O modelo nem sempre usa a frase exata das instruções: aceitamos variações
    return "não encontrei" in resposta.lower()


def main():
    pedacos, matriz = carregar_indice()

    print("FORA DO ESCOPO: o assistente deveria recusar\n")
    recusas_certas = 0
    for pergunta in FORA_DO_ESCOPO:
        resposta, _ = responder(pergunta, pedacos, matriz)
        ok = recusou(resposta)
        recusas_certas += ok
        print(f"[{'OK  ' if ok else 'ERRO'}] {pergunta}")
        if not ok:
            print(f"       resposta: {resposta[:200]!r}")

    print("\nDENTRO DO ESCOPO: o assistente deveria responder citando artigos\n")
    recusas_indevidas = 0
    sem_citacao = 0
    com_alarme = 0
    for pergunta, _ in PERGUNTAS:
        resposta, encontrados = responder(pergunta, pedacos, matriz)
        if recusou(resposta):
            recusas_indevidas += 1
            print(f"[RECUSOU] {pergunta}")
            continue
        citados = sorted(numeros_de_artigos(resposta))
        suspeitas = citacoes_fora_dos_trechos(resposta, encontrados)
        if not citados:
            sem_citacao += 1
        if suspeitas:
            com_alarme += 1
        print(f"[RESPONDEU] {pergunta}")
        print(f"       artigos citados: {citados} | citações suspeitas: {suspeitas}")

    print("\nRESUMO")
    print(f"  Recusas corretas (fora do escopo): {recusas_certas}/{len(FORA_DO_ESCOPO)}")
    print(f"  Recusas indevidas (dentro do escopo): {recusas_indevidas}/{len(PERGUNTAS)}")
    print(f"  Respostas sem nenhuma citação de artigo: {sem_citacao}")
    print(f"  Respostas com citação suspeita: {com_alarme}")


if __name__ == "__main__":
    main()