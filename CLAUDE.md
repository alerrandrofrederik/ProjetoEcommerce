# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

Educational data engineering project ("Jornada de Dados — Dia 2 & 3") that teaches:
- **Day 2 (Python):** EL pipeline — extract Parquet files from a Supabase S3-compatible Data Lake and load them into PostgreSQL
- **Day 3 (dbt):** Medallion architecture transformations (Bronze → Silver → Gold) on top of the raw tables loaded by Python

**Infrastructure:** Supabase (PostgreSQL + S3-compatible Storage). Credentials live in `.env` (see `.env.example`). A read-only Supabase MCP server is connected via `.mcp.json`.

---

## Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux

# Install Python dependencies
pip install -r requirements.txt

# Install dbt adapter (not in requirements.txt)
pip install dbt-postgres
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

## Architecture: Medallion Layers

Raw tables (`public` schema) are loaded by the Python scripts, then dbt transforms them through three layers:

| Layer | Materialization | Schema | What it does |
|-------|----------------|--------|--------------|
| **Bronze** | VIEW | `bronze` | Pass-through copy of raw tables — no transformations |
| **Silver** | VIEW | `silver` | Cleans and enriches: adds `faixa_preco`, `receita_total`, temporal dimensions (`ano_venda`, `mes_venda`, `dia_venda`, `hora_venda`), converts timestamps |
| **Gold** | TABLE | per domain (see below) | Business KPIs ready for consumption |

**Gold data marts** (full schemas, columns, business rules, and sample queries are in `app/database.md`):

| Model | Schema | Domain |
|-------|--------|--------|
| `vendas_temporais` | `public_gold_sales` | Sales time-series by day/hour |
| `clientes_segmentacao` | `public_gold_cs` | Customer segmentation: VIP (≥ R$10k), TOP_TIER (≥ R$5k), REGULAR |
| `precos_competitividade` | `public_gold_pricing` | Price positioning vs. Mercado Livre, Amazon, Shopee, Magalu |

**Schema naming:** `Ecommerce/macros/generate_schema_name.sql` overrides dbt's default `{target}_{custom}` pattern to return just the custom schema name as-is, so the layers land in clean schemas (`bronze`, `silver`, etc.) rather than `public_bronze`, `public_silver`.

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

## App (Streamlit Dashboard — WIP)

`app/prd-dashboard.md` contains the full PRD for a 3-page Streamlit dashboard (Vendas / Clientes / Pricing) that reads from the Gold data marts. The app does not exist yet — the PRD is the spec to implement it.

Target file: `case-01-dashboard/app.py`. Connect via `psycopg2` using `SUPABASE_*` env vars. Use `plotly` for charts and format numbers in Brazilian Portuguese (R$ with `.` thousands and `,` decimal).
