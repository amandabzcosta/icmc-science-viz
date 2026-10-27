# icmc-science-viz

Exploração visual da produção científica do ICMC-USP (São Carlos) a partir da OpenAlex.
Projeto da disciplina SCC0252 – Visualização Computacional (ICMC-USP, 2026/2).

Autora: Amanda Bezerra da Costa — nº USP 12680861

## Instalação

Testado com Python 3.13 (versões das bibliotecas fixadas em `requirements.txt`). Se `python` não for reconhecido no Windows mas houver Anaconda instalado, use o caminho completo (ex.: `C:\Users\<usuário>\anaconda3\python.exe`).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha `OPENALEX_API_KEY` (chave grátis em https://openalex.org/settings/api).

## Etapas

### M0 — Contagem das variantes de afiliação

```bash
python src/collect/count_affiliation_variants.py
python src/collect/count_affiliation_variants.py --ano-inicio 2010 --ano-fim 2026
```

Imprime quantas obras casam com cada variante definida em `config.yaml` e o consumo de orçamento da API.
Use `--escopo` para restringir aos anos e tipos do `config.yaml`.

### M1 — Coleta e validação da afiliação

```bash
python src/collect/collect_openalex.py          # baixa (com cache) e une as variantes
python src/collect/collect_openalex.py --so-unir   # só refaz a união a partir do cache
python src/collect/validate_affiliation.py      # resumo + amostra manual em docs/validacao_afiliacao.md
```

- Cache: `data/raw/obras/<variante>/<ano>.jsonl` (anos já baixados são pulados).
- Resultado: `data/raw/obras_unidas.jsonl` (uma obra por linha, com `matched_by`).
- Consumo de orçamento: `data/raw/log_coleta.jsonl`.

### M2 — Tabelas limpas, rede e comunidades

```bash
python src/process/build_tables.py     # obras, autorias, autores, tópicos, cobertura
python src/process/build_network.py    # arestas, comunidades (Louvain), métricas de ponte
```

Saídas em `data/processed/` (Parquet). Os números da limpeza ficam em `limpeza.json`,
a cobertura dos campos em `cobertura.csv` e o resumo da rede em `rede_resumo.json`.

### M3 — Aplicativo (visualizações V1–V4)

```bash
python app/app.py      # abre em http://127.0.0.1:8050 (funciona offline)
python src/process/evidencias_q1_q3.py   # números que respondem Q1–Q3
```

Visões: rede de coautoria (V1), autores-ponte (V4), evolução das áreas (V2) e hierarquia de tópicos (V3).
Nesta entrega cada interação afeta só a própria visão. Cada visão tem "Ver os dados em tabela".

### M4 — Acessibilidade e entrega

```bash
python src/report/simular_daltonismo.py report/entrega1/figuras/app_visao_geral.png  # protan/deutan/tritan
python src/empacotar.py --nome entrega1     # gera dist/icmc-science-viz_entrega1.zip
```

O pacote leva código, documentação, `data/processed/` e o conjunto coletado
(`data/raw/obras_unidas.jsonl`), mas nunca o `.env`. Para refazer só o processamento
a partir do pacote (sem chave da API): `build_tables.py` → `build_network.py` → `app/app.py`.

### Figuras individuais (slides e relatório)

```bash
python src/report/gerar_figuras.py                  # todas as visões, perfis slide e relatório
python src/report/gerar_figuras.py --perfil slide --so v3_treemap
python src/report/gerar_figuras.py --com-app        # inclui o print da tela inteira do app
```

Cada visão é salva sozinha em `report/entrega1/figuras/individuais/<perfil>/`
(slide: 2560 × 1440; relatório: 2460 × 1680), com as mesmas funções de figura do app.
Requer Microsoft Edge ou Google Chrome instalado (usado sem janela para gerar o PNG).

## Estrutura

- `config.yaml` — parâmetros de coleta, rede e embeddings
- `src/collect/` — scripts de consulta à OpenAlex
- `src/process/` — limpeza, rede, embeddings, exportação para o app
- `data/raw/` (cache da coleta, fora do git) e `data/processed/`
- `app/` — aplicação Dash
- `docs/` — decisões, validação da afiliação, perguntas de arguição
- `report/` — relatórios das entregas
