"""
Pescados do Alexandre - Aplicativo Principal
Este script inicia o servidor e abre o navegador automaticamente.
"""

import os
import sys
import socket
import webbrowser
import threading
import time

# Definir diretorio base (funciona tanto em dev quanto no executavel)
if getattr(sys, 'frozen', False):
    # Executando como executavel PyInstaller
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Executando como script Python
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mudar para o diretorio base
os.chdir(BASE_DIR)

# Configurar caminho do banco de dados
DB_PATH = os.path.join(BASE_DIR, 'pescados.db')

# Importar Flask e configurar app
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

# ==================== DATABASE ====================

def get_connection():
    """Retorna uma conexao com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessarias"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            precoCompraPadrao REAL NOT NULL,
            precoVendaPadrao REAL NOT NULL
        )
    ''')

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

def popular_produtos_iniciais():
    """Popula o banco com os produtos iniciais (sem transacoes)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM produtos')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

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

    conn.commit()
    conn.close()
    print(f"Banco inicializado com {len(produtos)} produtos.")

def get_produtos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM produtos ORDER BY nome')
    produtos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return produtos

def get_transacoes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transacoes ORDER BY data DESC, id DESC')
    transacoes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transacoes

def adicionar_produto(nome, preco_compra, preco_venda):
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM produtos WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def adicionar_transacao(produto_id, tipo, peso_kg, preco_kg, valor_total, data):
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()

# ==================== ROTAS ====================

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory(BASE_DIR, 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory(BASE_DIR, 'sw.js', mimetype='application/javascript')

@app.route('/icon-192.png')
def icon_192():
    return send_from_directory(BASE_DIR, 'icon-192.png', mimetype='image/png')

@app.route('/icon-512.png')
def icon_512():
    return send_from_directory(BASE_DIR, 'icon-512.png', mimetype='image/png')

@app.route('/api/produtos', methods=['GET'])
def api_get_produtos():
    return jsonify(get_produtos())

@app.route('/api/produtos', methods=['POST'])
def api_criar_produto():
    data = request.json
    id = adicionar_produto(data['nome'], data['precoCompraPadrao'], data['precoVendaPadrao'])
    return jsonify({'id': id, **data}), 201

@app.route('/api/produtos/<int:id>', methods=['PUT'])
def api_atualizar_produto(id):
    data = request.json
    atualizar_produto(id, data['nome'], data['precoCompraPadrao'], data['precoVendaPadrao'])
    return jsonify({'id': id, **data})

@app.route('/api/produtos/<int:id>', methods=['DELETE'])
def api_excluir_produto(id):
    excluir_produto(id)
    return '', 204

@app.route('/api/transacoes', methods=['GET'])
def api_get_transacoes():
    return jsonify(get_transacoes())

@app.route('/api/transacoes', methods=['POST'])
def api_criar_transacao():
    data = request.json
    id = adicionar_transacao(
        data['produtoId'], data['tipo'], data['pesoKg'],
        data['precoKg'], data['valorTotal'], data['data']
    )
    return jsonify({'id': id, **data}), 201

@app.route('/api/transacoes/<int:id>', methods=['DELETE'])
def api_excluir_transacao(id):
    excluir_transacao(id)
    return '', 204

# ==================== MAIN ====================

def get_local_ip():
    """Descobre o IP local da maquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def open_browser(port):
    """Abre o navegador apos um pequeno delay"""
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{port}')

def main():
    PORT = 5000
    local_ip = get_local_ip()

    # Inicializar banco de dados
    init_db()
    popular_produtos_iniciais()

    print("=" * 55)
    print("   PESCADOS DO ALEXANDRE - Controle de Estoque")
    print("=" * 55)
    print(f"   Acesso no computador: http://localhost:{PORT}")
    print(f"   Acesso pelo celular:  http://{local_ip}:{PORT}")
    print("=" * 55)
    print("   Mantenha esta janela aberta enquanto usa o app.")
    print("   Para fechar, pressione Ctrl+C ou feche a janela.")
    print("=" * 55)

    # Abrir navegador automaticamente
    threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()

    # Iniciar servidor (sem modo debug para producao)
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', PORT, app, threaded=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        server.shutdown()

if __name__ == '__main__':
    main()
