"""
Controle de Comércio — App genérico para controle de itens, movimentações e despesas.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
import altair as alt


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "pescados.db")
LOGO_PATH = os.path.join(APP_DIR, "frontend", "icon-192.png")

CATEGORIAS_DESPESA = [
    "Combustível",
    "Frete / Transporte",
    "Aluguel",
    "Embalagem",
    "Funcionário / Mão de obra",
    "Manutenção",
    "Marketing / Publicidade",
    "Impostos / Taxas",
    "Outros",
]


@dataclass(frozen=True)
class DbConfig:
    backend: str
    database_url: str | None = None


def get_db_config() -> DbConfig:
    database_url = None
    try:
        if "DATABASE_URL" in st.secrets:
            database_url = st.secrets["DATABASE_URL"]
    except Exception:
        database_url = None
    database_url = database_url or os.getenv("DATABASE_URL")
    if database_url:
        return DbConfig(backend="postgres", database_url=database_url)
    return DbConfig(backend="sqlite", database_url=None)


@contextmanager
def get_connection():
    cfg = get_db_config()
    if cfg.backend == "postgres":
        import psycopg2
        conn = psycopg2.connect(cfg.database_url)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def rows_to_dicts(cursor, rows):
    if not rows:
        return []
    if isinstance(rows[0], sqlite3.Row):
        return [dict(row) for row in rows]
    cols = [c[0] for c in cursor.description]
    key_map = {
        "precocomprapadrao": "precoCompraPadrao",
        "precovendapadrao": "precoVendaPadrao",
        "produtoid": "produtoId",
        "valortotal": "valorTotal",
        "produtonome": "produtoNome",
        "precounitario": "precoUnitario",
    }
    return [{key_map.get(k, k): v for k, v in dict(zip(cols, row)).items()} for row in rows]


def init_db() -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"

    with get_connection() as conn:
        cur = conn.cursor()

        if cfg.backend == "postgres":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    unidade TEXT NOT NULL DEFAULT 'un',
                    precoCompraPadrao DOUBLE PRECISION NOT NULL DEFAULT 0,
                    precoVendaPadrao DOUBLE PRECISION NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transacoes (
                    id SERIAL PRIMARY KEY,
                    produtoId INTEGER NOT NULL REFERENCES produtos(id),
                    tipo TEXT NOT NULL CHECK(tipo IN ('compra','venda')),
                    quantidade DOUBLE PRECISION NOT NULL DEFAULT 0,
                    unidade TEXT NOT NULL DEFAULT 'un',
                    precoUnitario DOUBLE PRECISION NOT NULL DEFAULT 0,
                    valorTotal DOUBLE PRECISION NOT NULL,
                    data DATE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS despesas (
                    id SERIAL PRIMARY KEY,
                    descricao TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    valor DOUBLE PRECISION NOT NULL,
                    data DATE NOT NULL
                )
            """)
            conn.commit()

            # Migration: add new columns to existing tables
            migrations = [
                "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS unidade TEXT DEFAULT 'un'",
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS quantidade DOUBLE PRECISION DEFAULT 0",
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS unidade TEXT DEFAULT 'un'",
                "ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS precoUnitario DOUBLE PRECISION DEFAULT 0",
            ]
            for sql in migrations:
                try:
                    cur.execute(sql)
                    conn.commit()
                except Exception:
                    conn.rollback()

            # Make old columns nullable so new INSERTs don't need to provide them
            for sql in [
                "ALTER TABLE transacoes ALTER COLUMN pesokg DROP NOT NULL",
                "ALTER TABLE transacoes ALTER COLUMN precokg DROP NOT NULL",
            ]:
                try:
                    cur.execute(sql)
                    conn.commit()
                except Exception:
                    conn.rollback()

            # Migrate data from old pesokg/precokg to new columns
            try:
                cur.execute("""
                    UPDATE transacoes
                    SET quantidade = pesokg,
                        unidade = 'kg',
                        precounitario = precokg
                    WHERE quantidade = 0 AND pesokg IS NOT NULL AND pesokg > 0
                """)
                conn.commit()
            except Exception:
                conn.rollback()

        else:  # SQLite
            cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    unidade TEXT NOT NULL DEFAULT 'un',
                    precoCompraPadrao REAL NOT NULL DEFAULT 0,
                    precoVendaPadrao REAL NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produtoId INTEGER NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('compra','venda')),
                    quantidade REAL NOT NULL DEFAULT 0,
                    unidade TEXT NOT NULL DEFAULT 'un',
                    precoUnitario REAL NOT NULL DEFAULT 0,
                    valorTotal REAL NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (produtoId) REFERENCES produtos(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS despesas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    valor REAL NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.commit()

            for table, col, typ in [
                ("produtos",  "unidade",      "TEXT DEFAULT 'un'"),
                ("transacoes","quantidade",   "REAL DEFAULT 0"),
                ("transacoes","unidade",      "TEXT DEFAULT 'un'"),
                ("transacoes","precoUnitario","REAL DEFAULT 0"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                    conn.commit()
                except Exception:
                    pass

            try:
                cur.execute("""
                    UPDATE transacoes
                    SET quantidade = pesoKg, unidade = 'kg', precoUnitario = precoKg
                    WHERE quantidade = 0 AND pesoKg IS NOT NULL AND pesoKg > 0
                """)
                conn.commit()
            except Exception:
                pass


# ── PRODUTOS ──────────────────────────────────────────────────────────────────

def get_produtos() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, unidade, precoCompraPadrao, precoVendaPadrao FROM produtos ORDER BY nome")
        return rows_to_dicts(cur, cur.fetchall())


def adicionar_produto(nome: str, unidade: str, preco_compra: float, preco_venda: float) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO produtos (nome, unidade, precoCompraPadrao, precoVendaPadrao) VALUES ({ph},{ph},{ph},{ph})",
            (nome, unidade, preco_compra, preco_venda),
        )
        conn.commit()


def atualizar_produto(pid: int, nome: str, unidade: str, preco_compra: float, preco_venda: float) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE produtos SET nome={ph}, unidade={ph}, precoCompraPadrao={ph}, precoVendaPadrao={ph} WHERE id={ph}",
            (nome, unidade, preco_compra, preco_venda, pid),
        )
        conn.commit()


def excluir_produto(pid: int) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM produtos WHERE id={ph}", (pid,))
        conn.commit()


# ── TRANSAÇÕES ────────────────────────────────────────────────────────────────

def get_transacoes() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.data, t.tipo, t.quantidade, t.unidade,
                   t.precoUnitario, t.valorTotal,
                   p.nome AS produtoNome
            FROM transacoes t
            JOIN produtos p ON p.id = t.produtoId
            ORDER BY t.data DESC, t.id DESC
        """)
        return rows_to_dicts(cur, cur.fetchall())


def get_resumo_itens() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                p.id, p.nome, p.unidade,
                COALESCE(SUM(CASE WHEN t.tipo='compra' THEN t.quantidade END), 0) AS qtd_compra,
                COALESCE(SUM(CASE WHEN t.tipo='venda'  THEN t.quantidade END), 0) AS qtd_venda,
                COALESCE(SUM(CASE WHEN t.tipo='compra' THEN t.valorTotal END), 0) AS valor_compra,
                COALESCE(SUM(CASE WHEN t.tipo='venda'  THEN t.valorTotal END), 0) AS valor_venda
            FROM produtos p
            LEFT JOIN transacoes t ON t.produtoId = p.id
            GROUP BY p.id, p.nome, p.unidade
            ORDER BY p.nome
        """)
        rows = rows_to_dicts(cur, cur.fetchall())
    for r in rows:
        r["estoque"] = r["qtd_compra"] - r["qtd_venda"]
        r["lucro_bruto"] = r["valor_venda"] - r["valor_compra"]
    return rows


def adicionar_transacao(
    produto_id: int, tipo: str, quantidade: float, unidade: str,
    preco_unitario: float, valor_total: float, data_str: str,
) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                f"""INSERT INTO transacoes
                    (produtoId, tipo, quantidade, unidade, precoUnitario, valorTotal, data)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})""",
                (produto_id, tipo, quantidade, unidade, preco_unitario, valor_total, data_str),
            )
        except Exception:
            # Fallback for old SQLite schema where pesoKg/precoKg are NOT NULL
            if cfg.backend != "postgres":
                conn.rollback() if hasattr(conn, "rollback") else None
            cur.execute(
                f"""INSERT INTO transacoes
                    (produtoId, tipo, pesoKg, precoKg, valorTotal, data)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph})""",
                (produto_id, tipo, quantidade, preco_unitario, valor_total, data_str),
            )
        conn.commit()


def excluir_transacao(tid: int) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM transacoes WHERE id={ph}", (tid,))
        conn.commit()


# ── DESPESAS ──────────────────────────────────────────────────────────────────

def get_despesas() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, descricao, categoria, valor, data FROM despesas ORDER BY data DESC, id DESC")
        return rows_to_dicts(cur, cur.fetchall())


def adicionar_despesa(descricao: str, categoria: str, valor: float, data_str: str) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO despesas (descricao, categoria, valor, data) VALUES ({ph},{ph},{ph},{ph})",
            (descricao, categoria, valor, data_str),
        )
        conn.commit()


def excluir_despesa(did: int) -> None:
    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM despesas WHERE id={ph}", (did,))
        conn.commit()


# ── UTILITÁRIOS ───────────────────────────────────────────────────────────────

def moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


UNIDADES_COMUNS = ["kg", "g", "un", "L", "mL", "caixa", "saco", "par", "dúzia", "m", "m²", "hora", "Outro..."]


def popular_dados_mock() -> int:
    """Insere transações e despesas de demonstração. Retorna o número de registros inseridos."""
    import random
    from datetime import timedelta

    random.seed(42)
    produtos = get_produtos()
    if not produtos:
        return 0

    cfg = get_db_config()
    ph = "%s" if cfg.backend == "postgres" else "?"
    hoje = date.today()
    inseridos = 0

    with get_connection() as conn:
        cur = conn.cursor()

        # Transações: 90 dias de histórico
        for dias_atras in range(90, 0, -1):
            dia = hoje - timedelta(days=dias_atras)
            # Compras: 3x por semana (seg, qua, sex)
            if dia.weekday() in (0, 2, 4):
                for prod in random.sample(produtos, k=min(3, len(produtos))):
                    unid = prod.get("unidade", "kg")
                    qtd  = round(random.uniform(5, 30), 1)
                    preco_c = float(prod["precoCompraPadrao"]) or random.uniform(10, 40)
                    total = round(qtd * preco_c, 2)
                    try:
                        cur.execute(
                            f"INSERT INTO transacoes (produtoId,tipo,quantidade,unidade,precoUnitario,valorTotal,data) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                            (prod["id"], "compra", qtd, unid, preco_c, total, dia.isoformat()),
                        )
                        inseridos += 1
                    except Exception:
                        pass
            # Vendas: 5x por semana (seg a sex)
            if dia.weekday() < 5:
                for prod in random.sample(produtos, k=min(4, len(produtos))):
                    unid = prod.get("unidade", "kg")
                    qtd  = round(random.uniform(2, 15), 1)
                    preco_v = float(prod["precoVendaPadrao"]) or random.uniform(20, 60)
                    total = round(qtd * preco_v, 2)
                    try:
                        cur.execute(
                            f"INSERT INTO transacoes (produtoId,tipo,quantidade,unidade,precoUnitario,valorTotal,data) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                            (prod["id"], "venda", qtd, unid, preco_v, total, dia.isoformat()),
                        )
                        inseridos += 1
                    except Exception:
                        pass

        # Despesas: 1-2 por semana
        despesas_mock = [
            ("Combustível semana",          "Combustível",           random.uniform(180, 280)),
            ("Frete fornecedor",            "Frete / Transporte",    random.uniform(150, 350)),
            ("Gelo e embalagens",           "Embalagem",             random.uniform(80, 160)),
            ("Ajudante de carga",           "Funcionário / Mão de obra", random.uniform(100, 200)),
            ("Manutenção câmara fria",      "Manutenção",            random.uniform(200, 500)),
            ("Taxa de barraca / mercado",   "Impostos / Taxas",      random.uniform(120, 250)),
        ]
        for dias_atras in range(90, 0, -7):
            dia = hoje - timedelta(days=dias_atras)
            desc, cat, val_base = random.choice(despesas_mock)
            val = round(val_base + random.uniform(-20, 20), 2)
            try:
                cur.execute(
                    f"INSERT INTO despesas (descricao,categoria,valor,data) VALUES ({ph},{ph},{ph},{ph})",
                    (desc, cat, val, dia.isoformat()),
                )
                inseridos += 1
            except Exception:
                pass

        conn.commit()

    return inseridos


CSS = """
<style>
body, .stApp { background-color: #f6f8fb; }
.main .block-container {
    background: #ffffff;
    border-radius: 16px;
    padding: 2rem 2.5rem 3rem;
    box-shadow: 0 10px 30px rgba(20,60,120,0.08);
}
h1,h2,h3,h4,h5,h6,p,span,label { color: #1f2a44; }
.stTabs [data-baseweb="tab"] { color: #1f2a44; }
.stTabs [aria-selected="true"] { color: #1f2a44; border-bottom: 2px solid #2a5bd7; }
.stMultiSelect [data-baseweb="tag"] {
    background-color: #e8f1ff !important;
    color: #1f2a44 !important;
    border: 1px solid #cfe0ff !important;
}
.stMultiSelect [data-baseweb="tag"] svg { color: #2a5bd7 !important; }
.kpi-card {
    background: white;
    border: 1px solid #e6eef7;
    border-radius: 14px;
    padding: 12px 14px;
    box-shadow: 0 6px 18px rgba(20,60,120,0.06);
}
.hero-card {
    background: linear-gradient(135deg, #1a3a6e 0%, #2a5bd7 100%);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(42,91,215,0.25);
}
[data-testid="stSidebar"] { display: none; }
</style>
"""


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="Meu Comércio", layout="wide", page_icon="🛒")
    init_db()
    st.markdown(CSS, unsafe_allow_html=True)

    # Header
    hcols = st.columns([1, 8])
    with hcols[0]:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=72)
        else:
            st.markdown("## 🛒")
    with hcols[1]:
        st.title("Meu Comércio")
        st.caption("Gerencie itens, movimentações e despesas do seu negócio.")

    # Load data
    produtos = get_produtos()
    transacoes = get_transacoes()
    despesas = get_despesas()
    resumo = get_resumo_itens()

    df_trans_all = pd.DataFrame(transacoes) if transacoes else pd.DataFrame()
    df_desp_all = pd.DataFrame(despesas) if despesas else pd.DataFrame()

    if not df_trans_all.empty:
        df_trans_all["data"] = pd.to_datetime(df_trans_all["data"], errors="coerce")
    if not df_desp_all.empty:
        df_desp_all["data"] = pd.to_datetime(df_desp_all["data"], errors="coerce")

    tab_dash, tab_itens, tab_mov, tab_desp = st.tabs(
        ["📊 Dashboard", "📦 Itens", "↕️ Movimentações", "💸 Despesas"]
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_dash:
        df_trans = df_trans_all.copy()
        df_desp = df_desp_all.copy()

        with st.expander("🔍 Filtros", expanded=False):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                all_dates = []
                if not df_trans.empty:
                    all_dates += df_trans["data"].dropna().tolist()
                if not df_desp.empty:
                    all_dates += df_desp["data"].dropna().tolist()
                if all_dates:
                    min_d = min(d.date() if hasattr(d, "date") else d for d in all_dates)
                    max_d = max(d.date() if hasattr(d, "date") else d for d in all_dates)
                else:
                    min_d = max_d = date.today()
                date_range = st.date_input("Período", (min_d, max_d))
            with fc2:
                if not df_trans.empty:
                    itens_opts = sorted(df_trans["produtoNome"].dropna().unique().tolist())
                    sel_itens = st.multiselect("Itens", itens_opts, default=itens_opts)
                else:
                    sel_itens = []
            with fc3:
                if not df_desp.empty:
                    cat_opts = sorted(df_desp["categoria"].dropna().unique().tolist())
                    sel_cats = st.multiselect("Categoria de despesa", cat_opts, default=cat_opts)
                else:
                    sel_cats = []

            if isinstance(date_range, tuple) and len(date_range) == 2:
                s, e = date_range
                if not df_trans.empty:
                    df_trans = df_trans[(df_trans["data"].dt.date >= s) & (df_trans["data"].dt.date <= e)]
                if not df_desp.empty:
                    df_desp = df_desp[(df_desp["data"].dt.date >= s) & (df_desp["data"].dt.date <= e)]
            if sel_itens and not df_trans.empty:
                df_trans = df_trans[df_trans["produtoNome"].isin(sel_itens)]
            if sel_cats and not df_desp.empty:
                df_desp = df_desp[df_desp["categoria"].isin(sel_cats)]

        # KPIs
        total_venda   = df_trans.loc[df_trans["tipo"] == "venda",  "valorTotal"].sum() if not df_trans.empty else 0.0
        total_compra  = df_trans.loc[df_trans["tipo"] == "compra", "valorTotal"].sum() if not df_trans.empty else 0.0
        total_despesas = df_desp["valor"].sum() if not df_desp.empty else 0.0
        lucro_real = total_venda - total_compra - total_despesas

        cor_lucro  = "#4ade80" if lucro_real >= 0 else "#f87171"
        icon_lucro = "📈" if lucro_real >= 0 else "📉"

        st.markdown(
            f"""<div class="hero-card">
                <div style="color:#cbd5e1;font-size:0.85rem;margin-bottom:4px;">
                    Lucro Real &nbsp;=&nbsp; Vendas &minus; Compras &minus; Despesas
                </div>
                <div style="color:{cor_lucro};font-size:2.4rem;font-weight:800;line-height:1.1;">
                    {icon_lucro} {moeda(lucro_real)}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        for col, label, val in [
            (c1, "💰 Receita de Vendas",   moeda(total_venda)),
            (c2, "🛒 Custo de Compras",    moeda(total_compra)),
            (c3, "💸 Despesas Operac.",    moeda(total_despesas)),
            (c4, "📦 Itens em Estoque",    str(sum(1 for r in resumo if r["estoque"] > 0))),
        ]:
            with col:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric(label, val)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        ch1, ch2 = st.columns(2)

        with ch1:
            if not df_trans.empty:
                df_time = df_trans.copy()
                df_time["dia"] = df_time["data"].dt.date
                df_time = df_time.groupby(["dia", "tipo"])["valorTotal"].sum().reset_index()
                chart = (
                    alt.Chart(df_time).mark_area(opacity=0.4)
                    .encode(
                        x=alt.X("dia:T", title="Data"),
                        y=alt.Y("valorTotal:Q", title="Valor (R$)"),
                        color=alt.Color("tipo:N", title="Tipo",
                            scale=alt.Scale(domain=["compra", "venda"], range=["#f97316", "#3b82f6"])),
                        tooltip=["dia:T", "tipo:N", "valorTotal:Q"],
                    )
                    .properties(height=280, title="Compras × Vendas no Tempo")
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Sem movimentações no período.")

        with ch2:
            if not df_desp.empty and df_desp["valor"].sum() > 0:
                df_cat = df_desp.groupby("categoria")["valor"].sum().reset_index()
                chart = (
                    alt.Chart(df_cat).mark_arc(innerRadius=50)
                    .encode(
                        theta=alt.Theta("valor:Q"),
                        color=alt.Color("categoria:N", title="Categoria"),
                        tooltip=["categoria:N", alt.Tooltip("valor:Q", format=",.2f")],
                    )
                    .properties(height=280, title="Despesas por Categoria")
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Sem despesas no período.")

        # Demonstração
        with st.expander("🎭 Dados de Demonstração", expanded=False):
            st.caption("Popula o app com transações e despesas fictícias dos últimos 90 dias para apresentações.")
            if st.button("Carregar dados de demonstração", type="secondary"):
                n = popular_dados_mock()
                st.success(f"{n} registros de demonstração inseridos. Recarregue a página para ver.")
                st.rerun()

        st.subheader("Resumo por Item")
        df_res = pd.DataFrame(resumo)
        if not df_res.empty:
            df_show = df_res[["nome", "unidade", "qtd_compra", "qtd_venda", "estoque", "valor_compra", "valor_venda", "lucro_bruto"]].copy()
            df_show.columns = ["Item", "Unidade", "Qtd Comprada", "Qtd Vendida", "Estoque", "Custo Total", "Receita Total", "Lucro Bruto"]
            for col in ["Custo Total", "Receita Total", "Lucro Bruto"]:
                df_show[col] = df_show[col].apply(moeda)
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado para exibir ainda.")

    # ═══════════════════════════════════════════════════════════════════════════
    # ITENS
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_itens:
        st.subheader("Cadastrar Novo Item")
        with st.form("form_add_item", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome do item", placeholder="ex: Arroz, Camiseta P, Gasolina...")
                unidade_sel = st.selectbox("Unidade de medida", UNIDADES_COMUNS)
                unidade = st.text_input("Qual unidade?", placeholder="ex: fardo, resma...") if unidade_sel == "Outro..." else unidade_sel
            with c2:
                preco_compra = st.number_input("Preço de compra padrão (R$)", min_value=0.0, step=0.5, value=0.0, format="%.2f")
                preco_venda  = st.number_input("Preço de venda padrão (R$)",  min_value=0.0, step=0.5, value=0.0, format="%.2f")
            if st.form_submit_button("➕ Adicionar item", use_container_width=True):
                if not nome.strip():
                    st.error("Informe o nome do item.")
                elif not unidade.strip():
                    st.error("Informe a unidade de medida.")
                else:
                    adicionar_produto(nome.strip(), unidade.strip(), preco_compra, preco_venda)
                    st.success(f"Item '{nome.strip()}' cadastrado com sucesso.")
                    st.rerun()

        if produtos:
            st.divider()
            st.subheader("Editar / Excluir Item")
            prod_map = {p["nome"]: p for p in produtos}
            sel = st.selectbox("Selecione um item", list(prod_map.keys()))
            prod = prod_map[sel]

            col_edit, col_del = st.columns([3, 1])
            with col_edit:
                with st.form("form_edit_item"):
                    c1, c2 = st.columns(2)
                    with c1:
                        nome_e = st.text_input("Nome", value=prod["nome"])
                        unid_atual = prod.get("unidade", "un")
                        idx_unid = UNIDADES_COMUNS.index(unid_atual) if unid_atual in UNIDADES_COMUNS else UNIDADES_COMUNS.index("Outro...")
                        unid_sel_e = st.selectbox("Unidade", UNIDADES_COMUNS, index=idx_unid)
                        unid_e = st.text_input("Qual unidade?", value=unid_atual, key="unid_outro_edit") if unid_sel_e == "Outro..." else unid_sel_e
                    with c2:
                        compra_e = st.number_input("Preço de compra (R$)", min_value=0.0, step=0.5, value=float(prod["precoCompraPadrao"]), format="%.2f")
                        venda_e  = st.number_input("Preço de venda (R$)",  min_value=0.0, step=0.5, value=float(prod["precoVendaPadrao"]),  format="%.2f")
                    if st.form_submit_button("💾 Salvar alterações", use_container_width=True):
                        atualizar_produto(prod["id"], nome_e.strip(), unid_e.strip(), compra_e, venda_e)
                        st.success("Item atualizado.")
                        st.rerun()
            with col_del:
                st.write("")
                st.write("")
                st.caption("Excluir remove o cadastro. Movimentações anteriores são mantidas.")
                if st.button("🗑️ Excluir item", type="secondary", use_container_width=True):
                    try:
                        excluir_produto(prod["id"])
                        st.success("Item excluído.")
                        st.rerun()
                    except Exception:
                        st.error("Não é possível excluir: existem movimentações vinculadas a este item.")

            st.divider()
            st.subheader("Todos os Itens")
            df_p = pd.DataFrame(produtos)[["nome", "unidade", "precoCompraPadrao", "precoVendaPadrao"]]
            df_p.columns = ["Item", "Unidade", "Preço Compra (R$)", "Preço Venda (R$)"]
            st.dataframe(df_p, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # MOVIMENTAÇÕES
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_mov:
        st.subheader("Registrar Movimentação")
        if not produtos:
            st.info("Cadastre itens na aba **Itens** antes de registrar movimentações.")
        else:
            prod_map = {p["nome"]: p for p in produtos}
            with st.form("form_add_mov", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    item_key = st.selectbox("Item", list(prod_map.keys()))
                    tipo = st.radio("Tipo", ["compra", "venda"], horizontal=True,
                                    format_func=lambda x: "🛒 Compra" if x == "compra" else "💰 Venda")
                    data_ref = st.date_input("Data", value=date.today())
                with c2:
                    prod_sel  = prod_map[item_key]
                    unid_item = prod_sel.get("unidade", "un")
                    qtd = st.number_input(f"Quantidade ({unid_item})", min_value=0.0, step=0.1, value=0.0, format="%.3f")
                    preco_pad = prod_sel["precoCompraPadrao"] if tipo == "compra" else prod_sel["precoVendaPadrao"]
                    preco = st.number_input(f"Preço por {unid_item} (R$)", min_value=0.0, step=0.5, value=float(preco_pad), format="%.2f")
                    total = round(qtd * preco, 2)
                    st.metric("Valor Total", moeda(total))

                if st.form_submit_button("➕ Registrar movimentação", use_container_width=True):
                    if qtd <= 0:
                        st.error("Quantidade deve ser maior que zero.")
                    else:
                        adicionar_transacao(prod_sel["id"], tipo, qtd, unid_item, preco, total, data_ref.isoformat())
                        st.success("Movimentação registrada.")
                        st.rerun()

        if not df_trans_all.empty:
            st.divider()
            st.subheader("Movimentações Cadastradas")
            df_show = df_trans_all[["id", "data", "produtoNome", "tipo", "quantidade", "unidade", "precoUnitario", "valorTotal"]].copy()
            df_show.columns = ["ID", "Data", "Item", "Tipo", "Quantidade", "Unidade", "Preço Unit.", "Valor Total"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            trans_map = {f"ID {t['id']} – {t['produtoNome']} ({t['tipo']})": t for t in transacoes}
            cs, cb = st.columns([5, 1])
            with cs:
                sel_t = st.selectbox("Selecione para excluir", list(trans_map.keys()), key="sel_del_mov")
            with cb:
                st.write("")
                if st.button("🗑️ Excluir", type="secondary", use_container_width=True, key="btn_del_mov"):
                    excluir_transacao(trans_map[sel_t]["id"])
                    st.success("Movimentação excluída.")
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════════
    # DESPESAS
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_desp:
        st.subheader("Registrar Despesa")
        with st.form("form_add_desp", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                desc  = st.text_input("Descrição", placeholder="ex: Gasolina da semana, Frete da carga...")
                cat   = st.selectbox("Categoria", CATEGORIAS_DESPESA)
            with c2:
                val_d  = st.number_input("Valor (R$)", min_value=0.0, step=1.0, value=0.0, format="%.2f")
                data_d = st.date_input("Data", value=date.today())
            if st.form_submit_button("➕ Registrar despesa", use_container_width=True):
                if not desc.strip():
                    st.error("Informe a descrição da despesa.")
                elif val_d <= 0:
                    st.error("Valor deve ser maior que zero.")
                else:
                    adicionar_despesa(desc.strip(), cat, val_d, data_d.isoformat())
                    st.success("Despesa registrada.")
                    st.rerun()

        if not df_desp_all.empty:
            st.divider()
            st.subheader("Resumo por Categoria")
            df_cat_sum = (
                df_desp_all.groupby("categoria")["valor"].sum()
                .reset_index().sort_values("valor", ascending=False)
            )
            df_cat_sum.columns = ["Categoria", "Total (R$)"]
            df_cat_sum["Total (R$)"] = df_cat_sum["Total (R$)"].apply(moeda)
            st.dataframe(df_cat_sum, use_container_width=True, hide_index=True)

            st.subheader("Todas as Despesas")
            df_show = df_desp_all[["id", "data", "descricao", "categoria", "valor"]].copy()
            df_show.columns = ["ID", "Data", "Descrição", "Categoria", "Valor (R$)"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            desp_map = {f"ID {d['id']} – {d['descricao']} ({d['categoria']})": d for d in despesas}
            cs, cb = st.columns([5, 1])
            with cs:
                sel_d = st.selectbox("Selecione para excluir", list(desp_map.keys()), key="sel_del_desp")
            with cb:
                st.write("")
                if st.button("🗑️ Excluir", type="secondary", use_container_width=True, key="btn_del_desp"):
                    excluir_despesa(desp_map[sel_d]["id"])
                    st.success("Despesa excluída.")
                    st.rerun()


if __name__ == "__main__":
    main()
