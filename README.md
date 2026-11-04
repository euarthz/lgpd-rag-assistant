# lgpd-rag-assistant

Assistente de perguntas e respostas sobre a **LGPD (Lei nº 13.709/2018)** que roda localmente.
Ele busca os artigos mais relevantes e pede a um modelo de linguagem que responda
**somente com base neles, citando o artigo**.

> Projeto de estudo. Não é aconselhamento jurídico. Confira sempre a redação vigente da lei
> no [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm).

## Por que RAG?

Perguntei ao `gemma3:12b`, **sem RAG**: "O que diz o artigo 18 da LGPD? Cite os incisos."
Ele respondeu com segurança, listou 8 incisos e inventou o texto de alguns. O Art. 18 tem 9 incisos (I a IX).
Com RAG, o assistente recebe o texto real do artigo e responde com os 9 incisos, citando "Art. 18".

## Como funciona

1. **Ingestão** (`ingest.py`): quebra o texto da lei em um pedaço por artigo (o Art. 5, que reúne as
   definições, é dividido por inciso), gera um vetor para cada pedaço com o `bge-m3` e salva em `data/index.json`.
2. **Busca** (`ask.py`): transforma a pergunta em vetor e pega os 4 trechos mais parecidos (similaridade de
   cosseno). Se a pergunta cita um artigo pelo número ("art. 18"), ele é buscado diretamente.
3. **Resposta**: o `gemma3:12b` recebe os trechos com cabeçalho (`--- TRECHO: Art. N ---`) e a instrução de
   responder só com eles, citar o artigo e recusar quando não achar a resposta.
4. **Verificação de citações**: se a resposta cita um artigo que não estava entre os trechos enviados (nem é
   referenciado dentro deles), o programa avisa.

O código só conversa com o [Ollama](https://ollama.com) local: nenhuma API externa é chamada.

## Resultados

Conjunto de avaliação: 20 perguntas sobre a lei (com o artigo esperado) e 12 fora do escopo
(5 sem relação nenhuma e 7 próximas do tema, como Marco Civil e GDPR).

| Métrica | Só por artigo | Art. 5 por inciso |
|---|---|---|
| Artigo esperado entre os 4 trechos | 19/20 | 20/20 |
| Artigo esperado no 1º trecho | 18/20 | 19/20 |
| Recusas indevidas (pergunta da lei) | 1/20 | 0/20 |
| Recusas corretas (fora do escopo) | 12/12 | 12/12 |

**Verificação manual:** conferi à mão duas respostas contra o texto de `data/lgpd.txt`.

- Princípios (Art. 6): a resposta trouxe a boa-fé e os 10 princípios do artigo.
- Sanções (Art. 52): os valores da multa (2% do faturamento e teto de R$ 50 milhões por infração) estavam
  corretos, mas o assistente resumiu o inciso II e omitiu "de direito privado" e "no seu último exercício,
  excluídos os tributos", qualificadores que mudam o alcance da regra. A avaliação automática não detecta
  esse tipo de perda, por isso a conferência manual é necessária.

## Limitações conhecidas

- **Amostra pequena e não independente:** usei as mesmas 20 perguntas para encontrar o problema do Art. 5 e para
  medir a melhora. Os números mostram a tendência, não uma garantia.
- **A avaliação automática não julga o conteúdo:** ela mede a busca, a recusa e a presença de citação. A correção
  do texto foi conferida à mão só em 2 respostas.
- **Limiar de similaridade não funcionou:** perguntas próximas do tema, mas fora da lei, chegaram a 0,54 de
  similaridade, contra 0,56 da pergunta correta de menor nota. A recusa depende do modelo seguir a instrução.
- **Modelo pequeno:** o `gemma3:12b` local pode errar mesmo com os trechos certos. A checagem de citações
  confere de onde veio a citação, não se o conteúdo está certo.
- **A lei muda:** o texto em `data/lgpd.txt` foi copiado do site do Planalto em novembro de 2026. Para os artigos
  que aparecem com várias redações na página, o programa usa a última, descarta artigos marcados como revogados
  e, no Art. 5, mantém só a última redação de cada inciso. Essa regra foi validada por amostragem, não artigo a artigo.
- **Nota inconsistente na fonte:** na cópia, o Art. 55-A cita a "Lei nº 15.452, de 2026" e o Art. 55-C cita a
  "Lei nº 15.352, de 2026". Não verifiquei qual está correta, e o texto foi mantido como estava.
- A busca direta por número reconhece só o primeiro artigo mencionado na pergunta.

## Como rodar

Requisitos: Python 3, [Ollama](https://ollama.com) instalado e rodando, e uma GPU com memória suficiente para o
modelo (testado com RTX 4070 Super, 12 GB).

```bash
ollama pull gemma3:12b
ollama pull bge-m3

python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash). No Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python ingest.py                 # gera data/index.json
python ask.py "Quais são os direitos do titular dos dados?"
python avaliacao.py              # avalia a busca
python avaliacao_ponta_a_ponta.py  # avalia recusa e citações com o modelo
```

## Arquivos

- `ingest.py`: quebra a lei, gera os vetores e salva o índice.
- `ask.py`: busca, resposta e verificação de citações.
- `avaliacao.py` e `avaliacao_ponta_a_ponta.py`: conjuntos de avaliação.
- `data/lgpd.txt`: texto da lei (fonte: Planalto).
