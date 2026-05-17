import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from db import execute_query

load_dotenv()

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


# ── Schemas das tabelas gold (contexto para o Claude) ─────────────────────────

_SCHEMA_CONTEXT = """
Tabelas disponíveis no banco PostgreSQL (schema: gold):

## gold.vendas_temporais
Granularidade: 1 linha por data_venda + hora_venda
Colunas:
- data_venda DATE, ano_venda INT, mes_venda INT, dia_venda INT
- dia_semana_nome VARCHAR  -- valores: Domingo, Segunda, Terça, Quarta, Quinta, Sexta, Sábado
- hora_venda INT  -- 0 a 23
- receita_total NUMERIC  -- SUM(quantidade × preco_unitario)
- quantidade_total INT, total_vendas INT, total_clientes_unicos INT
- ticket_medio NUMERIC  -- AVG da receita por transação individual

## gold.clientes_segmentacao
Granularidade: 1 linha por cliente
Colunas:
- cliente_id VARCHAR, nome_cliente VARCHAR, estado VARCHAR(2)
- receita_total NUMERIC, total_compras INT, ticket_medio NUMERIC
- primeira_compra DATE, ultima_compra DATE
- segmento_cliente VARCHAR  -- valores: VIP (>=R$10k), TOP_TIER (>=R$5k), REGULAR (<R$5k)
- ranking_receita INT  -- 1 = maior receita

## gold.precos_competitividade
Granularidade: 1 linha por produto com dados de concorrentes
Colunas:
- produto_id VARCHAR, nome_produto VARCHAR, categoria VARCHAR, marca VARCHAR
- nosso_preco NUMERIC
- preco_medio_concorrentes NUMERIC, preco_minimo_concorrentes NUMERIC, preco_maximo_concorrentes NUMERIC
- total_concorrentes INT
- diferenca_percentual_vs_media NUMERIC  -- positivo = mais caro que a média
- diferenca_percentual_vs_minimo NUMERIC
- classificacao_preco VARCHAR  -- MAIS_CARO_QUE_TODOS | ACIMA_DA_MEDIA | NA_MEDIA | ABAIXO_DA_MEDIA | MAIS_BARATO_QUE_TODOS
- receita_total NUMERIC, quantidade_total INT
Concorrentes monitorados: Mercado Livre, Amazon, Shopee, Magalu
Categorias: Eletrônicos, Casa, Moda, Games, Cozinha, Beleza, Acessórios
""".strip()

_SYSTEM_CHAT = f"""Você é um analista de dados de um e-commerce brasileiro.
Responda perguntas usando os dados do banco PostgreSQL via a ferramenta executar_sql.
Formate valores monetários em R$ (ex: R$ 1.234,56). Responda em português. Seja conciso e direto.

{_SCHEMA_CONTEXT}"""

_TOOL_SQL = {
    "name": "executar_sql",
    "description": "Executa query SQL SELECT no banco PostgreSQL do e-commerce e retorna os resultados.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Query SQL SELECT ou WITH para executar.",
            }
        },
        "required": ["sql"],
    },
}

_SYSTEM_RELATORIO = """Você é um analista de dados sênior de um e-commerce brasileiro.
Gere um relatório executivo diário para 3 diretores com insights acionáveis.
Cada diretor tem necessidades distintas:
1. Diretor Comercial: receita, vendas, ticket médio e tendências.
2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.
3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.
Regras: seja direto e acionável; cada insight deve sugerir uma ação; use números reais;
formate valores em R$; destaque alertas críticos; máximo 1 página por seção; use Markdown."""


# ── chat ──────────────────────────────────────────────────────────────────────

def chat(pergunta: str) -> str:
    client = _get_client()
    messages = [{"role": "user", "content": pergunta}]

    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_SYSTEM_CHAT,
            tools=[_TOOL_SQL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        df = execute_query(block.input["sql"])
                        result = df.to_markdown(index=False) if not df.empty else "Nenhum resultado encontrado."
                    except Exception as e:
                        result = f"Erro ao executar SQL: {e}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Limite de iterações de tool use atingido."


# ── gerar_relatorio ───────────────────────────────────────────────────────────

def gerar_relatorio() -> str:
    _log("Iniciando geração do relatório...")

    _log("Consultando vendas (últimos 7 dias)...")
    df_vendas = execute_query("""
        SELECT data_venda, dia_semana_nome,
            SUM(receita_total)        AS receita,
            SUM(total_vendas)         AS vendas,
            SUM(total_clientes_unicos) AS clientes,
            ROUND(AVG(ticket_medio)::numeric, 2) AS ticket_medio
        FROM gold.vendas_temporais
        GROUP BY data_venda, dia_semana_nome
        ORDER BY data_venda DESC
        LIMIT 7
    """)

    _log("Consultando clientes...")
    df_clientes = execute_query("""
        SELECT segmento_cliente,
            COUNT(*)                          AS total_clientes,
            ROUND(SUM(receita_total)::numeric, 2)  AS receita_total,
            ROUND(AVG(ticket_medio)::numeric, 2)   AS ticket_medio_avg,
            ROUND(AVG(total_compras)::numeric, 1)  AS compras_avg
        FROM gold.clientes_segmentacao
        GROUP BY segmento_cliente
        ORDER BY receita_total DESC
    """)

    _log("Consultando pricing...")
    df_pricing = execute_query("""
        SELECT classificacao_preco,
            COUNT(*)                                        AS total_produtos,
            ROUND(AVG(diferenca_percentual_vs_media)::numeric, 2) AS dif_media_pct,
            ROUND(SUM(receita_total)::numeric, 2)           AS receita_impactada
        FROM gold.precos_competitividade
        GROUP BY classificacao_preco
        ORDER BY total_produtos DESC
    """)

    _log("Consultando produtos críticos...")
    df_criticos = execute_query("""
        SELECT nome_produto, categoria, nosso_preco,
            preco_medio_concorrentes,
            ROUND(diferenca_percentual_vs_media::numeric, 2) AS dif_pct,
            ROUND(receita_total::numeric, 2)                 AS receita_total
        FROM gold.precos_competitividade
        WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
        ORDER BY diferenca_percentual_vs_media DESC
        LIMIT 10
    """)

    hoje = datetime.now().strftime("%d/%m/%Y")
    user_prompt = f"""Gere o relatório diário com base nos dados abaixo. Data: {hoje}

## Dados de Vendas (últimos 7 dias)
{df_vendas.to_markdown(index=False)}

## Segmentação de Clientes
{df_clientes.to_markdown(index=False)}

## Posicionamento de Preços
{df_pricing.to_markdown(index=False)}

## Produtos Críticos (mais caros que todos os concorrentes)
{df_criticos.to_markdown(index=False) if not df_criticos.empty else "Nenhum produto nesta categoria."}

Gere o relatório com 3 seções:
1. Comercial (para o Diretor Comercial)
2. Customer Success (para a Diretora de CS)
3. Pricing (para o Diretor de Pricing)

Comece com um resumo executivo de 3 linhas antes das seções."""

    _log("Enviando para Claude API...")
    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM_RELATORIO,
        messages=[{"role": "user", "content": user_prompt}],
    )
    relatorio = response.content[0].text

    nome_arquivo = f"relatorio_{datetime.now():%Y-%m-%d}.md"
    Path(nome_arquivo).write_text(relatorio, encoding="utf-8")
    _log(f"Relatório salvo em: {nome_arquivo}")

    return relatorio


# ── enviar_telegram ───────────────────────────────────────────────────────────

def _split_mensagem(texto: str, limite: int = 4096) -> list[str]:
    if len(texto) <= limite:
        return [texto]
    partes = []
    while texto:
        if len(texto) <= limite:
            partes.append(texto)
            break
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(texto[:corte])
        texto = texto[corte:].lstrip("\n")
    return partes


def _post_telegram(token: str, chat_id: str, texto: str, parse_mode: str = None) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def enviar_telegram(texto: str, chat_id: str = None) -> None:
    token = os.getenv("TELEGRAM")
    chat_id = chat_id or os.getenv("CHAT_ID")

    if not token:
        _log("TELEGRAM não configurado — mensagem não enviada.")
        return
    if not chat_id:
        _log("CHAT_ID não configurado — rode 'python bot.py' primeiro e envie /start no Telegram.")
        return

    for parte in _split_mensagem(texto):
        try:
            _post_telegram(token, chat_id, parte, parse_mode="Markdown")
        except urllib.error.HTTPError:
            try:
                _post_telegram(token, chat_id, parte)
            except Exception as e:
                _log(f"Erro ao enviar mensagem: {e}")
        except Exception as e:
            _log(f"Erro ao enviar mensagem: {e}")

    _log(f"Mensagem enviada para chat_id={chat_id}")


# ── salvar_chat_id ────────────────────────────────────────────────────────────

def salvar_chat_id(chat_id: str) -> None:
    chat_id = str(chat_id)
    if os.getenv("CHAT_ID") == chat_id:
        return

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        conteudo = env_path.read_text(encoding="utf-8")
    else:
        conteudo = ""

    if "CHAT_ID=" in conteudo:
        linhas = conteudo.splitlines()
        linhas = [f"CHAT_ID={chat_id}" if l.startswith("CHAT_ID=") else l for l in linhas]
        env_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    else:
        with env_path.open("a", encoding="utf-8") as f:
            f.write(f"\nCHAT_ID={chat_id}\n")

    os.environ["CHAT_ID"] = chat_id
    _log(f"CHAT_ID={chat_id} salvo no .env")


# ── standalone ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        relatorio = gerar_relatorio()
        sys.stdout.buffer.write(("\n" + relatorio + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        enviar_telegram(relatorio)
    except Exception as e:
        _log(f"Erro: {e}")
        raise
