import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'pescados.db'

def get_connection():
    """Retorna uma conexao com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessarias"""
    conn = get_connection()
    cursor = conn.cursor()

    # Criar tabela de produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            precoCompraPadrao REAL NOT NULL,
            precoVendaPadrao REAL NOT NULL
        )
    ''')

    # Criar tabela de transacoes
    cursor.execute('''
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
    ''')

    conn.commit()
    conn.close()

def popular_dados_ficticios():
    """Popula o banco com dados ficticios para teste"""
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar se ja existem produtos
    cursor.execute('SELECT COUNT(*) FROM produtos')
    if cursor.fetchone()[0] > 0:
        print("Banco ja possui dados. Pulando populacao.")
        conn.close()
        return

    # Inserir produtos
    produtos = [
        ('Camarao Regional', 25.00, 40.00),
        ('Camarao Rosa', 35.00, 55.00),
        ('Pescada Amarela', 18.00, 30.00),
        ('Dourada', 20.00, 35.00),
        ('Filhote', 28.00, 45.00),
        ('Pescada Go', 15.00, 28.00),
        ('Pata de Caranguejo', 30.00, 50.00),
        ('Massa de Caranguejo', 40.00, 65.00),
    ]

    cursor.executemany('''
        INSERT INTO produtos (nome, precoCompraPadrao, precoVendaPadrao)
        VALUES (?, ?, ?)
    ''', produtos)

    # Gerar transacoes ficticias dos ultimos 60 dias
    hoje = datetime.now()
    transacoes = []

    for dias_atras in range(60, -1, -1):
        data = (hoje - timedelta(days=dias_atras)).strftime('%Y-%m-%d')

        # Gerar 1-4 transacoes por dia (aleatorio)
        num_transacoes = random.randint(1, 4)

        for _ in range(num_transacoes):
            produto_id = random.randint(1, 8)
            produto = produtos[produto_id - 1]

            # 60% compras, 40% vendas
            tipo = 'compra' if random.random() < 0.6 else 'venda'

            # Peso entre 2 e 25 kg
            peso = round(random.uniform(2, 25), 1)

            # Preco com variacao de +-10% do padrao
            preco_base = produto[1] if tipo == 'compra' else produto[2]
            variacao = random.uniform(0.9, 1.1)
            preco = round(preco_base * variacao, 2)

            valor_total = round(peso * preco, 2)

            transacoes.append((produto_id, tipo, peso, preco, valor_total, data))

    cursor.executemany('''
        INSERT INTO transacoes (produtoId, tipo, pesoKg, precoKg, valorTotal, data)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', transacoes)

    conn.commit()
    conn.close()
    print(f"Banco populado com {len(produtos)} produtos e {len(transacoes)} transacoes.")

def get_produtos():
    """Retorna todos os produtos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM produtos ORDER BY nome')
    produtos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return produtos

def get_transacoes():
    """Retorna todas as transacoes ordenadas por data (mais recente primeiro)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transacoes ORDER BY data DESC, id DESC')
    transacoes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transacoes

def adicionar_produto(nome, preco_compra, preco_venda):
    """Adiciona um novo produto"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produtos (nome, precoCompraPadrao, precoVendaPadrao)
        VALUES (?, ?, ?)
    ''', (nome, preco_compra, preco_venda))
    produto_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return produto_id

def atualizar_produto(id, nome, preco_compra, preco_venda):
    """Atualiza um produto existente"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE produtos
        SET nome = ?, precoCompraPadrao = ?, precoVendaPadrao = ?
        WHERE id = ?
    ''', (nome, preco_compra, preco_venda, id))
    conn.commit()
    conn.close()

def excluir_produto(id):
    """Exclui um produto"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM produtos WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def adicionar_transacao(produto_id, tipo, peso_kg, preco_kg, valor_total, data):
    """Adiciona uma nova transacao"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transacoes (produtoId, tipo, pesoKg, precoKg, valorTotal, data)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (produto_id, tipo, peso_kg, preco_kg, valor_total, data))
    transacao_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return transacao_id

def excluir_transacao(id):
    """Exclui uma transacao"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Inicializando banco de dados...")
    init_db()
    print("Populando com dados ficticios...")
    popular_dados_ficticios()
    print("Concluido!")
