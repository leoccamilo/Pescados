"""
Pescados do Alexandre - Streamlit App
UI e lógica de negócio para controle de estoque e lucratividade.
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


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "pescados.db")


@dataclass(frozen=True)
class DbConfig:
    backend: str  # "postgres" or "sqlite"
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
    mapped = []
    key_map = {
        "precocomprapadrao": "precoCompraPadrao",
        "precovendapadrao": "precoVendaPadrao",
        "produtoid": "produtoId",
        "pesokg": "pesoKg",
        "precokg": "precoKg",
        "valortotal": "valorTotal",
        "produtonome": "produtoNome",
    }
    for row in rows:
        d = dict(zip(cols, row))
        fixed = {}
        for k, v in d.items():
            nk = key_map.get(k, k)
            fixed[nk] = v
        mapped.append(fixed)
    return mapped


def init_db() -> None:
    cfg = get_db_config()
    with get_connection() as conn:
        cursor = conn.cursor()

        if cfg.backend == "postgres":
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    precoCompraPadrao DOUBLE PRECISION NOT NULL,
                    precoVendaPadrao DOUBLE PRECISION NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transacoes (
                    id SERIAL PRIMARY KEY,
                    produtoId INTEGER NOT NULL REFERENCES produtos(id),
                    tipo TEXT NOT NULL CHECK(tipo IN ('compra', 'venda')),
                    pesoKg DOUBLE PRECISION NOT NULL,
                    precoKg DOUBLE PRECISION NOT NULL,
                    valorTotal DOUBLE PRECISION NOT NULL,
                    data DATE NOT NULL
                )
                """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    precoCompraPadrao REAL NOT NULL,
                    precoVendaPadrao REAL NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produtoId INTEGER NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('compra', 'venda')),
                    pesoKg REAL NOT NULL,
                    precoKg REAL NOT NULL,
                    valorTotal REAL NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (produtoId) REFERENCES produtos(id)
                )
                """
            )

        conn.commit()


def popular_produtos_iniciais() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        if cursor.fetchone()[0] > 0:
            return

        produtos = [
            ("Camarao Regional", 25.00, 40.00),
            ("Camarao Rosa", 35.00, 55.00),
            ("Pescada Amarela", 18.00, 30.00),
            ("Dourada", 20.00, 35.00),
            ("Filhote", 28.00, 45.00),
            ("Pescada Go", 15.00, 28.00),
            ("Pata de Caranguejo", 30.00, 50.00),
            ("Massa de Caranguejo", 40.00, 65.00),
        ]

        cfg = get_db_config()
        placeholder = "%s" if cfg.backend == "postgres" else "?"
        cursor.executemany(
            f"""
            INSERT INTO produtos (nome, precoCompraPadrao, precoVendaPadrao)
            VALUES ({placeholder}, {placeholder}, {placeholder})
            """,
            produtos,
        )
        conn.commit()


def get_produtos() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos ORDER BY nome")
        return rows_to_dicts(cursor, cursor.fetchall())


def get_transacoes() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.*, p.nome AS "produtoNome"
            FROM transacoes t
            JOIN produtos p ON p.id = t.produtoId
            ORDER BY t.data DESC, t.id DESC
            """
        )
        return rows_to_dicts(cursor, cursor.fetchall())


def get_resumo_produtos() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.id,
                p.nome,
                COALESCE(SUM(CASE WHEN t.tipo='compra' THEN t.pesoKg END), 0) AS peso_compra,
                COALESCE(SUM(CASE WHEN t.tipo='venda' THEN t.pesoKg END), 0) AS peso_venda,
                COALESCE(SUM(CASE WHEN t.tipo='compra' THEN t.valorTotal END), 0) AS valor_compra,
                COALESCE(SUM(CASE WHEN t.tipo='venda' THEN t.valorTotal END), 0) AS valor_venda
            FROM produtos p
            LEFT JOIN transacoes t ON t.produtoId = p.id
            GROUP BY p.id, p.nome
            ORDER BY p.nome
            """
        )
        rows = rows_to_dicts(cursor, cursor.fetchall())

    for r in rows:
        r["estoque_kg"] = r["peso_compra"] - r["peso_venda"]
        r["lucro"] = r["valor_venda"] - r["valor_compra"]
    return rows


def adicionar_produto(nome: str, preco_compra: float, preco_venda: float) -> None:
    cfg = get_db_config()
    placeholder = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO produtos (nome, precoCompraPadrao, precoVendaPadrao)
            VALUES ({placeholder}, {placeholder}, {placeholder})
            """,
            (nome, preco_compra, preco_venda),
        )
        conn.commit()


def atualizar_produto(produto_id: int, nome: str, preco_compra: float, preco_venda: float) -> None:
    cfg = get_db_config()
    placeholder = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE produtos
            SET nome = {placeholder}, precoCompraPadrao = {placeholder}, precoVendaPadrao = {placeholder}
            WHERE id = {placeholder}
            """,
            (nome, preco_compra, preco_venda, produto_id),
        )
        conn.commit()


def excluir_produto(produto_id: int) -> None:
    cfg = get_db_config()
    placeholder = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM produtos WHERE id = {placeholder}", (produto_id,))
        conn.commit()


def adicionar_transacao(
    produto_id: int,
    tipo: str,
    peso_kg: float,
    preco_kg: float,
    valor_total: float,
    data_str: str,
) -> None:
    cfg = get_db_config()
    placeholder = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO transacoes (produtoId, tipo, pesoKg, precoKg, valorTotal, data)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """,
            (produto_id, tipo, peso_kg, preco_kg, valor_total, data_str),
        )
        conn.commit()


def excluir_transacao(transacao_id: int) -> None:
    cfg = get_db_config()
    placeholder = "%s" if cfg.backend == "postgres" else "?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM transacoes WHERE id = {placeholder}", (transacao_id,))
        conn.commit()


def moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    st.set_page_config(page_title="Pescados do Alexandre", layout="wide")
    init_db()
    popular_produtos_iniciais()

    st.title("Pescados do Alexandre")
    st.caption("Controle de estoque e lucratividade de pescados.")

    produtos = get_produtos()
    transacoes = get_transacoes()
    resumo = get_resumo_produtos()

    tab_dashboard, tab_produtos, tab_transacoes = st.tabs(
        ["Dashboard", "Produtos", "Transações"]
    )

    with tab_dashboard:
        total_compra = sum(r["valor_compra"] for r in resumo)
        total_venda = sum(r["valor_venda"] for r in resumo)
        total_lucro = total_venda - total_compra
        total_estoque = sum(r["estoque_kg"] for r in resumo)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Compras", moeda(total_compra))
        c2.metric("Total de Vendas", moeda(total_venda))
        c3.metric("Lucro", moeda(total_lucro))
        c4.metric("Estoque (kg)", f"{total_estoque:.2f}")

        st.subheader("Resumo por Produto")
        df_resumo = pd.DataFrame(resumo)
        if not df_resumo.empty:
            df_resumo = df_resumo[
                [
                    "nome",
                    "peso_compra",
                    "peso_venda",
                    "estoque_kg",
                    "valor_compra",
                    "valor_venda",
                    "lucro",
                ]
            ]
            df_resumo.columns = [
                "Produto",
                "Compra (kg)",
                "Venda (kg)",
                "Estoque (kg)",
                "Valor Compra",
                "Valor Venda",
                "Lucro",
            ]
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado para exibir ainda.")

        st.subheader("Transações Recentes")
        df_trans = pd.DataFrame(transacoes)
        if not df_trans.empty:
            df_trans = df_trans[
                ["data", "produtoNome", "tipo", "pesoKg", "precoKg", "valorTotal"]
            ]
            df_trans.columns = [
                "Data",
                "Produto",
                "Tipo",
                "Peso (kg)",
                "Preço (R$/kg)",
                "Valor Total",
            ]
            st.dataframe(df_trans, use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não há transações registradas.")

    with tab_produtos:
        st.subheader("Cadastro de Produtos")

        with st.form("form_add_produto", clear_on_submit=True):
            nome = st.text_input("Nome do produto")
            preco_compra = st.number_input(
                "Preço de compra padrão (R$/kg)", min_value=0.0, step=0.5, value=0.0
            )
            preco_venda = st.number_input(
                "Preço de venda padrão (R$/kg)", min_value=0.0, step=0.5, value=0.0
            )
            submitted = st.form_submit_button("Adicionar produto")
            if submitted:
                if not nome.strip():
                    st.error("Informe o nome do produto.")
                else:
                    adicionar_produto(nome.strip(), preco_compra, preco_venda)
                    st.success("Produto adicionado.")
                    st.rerun()

        st.divider()
        st.subheader("Editar / Excluir Produto")
        if produtos:
            prod_map = {f"{p['nome']} (ID {p['id']})": p for p in produtos}
            selecionado = st.selectbox("Selecione um produto", list(prod_map.keys()))
            prod = prod_map[selecionado]

            col_a, col_b = st.columns(2)
            with col_a:
                nome_edit = st.text_input("Nome", value=prod["nome"])
                compra_edit = st.number_input(
                    "Preço de compra (R$/kg)",
                    min_value=0.0,
                    step=0.5,
                    value=float(prod["precoCompraPadrao"]),
                )
                venda_edit = st.number_input(
                    "Preço de venda (R$/kg)",
                    min_value=0.0,
                    step=0.5,
                    value=float(prod["precoVendaPadrao"]),
                )
                if st.button("Salvar alterações"):
                    atualizar_produto(prod["id"], nome_edit.strip(), compra_edit, venda_edit)
                    st.success("Produto atualizado.")
                    st.rerun()

            with col_b:
                st.warning("Excluir produto remove apenas o cadastro. Transações antigas permanecem.")
                if st.button("Excluir produto", type="secondary"):
                    excluir_produto(prod["id"])
                    st.success("Produto excluído.")
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado.")

    with tab_transacoes:
        st.subheader("Registrar Transação")
        if not produtos:
            st.info("Cadastre produtos antes de registrar transações.")
        else:
            prod_map = {f"{p['nome']} (ID {p['id']})": p for p in produtos}
            with st.form("form_add_transacao", clear_on_submit=True):
                prod_key = st.selectbox("Produto", list(prod_map.keys()))
                tipo = st.radio("Tipo", ["compra", "venda"], horizontal=True)
                peso_kg = st.number_input("Peso (kg)", min_value=0.0, step=0.1, value=0.0)
                preco_padrao = (
                    prod_map[prod_key]["precoCompraPadrao"]
                    if tipo == "compra"
                    else prod_map[prod_key]["precoVendaPadrao"]
                )
                preco_kg = st.number_input(
                    "Preço (R$/kg)", min_value=0.0, step=0.5, value=float(preco_padrao)
                )
                data_ref = st.date_input("Data", value=date.today())
                valor_total = round(peso_kg * preco_kg, 2)
                st.caption(f"Valor total: {moeda(valor_total)}")
                submitted = st.form_submit_button("Adicionar transação")
                if submitted:
                    adicionar_transacao(
                        prod_map[prod_key]["id"],
                        tipo,
                        peso_kg,
                        preco_kg,
                        valor_total,
                        data_ref.isoformat(),
                    )
                    st.success("Transação registrada.")
                    st.rerun()

        st.divider()
        st.subheader("Transações Cadastradas")
        df_trans = pd.DataFrame(transacoes)
        if not df_trans.empty:
            df_trans = df_trans[
                ["id", "data", "produtoNome", "tipo", "pesoKg", "precoKg", "valorTotal"]
            ]
            df_trans.columns = [
                "ID",
                "Data",
                "Produto",
                "Tipo",
                "Peso (kg)",
                "Preço (R$/kg)",
                "Valor Total",
            ]
            st.dataframe(df_trans, use_container_width=True, hide_index=True)

            trans_map = {
                f"ID {t['id']} - {t['produtoNome']} - {t['tipo']}": t for t in transacoes
            }
            selecionada = st.selectbox("Selecione uma transação para excluir", list(trans_map.keys()))
            if st.button("Excluir transação", type="secondary"):
                excluir_transacao(trans_map[selecionada]["id"])
                st.success("Transação excluída.")
                st.rerun()
        else:
            st.info("Nenhuma transação encontrada.")


if __name__ == "__main__":
    main()
