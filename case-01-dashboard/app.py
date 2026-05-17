import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    layout="wide",
    page_title="E-commerce Analytics",
    page_icon="🛒",
)

# ── Conexão ──────────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_HOST"),
        port=int(os.getenv("SUPABASE_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB", "postgres"),
        user=os.getenv("SUPABASE_USER"),
        password=os.getenv("SUPABASE_PASSWORD"),
    )


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    try:
        conn = get_connection()
        return pd.read_sql_query(sql, conn)
    except Exception:
        get_connection.clear()
        conn = get_connection()
        return pd.read_sql_query(sql, conn)


# ── Formatação brasileira ─────────────────────────────────────────────────────

def fmt_currency(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "R$ -"
    v = float(value)
    base = f"{v:,.2f}"          # "1,234,567.89"
    parts = base.split(".")
    integer_part = parts[0].replace(",", ".")
    decimal_part = parts[1]
    return f"R$ {integer_part},{decimal_part}"


def fmt_number(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    v = int(float(value))
    return f"{v:,}".replace(",", ".")


def fmt_percent(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    v = float(value)
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%".replace(".", ",")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🛒 E-commerce Analytics")
    page = st.radio(
        "Navegação",
        ["📈 Vendas", "👥 Clientes", "🏷️ Pricing"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🔄 Atualizar dados"):
        run_query.clear()
        st.rerun()
    st.caption("Cache: 5 min. Clique para forçar atualização.")


# ── Página 1: Vendas ──────────────────────────────────────────────────────────

def show_vendas():
    st.header("📈 Vendas")

    mes_opcoes = {
        "Todos os meses": None,
        "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
        "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
        "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
    }
    mes_label = st.selectbox("Filtrar por mês", list(mes_opcoes.keys()))
    mes = mes_opcoes[mes_label]

    where = f"WHERE mes_venda = {mes}" if mes else ""

    with st.spinner("Carregando dados de vendas..."):
        try:
            df = run_query(f"""
                SELECT *
                FROM gold.vendas_temporais
                {where}
            """)
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados. Verifique as credenciais no .env.\n\n`{e}`")
            return

    if df.empty:
        st.info("Nenhum dado encontrado para o filtro selecionado.")
        return

    # KPIs
    receita_total = df["receita_total"].sum()
    total_vendas = df["total_vendas"].sum()
    ticket_medio = receita_total / total_vendas if total_vendas > 0 else 0
    clientes_unicos = df["total_clientes_unicos"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Total", fmt_currency(receita_total))
    c2.metric("Total de Vendas", fmt_number(total_vendas))
    c3.metric("Ticket Médio", fmt_currency(ticket_medio))
    c4.metric("Clientes Únicos", fmt_number(clientes_unicos))

    st.divider()

    # Gráfico 1: Receita Diária
    df_diario = (
        df.groupby("data_venda", as_index=False)["receita_total"]
        .sum()
        .sort_values("data_venda")
    )
    fig1 = px.line(
        df_diario,
        x="data_venda",
        y="receita_total",
        title="Receita Diária",
        labels={"data_venda": "Data", "receita_total": "Receita (R$)"},
    )
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns(2)

    # Gráfico 2: Receita por Dia da Semana
    ordem_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    df_semana = (
        df.groupby("dia_semana_nome", as_index=False)["receita_total"]
        .sum()
    )
    df_semana["dia_semana_nome"] = pd.Categorical(
        df_semana["dia_semana_nome"], categories=ordem_semana, ordered=True
    )
    df_semana = df_semana.sort_values("dia_semana_nome")

    fig2 = px.bar(
        df_semana,
        x="dia_semana_nome",
        y="receita_total",
        title="Receita por Dia da Semana",
        labels={"dia_semana_nome": "Dia", "receita_total": "Receita (R$)"},
    )
    col_a.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3: Volume por Hora
    df_hora = (
        df.groupby("hora_venda", as_index=False)["total_vendas"]
        .sum()
        .sort_values("hora_venda")
    )
    fig3 = px.bar(
        df_hora,
        x="hora_venda",
        y="total_vendas",
        title="Volume de Vendas por Hora",
        labels={"hora_venda": "Hora", "total_vendas": "Nº de Vendas"},
    )
    col_b.plotly_chart(fig3, use_container_width=True)


# ── Página 2: Clientes ────────────────────────────────────────────────────────

def show_clientes():
    st.header("👥 Clientes")

    with st.spinner("Carregando dados de clientes..."):
        try:
            df = run_query("SELECT * FROM gold.clientes_segmentacao")
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados.\n\n`{e}`")
            return

    if df.empty:
        st.info("Nenhum dado encontrado.")
        return

    # KPIs
    total_clientes = len(df)
    df_vip = df[df["segmento_cliente"] == "VIP"]
    clientes_vip = len(df_vip)
    receita_vip = df_vip["receita_total"].sum()
    ticket_medio_geral = df["ticket_medio"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Clientes", fmt_number(total_clientes))
    c2.metric("Clientes VIP", fmt_number(clientes_vip))
    c3.metric("Receita VIP", fmt_currency(receita_vip))
    c4.metric("Ticket Médio Geral", fmt_currency(ticket_medio_geral))

    st.divider()

    # Gráficos linha 1
    col_a, col_b = st.columns(2)

    df_seg = df.groupby("segmento_cliente", as_index=False).agg(
        total=("cliente_id", "count"),
        receita=("receita_total", "sum"),
    )

    fig1 = px.pie(
        df_seg,
        names="segmento_cliente",
        values="total",
        title="Distribuição de Clientes por Segmento",
        hole=0.35,
    )
    col_a.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(
        df_seg,
        x="segmento_cliente",
        y="receita",
        title="Receita por Segmento",
        labels={"segmento_cliente": "Segmento", "receita": "Receita (R$)"},
        color="segmento_cliente",
    )
    col_b.plotly_chart(fig2, use_container_width=True)

    # Gráficos linha 2
    col_c, col_d = st.columns(2)

    df_top10 = df[df["ranking_receita"] <= 10].sort_values("receita_total")
    fig3 = px.bar(
        df_top10,
        y="nome_cliente",
        x="receita_total",
        orientation="h",
        title="Top 10 Clientes por Receita",
        labels={"nome_cliente": "Cliente", "receita_total": "Receita (R$)"},
    )
    col_c.plotly_chart(fig3, use_container_width=True)

    df_estado = (
        df.groupby("estado", as_index=False)
        .size()
        .rename(columns={"size": "total"})
        .sort_values("total", ascending=False)
    )
    fig4 = px.bar(
        df_estado,
        x="estado",
        y="total",
        title="Clientes por Estado",
        labels={"estado": "Estado (UF)", "total": "Nº de Clientes"},
    )
    col_d.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # Tabela detalhada com filtro
    segmento_filtro = st.selectbox(
        "Filtrar tabela por segmento",
        ["Todos", "VIP", "TOP_TIER", "REGULAR"],
    )
    df_tabela = df if segmento_filtro == "Todos" else df[df["segmento_cliente"] == segmento_filtro]

    if df_tabela.empty:
        st.info("Nenhum cliente encontrado para o segmento selecionado.")
    else:
        st.dataframe(df_tabela, use_container_width=True, hide_index=True)


# ── Página 3: Pricing ─────────────────────────────────────────────────────────

def show_pricing():
    st.header("🏷️ Pricing")

    with st.spinner("Carregando dados de pricing..."):
        try:
            df = run_query("SELECT * FROM gold.precos_competitividade")
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados.\n\n`{e}`")
            return

    if df.empty:
        st.info("Nenhum dado encontrado.")
        return

    # Filtro de categoria (afeta toda a página)
    categorias = sorted(df["categoria"].unique().tolist())
    selecionadas = st.multiselect("Filtrar por categoria", categorias, default=categorias)
    df = df[df["categoria"].isin(selecionadas)] if selecionadas else df

    if df.empty:
        st.info("Nenhum produto encontrado para as categorias selecionadas.")
        return

    # KPIs
    total_produtos = len(df)
    mais_caros = len(df[df["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"])
    mais_baratos = len(df[df["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS"])
    dif_media = df["diferenca_percentual_vs_media"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Produtos Monitorados", fmt_number(total_produtos))
    c2.metric("Mais Caros que Todos", fmt_number(mais_caros))
    c3.metric("Mais Baratos que Todos", fmt_number(mais_baratos))
    c4.metric("Diferença Média vs Mercado", fmt_percent(dif_media))

    st.divider()

    # Gráficos linha 1
    col_a, col_b = st.columns(2)

    df_class = df.groupby("classificacao_preco", as_index=False).size().rename(columns={"size": "total"})
    fig1 = px.pie(
        df_class,
        names="classificacao_preco",
        values="total",
        title="Posicionamento de Preço vs Concorrência",
        hole=0.35,
    )
    col_a.plotly_chart(fig1, use_container_width=True)

    df_cat = (
        df.groupby("categoria", as_index=False)["diferenca_percentual_vs_media"]
        .mean()
        .sort_values("diferenca_percentual_vs_media", ascending=False)
    )
    df_cat["cor"] = df_cat["diferenca_percentual_vs_media"].apply(
        lambda x: "Mais caro" if x > 0 else "Mais barato"
    )
    fig2 = px.bar(
        df_cat,
        x="categoria",
        y="diferenca_percentual_vs_media",
        color="cor",
        color_discrete_map={"Mais caro": "#E74C3C", "Mais barato": "#27AE60"},
        title="Competitividade por Categoria (%)",
        labels={"categoria": "Categoria", "diferenca_percentual_vs_media": "Dif. % vs Média"},
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
    col_b.plotly_chart(fig2, use_container_width=True)

    # Gráfico Scatter
    fig3 = px.scatter(
        df,
        x="diferenca_percentual_vs_media",
        y="quantidade_total",
        color="classificacao_preco",
        size="receita_total",
        size_max=40,
        hover_name="nome_produto",
        hover_data=["categoria", "marca", "nosso_preco"],
        title="Competitividade × Volume de Vendas",
        labels={
            "diferenca_percentual_vs_media": "Dif. % vs Média Concorrentes",
            "quantidade_total": "Quantidade Vendida",
        },
    )
    fig3.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # Tabela de alertas
    st.subheader("⚠️ Produtos em Alerta — Mais Caros que Todos os Concorrentes")
    df_alerta = df[df["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"][
        ["nome_produto", "categoria", "nosso_preco", "preco_maximo_concorrentes", "diferenca_percentual_vs_media"]
    ].sort_values("diferenca_percentual_vs_media", ascending=False)

    if df_alerta.empty:
        st.success("Nenhum produto está mais caro que todos os concorrentes para as categorias selecionadas.")
    else:
        st.dataframe(df_alerta, use_container_width=True, hide_index=True)


# ── Roteamento ────────────────────────────────────────────────────────────────

if page == "📈 Vendas":
    show_vendas()
elif page == "👥 Clientes":
    show_clientes()
else:
    show_pricing()
