"""
============================================
EXEMPLO 2: Salvar Dados no Banco de Dados PostgreSQL
============================================
Conceito: Salvar dados processados no PostgreSQL usando pandas
Pergunta: Como salvar dados processados em um banco PostgreSQL?

NESTE EXEMPLO VOCÊ APRENDE:
- Como conectar com PostgreSQL usando pandas
- Como salvar DataFrame em tabela SQL
- Por que pandas serve para ler, processar E salvar dados
"""

# Instalar: pip install sqlalchemy psycopg2-binary boto3 pandas pyarrow
import io
import boto3
import pandas as pd
from sqlalchemy import create_engine, text

# ============================================
# PASSO 1: Ler vendas.parquet do DataLake
# ============================================

# Configurações do DataLake (mesmas do exemplo-01)
S3_ENDPOINT_URL = "https://XXXX.storage.supabase.co/storage/v1/s3"
AWS_REGION = "us-west-2"
AWS_ACCESS_KEY_ID = "XXXX"
AWS_SECRET_ACCESS_KEY = "XXXXX"
BUCKET_NAME = "XXXX"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

FILE_KEY = "vendas.parquet"
response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_KEY)
parquet_bytes = response["Body"].read()

# Converter Parquet para DataFrame
df_vendas = pd.read_parquet(io.BytesIO(parquet_bytes))

print(f"📥 Lido do DataLake: {len(df_vendas)} linhas")

# ============================================
# PASSO 2: Salvar no PostgreSQL
# ============================================

# Configurações do PostgreSQL (Supabase)
# Usar postgresql+psycopg2:// ao invés de postgresql://
DATABASE_URL = "postgresql+psycopg2://xxxx"

# Criar engine de conexão
engine = create_engine(DATABASE_URL)

# Salvar DataFrame em tabela PostgreSQL
# if_exists: 'replace' (substitui), 'append' (adiciona), 'fail' (erro se existir)
df_vendas.to_sql(
    "vendas",  # Nome da tabela
    engine,  # Engine de conexão
    if_exists="replace",  # Substituir se existir
    index=False  # Não salvar índice
)

print("💾 Tabela 'vendas' salva no PostgreSQL")

# Ler dados salvos para verificar
# SQLAlchemy 2.x: usar text() e connection explícita em read_sql_query
with engine.connect() as conn:
    df_verificacao = pd.read_sql_query(text("SELECT * FROM vendas"), conn)
print(f"✅ Verificação: {len(df_verificacao)} linhas no banco")
print(df_verificacao.head())

# ============================================
# OUTRAS OPERAÇÕES COM PANDAS E SQL
# ============================================

# Executar query e trazer para pandas
query = """
SELECT
    COUNT(*) as total_vendas,
    SUM(quantidade) as total_quantidade
FROM vendas
"""
with engine.connect() as conn:
    df_agregado = pd.read_sql_query(text(query), conn)
print(df_agregado)

# ============================================
# APPEND: adicionar novas linhas sem apagar as existentes
# ============================================
# Use 'append' quando estiver fazendo carga incremental
# (ex: cargas diárias adicionando linhas novas à tabela)
df_vendas.to_sql(
    "vendas",
    engine,
    if_exists="append",  # Adiciona ao final, não substitui
    index=False,
)

# Fechar conexão
engine.dispose()
