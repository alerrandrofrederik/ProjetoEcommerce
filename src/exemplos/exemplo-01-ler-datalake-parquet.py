"""
============================================
EXEMPLO 1: Conectar com DataLake e Ler Parquet
============================================
Conceito: Conectar com DataLake usando boto3 e ler arquivos Parquet
Pergunta: Como ler dados de um DataLake usando a API S3?
"""

# Instalar: pip install boto3 pandas pyarrow
import io  # Trabalha com dados "em memória" (bytes que viram "arquivo")
import boto3
import pandas as pd

# Configurações do DataLake
S3_ENDPOINT_URL = "https://XXXX.storage.supabase.co/storage/v1/s3"
AWS_REGION = "us-west-2"
AWS_ACCESS_KEY_ID = "XXXX"
AWS_SECRET_ACCESS_KEY = "XXXXX"
BUCKET_NAME = "XXXX"

# Criar cliente S3
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Listar arquivos no bucket
# response é um dicionário; response["Contents"] é uma lista de dicionários
# Cada item tem chaves como "Key" (nome do arquivo), "Size", "LastModified"...
response = s3.list_objects(Bucket=BUCKET_NAME)

# Forma 1 (didática): for tradicional
arquivos = []
for obj in response["Contents"]:
    arquivos.append(obj["Key"])

# Forma 2 (mais curta - "list comprehension"): mesmo resultado em uma linha
# arquivos = [obj["Key"] for obj in response["Contents"]]

print(f"Arquivos no bucket: {arquivos}")

# Baixar arquivo Parquet
FILE_KEY = "vendas.parquet"
response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_KEY)
parquet_bytes = response["Body"].read()  # bytes brutos do arquivo

# Converter Parquet para DataFrame
# pandas espera um "arquivo"; como temos só bytes na memória,
# io.BytesIO finge ser um arquivo pra ele conseguir ler.
df_vendas = pd.read_parquet(io.BytesIO(parquet_bytes))

# ============================================
# EXPLORANDO DADOS COM PANDAS
# ============================================
# IMPORTANTE: em script .py, df.head() sozinho NÃO exibe nada.
# Precisamos de print() para ver o resultado no terminal.
# (Em notebook/Jupyter o print é automático)

# Visualizar primeiras linhas
print(df_vendas.head())

# Visualizar últimas linhas
print(df_vendas.tail())

# Informações do DataFrame (tipos, memória, etc)
df_vendas.info()  # info() já imprime sozinho

# Estatísticas descritivas (média, mediana, desvio padrão, etc)
print(df_vendas.describe())

# Estatísticas de uma coluna específica
print(df_vendas["preco_unitario"].describe())

# Contar valores únicos
print(df_vendas["id_produto"].value_counts())

# Contar valores únicos com percentual
print(df_vendas["id_produto"].value_counts(normalize=True))

# Agrupar e agregar dados
# Exemplo: Preço médio por produto
print(df_vendas.groupby("id_produto")["preco_unitario"].mean())

# Múltiplas agregações
print(df_vendas.groupby("id_produto")["preco_unitario"].agg(["mean", "min", "max", "count"]))

# Agrupar por múltiplas colunas
print(df_vendas.groupby(["id_produto", "id_cliente"])["quantidade"].sum())

# Filtrar dados
# Vendas com preço maior que 100
print(df_vendas[df_vendas["preco_unitario"] > 100])

# Filtrar por múltiplas condições
print(df_vendas[(df_vendas["preco_unitario"] > 100) & (df_vendas["quantidade"] > 1)])

# Ordenar dados
print(df_vendas.sort_values("preco_unitario", ascending=False))

# Ordenar por múltiplas colunas
print(df_vendas.sort_values(["id_produto", "preco_unitario"], ascending=[True, False]))

# Selecionar colunas específicas
print(df_vendas[["id_produto", "quantidade", "preco_unitario"]])

# Criar nova coluna calculada
df_vendas["receita"] = df_vendas["quantidade"] * df_vendas["preco_unitario"]

# Contar linhas e colunas
print(len(df_vendas))   # Número de linhas
print(df_vendas.shape)  # (linhas, colunas)

# Verificar valores únicos
print(df_vendas["id_produto"].unique())
print(df_vendas["id_produto"].nunique())  # Quantidade de valores únicos

# Verificar valores faltantes
print(df_vendas.isnull().sum())

# Verificar duplicatas
print(df_vendas.duplicated().sum())

# Top N valores
print(df_vendas.nlargest(10, "preco_unitario"))   # Top 10 preços mais altos
print(df_vendas.nsmallest(10, "preco_unitario"))  # Top 10 preços mais baixos

# Converter data_venda para datetime (se necessário)
df_vendas["data_venda"] = pd.to_datetime(df_vendas["data_venda"])

# Agrupar por data e calcular média
print(df_vendas.groupby(df_vendas["data_venda"].dt.date)["preco_unitario"].mean())
