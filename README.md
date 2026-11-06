# icmc-science-viz

**Análise visual de colaborações científicas no ICMC-USP (2010–2026)**

App interativo e conjunto de dados sobre a produção científica do Instituto de Ciências
Matemáticas e de Computação da USP (São Carlos): quem publica com quem, como as áreas de pesquisa
evoluem e quais autores fazem a ponte entre grupos diferentes.

Projeto da disciplina SCC0252 – Visualização Computacional (ICMC-USP).
Autora: Amanda Bezerra da Costa.

---

## Sobre o projeto

Cada artigo registra autores, afiliações, temas e citações, mas essa informação não é comumente vista
em conjunto. Este projeto reúne a produção do ICMC numa base única e a explora com visualizações
interativas para responder três perguntas:

1. **Colaboração entre grupos** — quais comunidades de coautoria mais colaboram entre si, e quão coesas são?
2. **Evolução das áreas** — como as áreas e subáreas evoluíram em volume e em impacto?
3. **Autores-ponte** — quem liga grupos diferentes, e essas pessoas se destacam também em citações?

## Os dados

- **Fonte:** [OpenAlex](https://openalex.org), base aberta de metadados científicos, consultada pela API.
- **Como o ICMC é identificado:** a OpenAlex não tem o ICMC como instituição (só a USP inteira).
  Por isso, as obras são buscadas pelo **texto da afiliação** dos autores, com variantes do nome
  em português, inglês e sigla, com e sem acento. Depois, cada autoria é conferida por regras
  sobre o texto normalizado, que toleram erros comuns (acentos quebrados, hifenização,
  abreviações, nome antigo do instituto).
- **Escopo:** 2010–2026; artigos, revisões, trabalhos de conferência, capítulos de livro e preprints.

| Conteúdo | Quantidade |
|---|---:|
| Obras | 4.412 |
| Autores distintos | 6.012 |
| Autores do ICMC | 1.962 |
| Autores na rede de coautoria (componente principal) | 906 |
| Comunidades de coautoria (Louvain) | 20 |
| Domínios / campos / subcampos / tópicos | 4 / 23 / 150 / 648 |

**Tabelas processadas** (`data/processed/`, formato Parquet):

| Arquivo | Uma linha por… | Principais colunas |
|---|---|---|
| `obras.parquet` | obra | título, resumo, ano, tipo, citações, hierarquia de tópicos, nº de autores, colaboração internacional, citações normalizadas e por ano |
| `autorias.parquet` | par obra × autor | autor, posição, afiliação bruta, países, se a autoria é do ICMC |
| `autores.parquet` | autor | nº de obras, citações, primeiro e último ano, se é do ICMC |
| `arestas_coautoria.parquet` | par de autores do ICMC | nº de obras em conjunto e peso fracionário |
| `metricas_autores.parquet` | autor da rede | comunidade, grau, participação, intermediação, constraint de Burt, posição no desenho |
| `comunidades.parquet` | comunidade | tamanho, coesão, tópicos característicos (TF-IDF) |
| `pares_comunidades.parquet` | par de comunidades | nº de obras em conjunto |
| `topicos.parquet` | tópico | domínio > campo > subcampo > tópico, nº de obras |

Arquivos de apoio: `cobertura.csv` (preenchimento de cada campo), `limpeza.json` (obras removidas
em cada etapa), `rede_resumo.json` (tamanho da rede e modularidade) e `autores_fragmentados.csv`
(nomes associados a mais de um identificador).

## As visualizações

O app reúne quatro visualizações. Cada uma tem tooltip, detalhes sob demanda e a opção
"Ver os dados em tabela".

| Visualização | Pergunta | Interações |
|---|---|---|
| **Rede de coautoria** — cor e forma indicam a comunidade; tamanho, o nº de obras | 1 e 3 | zoom, busca por nome, clique para ver métricas e obras mais citadas, colorir por métrica de ponte |
| **Evolução das áreas** — um painel por área (small multiples) | 2 | nº de obras, % do ano ou citações por obra; campo ou subcampo; escala própria ou comum |
| **Hierarquia de tópicos** — treemap colorido por citações por ano | 2 | clicar para descer e subir de nível; obras mais citadas da área |
| **Ranking de autores-ponte** — métrica de ponte e citações lado a lado | 3 | escolher a métrica (participação, intermediação, constraint) e a ordenação |

**Acessibilidade:** a paleta foi validada para daltonismo, e nenhuma informação depende só da cor
(forma do marcador na rede, código da comunidade no ranking, título dos painéis na série temporal).
`src/report/simular_daltonismo.py` gera versões de uma imagem simulando protanopia, deuteranopia e
tritanopia.

## Como executar

### Instalação

Requer Python 3.13 (as versões das bibliotecas estão fixadas em `requirements.txt`).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
```

### Abrir o app

As tabelas processadas já estão no repositório, então basta:

```bash
python app/app.py
```

e abrir http://127.0.0.1:8050. O app funciona sem internet.

### Reproduzir os dados do zero

A coleta precisa de uma chave gratuita da OpenAlex
([openalex.org/settings/api](https://openalex.org/settings/api)). Copie `.env.example` para `.env`
e preencha `OPENALEX_API_KEY`.

```bash
python src/collect/count_affiliation_variants.py --escopo   # quantas obras cada variante encontra
python src/collect/collect_openalex.py                       # coleta (com cache) e une as variantes
python src/collect/validate_affiliation.py                   # resumo e amostra para conferência manual
python src/process/build_tables.py                           # limpeza, novas variáveis, cobertura
python src/process/build_network.py                          # rede, comunidades e métricas de ponte
python src/process/evidencias_q1_q3.py                       # números que respondem às três perguntas
```

- A coleta guarda um cache por variante e por ano em `data/raw/` e pode ser interrompida e retomada.
- O consumo da API fica registrado em `data/raw/log_coleta.jsonl`.
- Com as mesmas versões de bibliotecas, o processamento gera sempre as mesmas tabelas (sementes fixas).

### Gerar imagens das visualizações

```bash
python src/report/gerar_figuras.py                     # todas, em tamanho de slide e de documento
python src/report/gerar_figuras.py --so v3_treemap     # só uma
python src/report/gerar_figuras.py --com-app           # inclui um print da tela inteira do app
```

Cada visualização é salva sozinha, em alta resolução, em `report/entrega1/figuras/individuais/`.
O script usa o Microsoft Edge ou o Google Chrome (sem abrir janela) para gerar as imagens.

### Empacotar código e dados

```bash
python src/empacotar.py --nome <nome>      # gera dist/icmc-science-viz_<nome>.zip
```

O pacote leva o código, as tabelas processadas e o conjunto coletado, mas nunca o `.env`.

## Estrutura do repositório

```
icmc-science-viz/
├── app/                     app Dash
│   ├── app.py               ponto de entrada
│   ├── dados.py             carrega as tabelas e define cores das comunidades
│   ├── tema.py              aparência dos gráficos e tamanhos de exportação
│   ├── componentes.py       cartões, painéis de detalhes e tabelas
│   └── views/               uma visualização por arquivo
├── src/
│   ├── collect/             consulta à OpenAlex e identificação do ICMC
│   ├── process/             limpeza, rede, comunidades e métricas
│   └── report/              imagens das visualizações e simulação de daltonismo
├── data/
│   ├── raw/                 cache da coleta (fora do git)
│   └── processed/           tabelas prontas para o app
├── report/                  imagens geradas
├── config.yaml              parâmetros de coleta, escopo, regras de afiliação e rede
└── requirements.txt
```

## Ferramentas

Python · [Dash](https://dash.plotly.com) e [plotly.py](https://plotly.com/python/) (visualização) ·
pandas · NetworkX (rede, Louvain, centralidades) · scikit-learn (TF-IDF) · OpenAlex API.

## Limitações

- A identificação do ICMC depende do texto de afiliação: autores que declaram apenas
  "Universidade de São Paulo" não são reconhecidos naquela obra.
- Comunidades encontradas pelo algoritmo refletem padrões de coautoria, não grupos de pesquisa formais.
- A cobertura e a classificação temática dependem da OpenAlex; 2026 está incompleto e as citações
  de obras recentes ainda estão crescendo.
