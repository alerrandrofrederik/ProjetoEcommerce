# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

Educational data engineering project ("Jornada de Dados") covering the full modern data stack:
- **Day 2 (Python):** EL pipeline — extract Parquet files from a Supabase S3-compatible Data Lake and load into PostgreSQL
- **Day 3 (dbt):** Medallion architecture transformations (Bronze → Silver → Gold)
- **Day 4 (Streamlit):** Analytics dashboard consuming the Gold data marts

**Infrastructure:** Supabase (PostgreSQL + S3-compatible Storage). Credentials live in `.env` (see `.env.example`). A read-only Supabase MCP server is connected via `.mcp.json`.

---

## Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux

# Install Python/pipeline dependencies
pip install -r requirements.txt

# Install dbt adapter (not in requirements.txt)
pip install dbt-postgres

# Install dashboard dependencies
pip install -r case-01-dashboard/requirements.txt
```

Configure `~/.dbt/profiles.yml` for the dbt project:

```yaml
Ecommerce:
  outputs:
    dev:
      type: postgres
      host: <supabase-host>
      port: 5432
      dbname: postgres
      schema: public
      user: <user>
      pass: <password>
      threads: 1
  target: dev
```

---

## Python Ingest Scripts

Scripts in `src/` implement an EL pipeline: Supabase Storage (S3) → PostgreSQL.

```bash
# Run the complete pipeline (loads all 4 tables: produtos, clientes, vendas, preco_competidores)
python src/exemplo-03-projeto-completo.py

# Individual learning examples (in order)
python src/exemplos/exemplo-00-aquecimento-fundamentos.py
python src/exemplos/exemplo-01-ler-datalake-parquet.py
python src/exemplos/exemplo-02-salvar-banco-dados.py
```

**Critical detail in `exemplo-03-projeto-completo.py`:** Before calling `df.to_sql(..., if_exists="replace")`, the script issues `DROP TABLE IF EXISTS "<tabela>" CASCADE` to remove any dbt-built views (bronze/silver) that depend on the raw table. Without CASCADE the load will fail if dbt has been run beforehand.

---

## dbt Project

> All dbt commands must be run from inside the `Ecommerce/` directory.

```bash
cd Ecommerce

dbt debug                        # Test DB connection
dbt run                          # Run all models
dbt run --select bronze.*        # Run one layer only
dbt run --select silver.*
dbt run --select gold.*
dbt run --select <model_name>    # Run a single model
dbt test                         # Run data quality tests
dbt compile                      # Compile SQL without executing
dbt docs generate && dbt docs serve   # Browse lineage at http://localhost:8080
```

---

## Streamlit Dashboard

```bash
# Copy and fill credentials
cp case-01-dashboard/.env.example case-01-dashboard/.env

# Run the dashboard
streamlit run case-01-dashboard/app.py
# Opens at http://localhost:8501
```

The dashboard uses `SUPABASE_*` env vars (host, port, db, user, password) — different from the root `.env` which uses `DATABASE_URL` for the EL pipeline.

---

## Architecture: Medallion Layers

Raw tables (`public` schema) are loaded by the Python scripts, then dbt transforms them:

| Layer | Materialization | Schema | What it does |
|-------|----------------|--------|--------------|
| **Bronze** | VIEW | `bronze` | Pass-through copy of raw tables — no transformations |
| **Silver** | VIEW | `silver` | Cleans and enriches: adds `faixa_preco`, `receita_total`, temporal dimensions (`ano_venda`, `mes_venda`, `dia_venda`, `hora_venda`), converts timestamps |
| **Gold** | TABLE | `gold` | Business KPIs ready for consumption |

**Gold data marts** (full schemas, columns, business rules, and sample queries are in `app/database.md`):

| Model | Table | Domain |
|-------|-------|--------|
| `gold.vendas_temporais` | Sales time-series by day/hour | Granularity: 1 row per `data_venda` + `hora_venda` |
| `gold.clientes_segmentacao` | Customer segmentation: VIP (≥ R$10k), TOP_TIER (≥ R$5k), REGULAR | Granularity: 1 row per customer |
| `gold.precos_competitividade` | Price positioning vs. Mercado Livre, Amazon, Shopee, Magalu | Granularity: 1 row per product with competitor data |

**Schema naming:** `Ecommerce/macros/generate_schema_name.sql` overrides dbt's default `{target}_{custom}` pattern to return just the custom schema name as-is, so layers land in `bronze`, `silver`, `gold` — not `public_bronze` etc.

**Lineage:** `silver_vendas` is the hub — it feeds all three Gold models. Cross-domain joins must go through silver tables.

---

## Raw Data Model

Four source tables in `public` schema (defined in `Ecommerce/models/_sources.yml`):

| Table | Rows | Key columns |
|-------|------|-------------|
| `produtos` | ~215 | `id_produto`, `nome_produto`, `categoria`, `marca`, `preco_atual` |
| `clientes` | ~50 | `id_cliente`, `nome_cliente`, `estado` |
| `vendas` | ~3,020 | `id_venda`, `data_venda`, `id_cliente`, `id_produto`, `canal_venda`, `quantidade`, `preco_unitario` |
| `preco_competidores` | ~728 | `id_produto`, `nome_concorrente`, `preco_concorrente`, `data_coleta` |

---

## Dashboard Architecture (`case-01-dashboard/app.py`)

Three-page Streamlit app. Key patterns used throughout:

- **`@st.cache_resource` on `get_connection()`** — reusable psycopg2 connection pool; auto-reconnects on failure
- **`@st.cache_data(ttl=300)` on `run_query(sql)`** — 5-min query cache; sidebar "Atualizar dados" button calls `run_query.clear()` to force refresh
- **`fmt_currency(v)`** — returns Brazilian format `R$ 1.234,56`; always use this for monetary values, never raw f-strings
- Each page function (`show_vendas`, `show_clientes`, `show_pricing`) wraps its `run_query` call in `try/except` and shows `st.error()` on connection failure, `st.info()` on empty results after filtering

Page-to-table mapping:
- `show_vendas()` → `gold.vendas_temporais` — filter by `mes_venda`; charts: line (daily), bar (weekday order fixed: Segunda→Domingo), bar (hourly)
- `show_clientes()` → `gold.clientes_segmentacao` — filter by `segmento_cliente` on detail table; `ranking_receita <= 10` for top-10 chart
- `show_pricing()` → `gold.precos_competitividade` — `st.multiselect` on `categoria` filters all visuals; scatter uses `receita_total` as bubble size; alert table shows only `MAIS_CARO_QUE_TODOS`
