"""
Migrate local SQLite data (pescados.db) to Supabase Postgres.
Usage (PowerShell):
  $env:DATABASE_URL="postgresql://..."; python migrate_sqlite_to_supabase.py
"""

from __future__ import annotations

import os
import sqlite3
import sys


APP_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(APP_DIR, "pescados.db")


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL não definido.")
        return 1

    if not os.path.exists(SQLITE_PATH):
        print(f"SQLite não encontrado em {SQLITE_PATH}")
        return 1

    import psycopg2

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(database_url)
    pg_cur = pg_conn.cursor()

    try:
        # Create tables if needed
        pg_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                precoCompraPadrao DOUBLE PRECISION NOT NULL,
                precoVendaPadrao DOUBLE PRECISION NOT NULL
            )
            """
        )
        pg_cur.execute(
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
        pg_conn.commit()

        # Safety: avoid duplicate imports
        pg_cur.execute("SELECT COUNT(*) FROM produtos")
        if pg_cur.fetchone()[0] > 0:
            print("Tabela produtos já possui dados. Abortando para evitar duplicidade.")
            return 1

        pg_cur.execute("SELECT COUNT(*) FROM transacoes")
        if pg_cur.fetchone()[0] > 0:
            print("Tabela transacoes já possui dados. Abortando para evitar duplicidade.")
            return 1

        # Read from SQLite
        sqlite_cur.execute(
            "SELECT id, nome, precoCompraPadrao, precoVendaPadrao FROM produtos ORDER BY id"
        )
        produtos = [tuple(row) for row in sqlite_cur.fetchall()]

        sqlite_cur.execute(
            "SELECT id, produtoId, tipo, pesoKg, precoKg, valorTotal, data FROM transacoes ORDER BY id"
        )
        transacoes = [tuple(row) for row in sqlite_cur.fetchall()]

        # Insert into Postgres
        if produtos:
            pg_cur.executemany(
                """
                INSERT INTO produtos (id, nome, precoCompraPadrao, precoVendaPadrao)
                VALUES (%s, %s, %s, %s)
                """,
                produtos,
            )

        if transacoes:
            pg_cur.executemany(
                """
                INSERT INTO transacoes (id, produtoId, tipo, pesoKg, precoKg, valorTotal, data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                transacoes,
            )

        # Sync sequences
        pg_cur.execute(
            "SELECT setval(pg_get_serial_sequence('produtos','id'), COALESCE(MAX(id),1), true) FROM produtos"
        )
        pg_cur.execute(
            "SELECT setval(pg_get_serial_sequence('transacoes','id'), COALESCE(MAX(id),1), true) FROM transacoes"
        )

        pg_conn.commit()
        print("Migração concluída com sucesso.")
        return 0
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
