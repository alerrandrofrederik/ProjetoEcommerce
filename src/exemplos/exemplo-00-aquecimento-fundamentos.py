"""
============================================
AQUECIMENTO: Fundamentos de Python
============================================
Conceito: Revisar conceitos fundamentais antes de trabalhar com dados
Pergunta: Por que preciso saber Python básico para trabalhar com dados?
"""

# Print simples
print("Hello World!")

# Print com variáveis
nome = "Jornada de Dados"
print(f"Olá, {nome}")

# Variáveis - String (str)
nome_produto = "Tênis Nike Air Max"
categoria = 'Tênis'

# Variáveis - Int (int)
quantidade = 10
total_produtos = 200

# Lista (list) - Coleção Ordenada
tenis = ["Tênis Nike Air Max", "Tênis Adidas Ultraboost", "Tênis Puma RS-X"]
precos = [599.90, 699.90, 449.90]

# Dicionário (dict) - Pares Chave-Valor
# GUARDE BEM ISSO: Dicionários são perfeitos para armazenar conjuntos de dados!
tenis_nike = {
    "nome": "Tênis Nike Air Max",
    "marca": "Nike",
    "categoria": "Tênis",
    "preco": 599.90,
    "quantidade": 10
}

# Acessar valor de um dicionário pela chave: dicionario["chave"]
# É ASSIM que vamos pegar dados depois! Ex: response["Body"] no S3
print(tenis_nike["nome"])      # "Tênis Nike Air Max"
print(tenis_nike["preco"])     # 599.90
print(tenis_nike["quantidade"])  # 10

# Percorrer chave e valor ao mesmo tempo com .items()
# Vamos usar isso no exemplo-03 para salvar várias tabelas no banco!
for chave, valor in tenis_nike.items():
    print(f"{chave}: {valor}")

# Lista de dicionários - Estrutura mais comum para dados tabulares!
lista_tenis = [
    {"nome": "Tênis Nike Air Max", "marca": "Nike", "preco": 599.90},
    {"nome": "Tênis Adidas Ultraboost", "marca": "Adidas", "preco": 699.90},
    {"nome": "Tênis Puma RS-X", "marca": "Puma", "preco": 449.90},
    {"nome": "Tênis Vans Old Skool", "marca": "Vans", "preco": 399.90},
    {"nome": "Tênis Converse Chuck", "marca": "Converse", "preco": 349.90}
]

# len() - Quantos itens tem a lista?
# Vamos usar muito isso depois: len(df) = quantas linhas tem o DataFrame
print(f"Total de tênis: {len(lista_tenis)}")  # 5

# For loop - Percorrer uma lista
# É assim que iteramos sobre dados no Python!
for tenis_item in lista_tenis:
    print(f"{tenis_item['nome']} - R$ {tenis_item['preco']}")

# For loop com lista simples
tabelas = ["produtos", "clientes", "vendas", "preco_competidores"]
for tabela in tabelas:
    print(f"Processando: {tabela}.parquet")
