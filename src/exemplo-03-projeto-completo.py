"""
============================================
EXEMPLO 3: Projeto Completo - DataLake → Banco
============================================
Conceito: Pipeline completo de ingestão de dados
Pergunta: Como fazer um pipeline completo: ler do DataLake e salvar no banco?

NESTE EXEMPLO VOCÊ APRENDE:
- Como combinar todos os conceitos aprendidos
- Pipeline completo: DataLake → PostgreSQL (sem processamento)
- Salvar exatamente o que vem do Parquet
- Por que Python é essencial para engenharia de dados

ESTRUTURA DIDÁTICA:
- PARTE 1.A: Ler UM Parquet do DataLake (io + boto3 + pandas)
- PARTE 1.B: Salvar essa tabela no PostgreSQL (sqlalchemy)
- PARTE 2:   Refatorar tudo com FOR para as 4 tabelas
"""

# ============================================
# ============================================
# PARTE 1.A: Ler UM Parquet do DataLake
# ============================================
# ============================================
# Aqui só precisamos de 3 libs:
# - io     → para tratar os bytes que vêm do S3
# - boto3  → para conversar com o DataLake (S3)
# - pandas → para transformar o Parquet em DataFrame

import io
import os

import boto3
import pandas as pd
from dotenv import load_dotenv

# Instalar: pip install boto3 pandas pyarrow python-dotenv
# Carregar variáveis do arquivo .env (nunca suba credenciais no código!)
load_dotenv()

# Configurações do DataLake lidas do .env
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Criar cliente S3
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# --- Teste de conexão: listar arquivos no bucket ---
# Antes de processar tabela por tabela, vamos confirmar que a conexão
# com o DataLake está funcionando listando todos os arquivos disponíveis.
response = s3.list_objects(Bucket=BUCKET_NAME)
arquivos = [obj["Key"] for obj in response["Contents"]]
print("📂 Arquivos encontrados no DataLake:")
print(arquivos)

# # --- Baixar o arquivo Parquet de UMA tabela (produtos) ---
# print("\n📥 Baixando produtos.parquet do DataLake...")

# file_key = "produtos.parquet"
# response = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
# parquet_bytes = response["Body"].read()

# # --- Converter bytes → DataFrame ---
# df_produtos = pd.read_parquet(io.BytesIO(parquet_bytes))
# print(f"✅ produtos: {len(df_produtos)} linhas carregadas")


# ============================================
# ============================================
# PARTE 1.B: Salvar essa tabela no PostgreSQL
# ============================================
# ============================================
# Agora que já temos o DataFrame em memória, falta enviar pro banco.
# Para isso usamos:
# - sqlalchemy → para criar a "engine" de conexão com o PostgreSQL
# (o pandas já sabe usar essa engine no .to_sql())

from sqlalchemy import create_engine, text

# Instalar: pip install sqlalchemy psycopg2-binary
# DATABASE_URL lida do .env — usa postgresql+psycopg2:// (driver explícito)
DATABASE_URL = os.getenv("DATABASE_URL")

# Criar engine de conexão com o PostgreSQL
engine = create_engine(DATABASE_URL)

# # --- Salvar produtos no PostgreSQL ---
# print("\n💾 Salvando produtos no PostgreSQL...")

# with engine.begin() as conn:
#     conn.execute(text('DROP TABLE IF EXISTS "produtos" CASCADE'))
# df_produtos.to_sql(
#     "produtos",            # Nome da tabela no banco
#     engine,                # Engine de conexão
#     if_exists="replace",   # Substituir se existir
#     index=False,           # Não salvar índice do pandas
# )
# print(f"✅ produtos: {len(df_produtos)} linhas salvas no banco")

# # --- Verificar se os dados foram salvos ---
# with engine.connect() as conn:
#     df_verificacao = pd.read_sql_query(
#         text("SELECT COUNT(*) as total FROM produtos"), conn
#     )
# total = df_verificacao["total"].iloc[0]
# print(f"📊 Verificação: produtos tem {total} linhas no banco")

# 🤔 PROBLEMA: e se tivéssemos 4, 10 ou 100 tabelas?
# Copiar e colar esse bloco várias vezes é repetitivo e fácil de errar.
# É aqui que o FOR entra: ele repete o mesmo bloco para cada tabela.


# ============================================
# ============================================
# PARTE 2: Refatorando com FOR para 4 tabelas
# ============================================
# ============================================
# Agora que você entendeu o pipeline com UMA tabela,
# vamos usar FOR para processar AS QUATRO tabelas
# com o MESMO código que escrevemos acima.

print("\n" + "=" * 50)
print("PARTE 2: Pipeline para as 4 tabelas (com FOR)")
print("=" * 50)

# Lista com os nomes das 4 tabelas que vamos carregar
TABELAS = ["produtos", "clientes", "vendas", "preco_competidores"]

# Dicionário vazio onde vamos guardar os DataFrames
# Chave = nome da tabela, Valor = DataFrame com os dados
dataframes = {}

# --- FOR 1: Baixar cada tabela do DataLake ---
# Na 1ª volta: tabela = "produtos"
# Na 2ª volta: tabela = "clientes"
# Na 3ª volta: tabela = "vendas"
# Na 4ª volta: tabela = "preco_competidores"
for tabela in TABELAS:
    print(f"📥 Baixando {tabela}.parquet do DataLake...")

    # Montar o nome do arquivo: "produtos" → "produtos.parquet"
    file_key = f"{tabela}.parquet"

    # Baixar o arquivo do S3 (mesmo código da PARTE 1.A, mas com variável)
    response = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    parquet_bytes = response["Body"].read()

    # Converter bytes → DataFrame e guardar no dicionário
    dataframes[tabela] = pd.read_parquet(io.BytesIO(parquet_bytes))

    print(f"✅ {tabela}: {len(dataframes[tabela])} linhas carregadas")

# Resultado: dataframes = {
#   "produtos": DataFrame com dados de produtos,
#   "clientes": DataFrame com dados de clientes,
#   "vendas": DataFrame com dados de vendas,
#   "preco_competidores": DataFrame com dados de preços
# }

# --- FOR 2: Salvar cada tabela no PostgreSQL ---
# .items() retorna pares (chave, valor) → (nome_tabela, dataframe)
# Na 1ª volta: tabela = "produtos", df = DataFrame de produtos
# Na 2ª volta: tabela = "clientes", df = DataFrame de clientes
# Na 3ª volta: tabela = "vendas", df = DataFrame de vendas
# Na 4ª volta: tabela = "preco_competidores", df = DataFrame de preços
for tabela, df in dataframes.items():
    print(f"💾 Salvando {tabela} no PostgreSQL...")

    # DROP CASCADE antes do replace para remover views dependentes (ex: bronze.*, silver.*)
    # sem isso, o to_sql falha quando há views do dbt construídas sobre a tabela
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{tabela}" CASCADE'))

    df.to_sql(
        tabela,                # Nome da tabela no banco
        engine,                # Engine de conexão
        if_exists="replace",   # Substituir se existir
        index=False,           # Não salvar índice do pandas
    )

    print(f"✅ {tabela}: {len(df)} linhas salvas no banco")

# --- FOR 3: Verificar se os dados foram salvos corretamente ---
# Agora lemos DO BANCO para confirmar que tudo chegou.
# NOTA: usamos f-string para montar o SQL porque `tabela` vem de uma
# constante interna (TABELAS). Em produção, NUNCA interpole input de
# usuário direto no SQL — isso abre brecha de SQL injection. Para input
# externo, use parâmetros (ex: pd.read_sql_query(sql, conn, params=...)).
print("\n📊 Verificação final:")
for tabela in TABELAS:
    with engine.connect() as conn:
        df_verificacao = pd.read_sql_query(
            text(f"SELECT COUNT(*) as total FROM {tabela}"), conn
        )
    total = df_verificacao["total"].iloc[0]
    print(f"  ✅ {tabela}: {total} linhas no banco")

# Fechar conexão
engine.dispose()

# ============================================
# RESUMO: Pipeline Completo
# ============================================
# PARTE 1.A — Ler 1 Parquet (io + boto3 + pandas):
#   1. ✅ Listou arquivos no DataLake
#   2. ✅ Baixou produtos.parquet
#   3. ✅ Converteu para DataFrame
#
# PARTE 1.B — Salvar essa tabela (sqlalchemy):
#   1. ✅ Criou engine de conexão com Postgres
#   2. ✅ Salvou produtos no banco
#   3. ✅ Conferiu o COUNT no banco
#
# PARTE 2 — Mesmo pipeline para 4 tabelas (com FOR):
#   1. ✅ FOR 1: baixou produtos, clientes, vendas, preco_competidores
#   2. ✅ FOR 2: DROP CASCADE + salvou todas no PostgreSQL
#   3. ✅ FOR 3: verificou no banco
#
# 💡 LIÇÃO: o FOR não muda a lógica, só REPETE o mesmo bloco
# para cada item da lista. Escreva primeiro para 1 caso,
# depois transforme em loop quando precisar repetir.
#
# Este é o fluxo completo de ingestão de dados:
# EXTRACTION → LOADING (EL)
# Dados salvos exatamente como vêm do Parquet
