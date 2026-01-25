from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import database

app = Flask(__name__, static_folder='.')
CORS(app)

# Inicializar banco de dados ao iniciar o servidor
database.init_db()
database.popular_dados_ficticios()

# Servir arquivos estaticos
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/icon-192.png')
def icon_192():
    return send_from_directory('.', 'icon-192.png', mimetype='image/png')

@app.route('/icon-512.png')
def icon_512():
    return send_from_directory('.', 'icon-512.png', mimetype='image/png')

# API de Produtos
@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    """Retorna todos os produtos"""
    produtos = database.get_produtos()
    return jsonify(produtos)

@app.route('/api/produtos', methods=['POST'])
def criar_produto():
    """Cria um novo produto"""
    data = request.json
    id = database.adicionar_produto(
        data['nome'],
        data['precoCompraPadrao'],
        data['precoVendaPadrao']
    )
    return jsonify({'id': id, **data}), 201

@app.route('/api/produtos/<int:id>', methods=['PUT'])
def atualizar_produto(id):
    """Atualiza um produto existente"""
    data = request.json
    database.atualizar_produto(
        id,
        data['nome'],
        data['precoCompraPadrao'],
        data['precoVendaPadrao']
    )
    return jsonify({'id': id, **data})

@app.route('/api/produtos/<int:id>', methods=['DELETE'])
def excluir_produto(id):
    """Exclui um produto"""
    database.excluir_produto(id)
    return '', 204

# API de Transacoes
@app.route('/api/transacoes', methods=['GET'])
def get_transacoes():
    """Retorna todas as transacoes"""
    transacoes = database.get_transacoes()
    return jsonify(transacoes)

@app.route('/api/transacoes', methods=['POST'])
def criar_transacao():
    """Cria uma nova transacao"""
    data = request.json
    id = database.adicionar_transacao(
        data['produtoId'],
        data['tipo'],
        data['pesoKg'],
        data['precoKg'],
        data['valorTotal'],
        data['data']
    )
    return jsonify({'id': id, **data}), 201

@app.route('/api/transacoes/<int:id>', methods=['DELETE'])
def excluir_transacao(id):
    """Exclui uma transacao"""
    database.excluir_transacao(id)
    return '', 204

if __name__ == '__main__':
    import socket

    # Descobrir IP local
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    local_ip = get_local_ip()

    print("=" * 50)
    print("Servidor iniciado!")
    print(f"Acesso local:    http://localhost:5000")
    print(f"Acesso na rede:  http://{local_ip}:5000")
    print("=" * 50)
    print("Use o endereco de rede no celular!")
    print("=" * 50)

    # host='0.0.0.0' permite conexoes de qualquer IP na rede
    app.run(debug=True, port=5000, host='0.0.0.0')
