# Pescados do Alexandre

Aplicativo completo para controle de estoque e análise de lucratividade de um negócio de pescados.

## 🎯 Funcionalidades

- **Cadastro de Produtos**: Gerenciamento de pescados com preços de compra e venda
- **Registro de Transações**: Compras e vendas com controle de peso e valores
- **Dashboard Analítico**: Gráficos de lucratividade, estoque e movimentação
- **PWA (Progressive Web App)**: Instale no celular como um app nativo
- **Modo Offline**: Funciona sem internet com sincronização automática
- **Acesso em Rede**: Use no celular acessando o computador pela rede local

## 📦 Distribuição

### Executável Windows (Recomendado)
- Baixe o instalador: `PescadosAlexandre.exe`
- Execute o instalador e siga as instruções
- O app abre automaticamente no navegador

### PWA no Celular
1. Inicie o servidor no computador
2. No celular, acesse `http://IP_DO_COMPUTADOR:5000`
3. Clique em "Instalar App" ou adicione à tela inicial
4. O app funciona offline após a primeira carga

## 🚀 Como Usar (Desenvolvimento)

### 1. Instalar dependências Python
```powershell
cd C:\Alexandre
pip install -r requirements.txt
```

### 2. Iniciar o servidor
```powershell
python app.py
```
Ou para servidor local simples:
```powershell
python server.py
```

### 3. Acessar o app
- **Local**: http://localhost:5000
- **Rede**: http://SEU_IP:5000 (mostrado no terminal ao iniciar)

## 📱 Acesso pelo Celular

1. Conecte o celular na mesma rede Wi-Fi do computador
2. Inicie o servidor no computador
3. No celular, acesse o IP mostrado no terminal (ex: `http://192.168.1.100:5000`)
4. Instale como PWA para usar offline

## 🔧 Build do Executável

Para gerar o instalador:
```powershell
build.bat
```

O instalador será criado em `PescadosAlexandre_Instalador/`.

## 📁 Estrutura de Arquivos

```
C:\Alexandre\
├── app.py                 # Servidor Flask principal (rede + abertura de navegador)
├── server.py              # Servidor Flask simplificado
├── database.py            # Módulo de acesso ao banco SQLite
├── index.html             # Frontend React + Tailwind + Recharts
├── sw.js                  # Service Worker para modo offline
├── manifest.json          # Manifesto PWA
├── icon-192.png           # Ícone PWA 192x192
├── icon-512.png           # Ícone PWA 512x512
├── Alexandre.ico          # Ícone do executável Windows
├── requirements.txt       # Dependências Python
├── build.bat              # Script de build do executável
├── generate_icons.py      # Gerador de ícones
├── PescadosApp.jsx        # Código fonte React (referência)
├── Instruções.txt         # Instruções originais
└── pescados.db            # Banco de dados SQLite (criado automaticamente)
```

## 🗄️ API REST

### Produtos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/produtos` | Lista todos os produtos |
| POST | `/api/produtos` | Cria um novo produto |
| PUT | `/api/produtos/:id` | Atualiza um produto |
| DELETE | `/api/produtos/:id` | Exclui um produto |

### Transações
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/transacoes` | Lista todas as transações |
| POST | `/api/transacoes` | Cria uma nova transação |
| DELETE | `/api/transacoes/:id` | Exclui uma transação |

### Sincronização
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/sync` | Sincroniza dados offline com o servidor |

## 📊 Estrutura de Dados

### Produto
- `id`: Identificador único
- `nome`: Nome do pescado
- `precoCompraPadrao`: Preço de compra padrão (R$/kg)
- `precoVendaPadrao`: Preço de venda padrão (R$/kg)

### Transação
- `id`: Identificador único
- `produtoId`: ID do produto relacionado
- `tipo`: "compra" ou "venda"
- `pesoKg`: Peso em quilogramas
- `precoKg`: Preço por quilo
- `valorTotal`: Valor total da transação
- `data`: Data da transação

## ⚙️ Requisitos

- Python 3.7+
- Flask e Flask-CORS
- Navegador moderno (Chrome, Edge, Firefox)
- Para PWA: navegador com suporte a Service Workers

## 📄 Licença

Projeto desenvolvido para uso pessoal - Pescados do Alexandre.
