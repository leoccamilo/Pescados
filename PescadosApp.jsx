import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Produtos iniciais padrão
const produtosIniciais = [
  { id: 1, nome: 'Camarão Regional', precoCompraPadrao: 25.00, precoVendaPadrao: 40.00 },
  { id: 2, nome: 'Camarão Rosa', precoCompraPadrao: 35.00, precoVendaPadrao: 55.00 },
  { id: 3, nome: 'Pescada Amarela', precoCompraPadrao: 18.00, precoVendaPadrao: 30.00 },
  { id: 4, nome: 'Dourada', precoCompraPadrao: 20.00, precoVendaPadrao: 35.00 },
  { id: 5, nome: 'Filhote', precoCompraPadrao: 28.00, precoVendaPadrao: 45.00 },
  { id: 6, nome: 'Pescada Gó', precoCompraPadrao: 15.00, precoVendaPadrao: 28.00 },
  { id: 7, nome: 'Pata de Caranguejo', precoCompraPadrao: 30.00, precoVendaPadrao: 50.00 },
  { id: 8, nome: 'Massa de Caranguejo', precoCompraPadrao: 40.00, precoVendaPadrao: 65.00 },
];

const CORES = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7300'];

const formatarMoeda = (valor) => {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
};

const formatarData = (data) => {
  return new Date(data).toLocaleDateString('pt-BR');
};

const formatarDataInput = (data) => {
  return new Date(data).toISOString().split('T')[0];
};

export default function PescadosApp() {
  // Estados principais
  const [produtos, setProdutos] = useState(() => {
    const saved = localStorage.getItem('pescados_produtos');
    return saved ? JSON.parse(saved) : produtosIniciais;
  });

  const [transacoes, setTransacoes] = useState(() => {
    const saved = localStorage.getItem('pescados_transacoes');
    return saved ? JSON.parse(saved) : [];
  });

  const [abaAtiva, setAbaAtiva] = useState('dashboard');
  const [filtroTempo, setFiltroTempo] = useState('mes');
  const [dataInicio, setDataInicio] = useState(() => {
    const hoje = new Date();
    hoje.setMonth(hoje.getMonth() - 1);
    return formatarDataInput(hoje);
  });
  const [dataFim, setDataFim] = useState(formatarDataInput(new Date()));

  // Estado para nova transação
  const [novaTransacao, setNovaTransacao] = useState({
    produtoId: '',
    tipo: 'compra',
    pesoKg: '',
    precoKg: '',
    data: formatarDataInput(new Date()),
  });

  // Estado para edição de produto
  const [produtoEditando, setProdutoEditando] = useState(null);
  const [novoProduto, setNovoProduto] = useState({
    nome: '',
    precoCompraPadrao: '',
    precoVendaPadrao: '',
  });

  // Persistência no localStorage
  useEffect(() => {
    localStorage.setItem('pescados_produtos', JSON.stringify(produtos));
  }, [produtos]);

  useEffect(() => {
    localStorage.setItem('pescados_transacoes', JSON.stringify(transacoes));
  }, [transacoes]);

  // Atualizar filtro de datas baseado no período selecionado
  useEffect(() => {
    const hoje = new Date();
    let inicio = new Date();

    switch (filtroTempo) {
      case 'dia':
        inicio = hoje;
        break;
      case 'semana':
        inicio.setDate(hoje.getDate() - 7);
        break;
      case 'mes':
        inicio.setMonth(hoje.getMonth() - 1);
        break;
      case 'ano':
        inicio.setFullYear(hoje.getFullYear() - 1);
        break;
      default:
        break;
    }

    setDataInicio(formatarDataInput(inicio));
    setDataFim(formatarDataInput(hoje));
  }, [filtroTempo]);

  // Atualizar preço padrão ao selecionar produto
  useEffect(() => {
    if (novaTransacao.produtoId) {
      const produto = produtos.find(p => p.id === parseInt(novaTransacao.produtoId));
      if (produto) {
        const preco = novaTransacao.tipo === 'compra' ? produto.precoCompraPadrao : produto.precoVendaPadrao;
        setNovaTransacao(prev => ({ ...prev, precoKg: preco.toString() }));
      }
    }
  }, [novaTransacao.produtoId, novaTransacao.tipo, produtos]);

  // Filtrar transações por período
  const transacoesFiltradas = useMemo(() => {
    return transacoes.filter(t => {
      const dataTransacao = new Date(t.data);
      const inicio = new Date(dataInicio);
      const fim = new Date(dataFim);
      fim.setHours(23, 59, 59);
      return dataTransacao >= inicio && dataTransacao <= fim;
    });
  }, [transacoes, dataInicio, dataFim]);

  // Calcular consolidações
  const consolidacoes = useMemo(() => {
    const porProduto = {};

    produtos.forEach(p => {
      porProduto[p.id] = {
        nome: p.nome,
        pesoComprado: 0,
        pesoVendido: 0,
        valorInvestido: 0,
        valorVendido: 0,
        lucro: 0,
      };
    });

    transacoesFiltradas.forEach(t => {
      if (porProduto[t.produtoId]) {
        if (t.tipo === 'compra') {
          porProduto[t.produtoId].pesoComprado += t.pesoKg;
          porProduto[t.produtoId].valorInvestido += t.valorTotal;
        } else {
          porProduto[t.produtoId].pesoVendido += t.pesoKg;
          porProduto[t.produtoId].valorVendido += t.valorTotal;
        }
        porProduto[t.produtoId].lucro = porProduto[t.produtoId].valorVendido - porProduto[t.produtoId].valorInvestido;
      }
    });

    const totais = Object.values(porProduto).reduce(
      (acc, p) => ({
        pesoComprado: acc.pesoComprado + p.pesoComprado,
        pesoVendido: acc.pesoVendido + p.pesoVendido,
        valorInvestido: acc.valorInvestido + p.valorInvestido,
        valorVendido: acc.valorVendido + p.valorVendido,
        lucro: acc.lucro + p.lucro,
      }),
      { pesoComprado: 0, pesoVendido: 0, valorInvestido: 0, valorVendido: 0, lucro: 0 }
    );

    return { porProduto, totais };
  }, [transacoesFiltradas, produtos]);

  // Dados para gráfico de barras
  const dadosBarras = useMemo(() => {
    return Object.entries(consolidacoes.porProduto)
      .filter(([_, dados]) => dados.valorInvestido > 0 || dados.valorVendido > 0)
      .map(([id, dados]) => ({
        nome: dados.nome.split(' ')[0],
        Investido: dados.valorInvestido,
        Vendido: dados.valorVendido,
      }));
  }, [consolidacoes]);

  // Dados para gráfico de linha (evolução do lucro)
  const dadosLinha = useMemo(() => {
    const lucrosPorData = {};

    transacoesFiltradas
      .sort((a, b) => new Date(a.data) - new Date(b.data))
      .forEach(t => {
        const dataStr = formatarData(t.data);
        if (!lucrosPorData[dataStr]) {
          lucrosPorData[dataStr] = 0;
        }
        if (t.tipo === 'venda') {
          lucrosPorData[dataStr] += t.valorTotal;
        } else {
          lucrosPorData[dataStr] -= t.valorTotal;
        }
      });

    let lucroAcumulado = 0;
    return Object.entries(lucrosPorData).map(([data, valor]) => {
      lucroAcumulado += valor;
      return { data, lucro: lucroAcumulado };
    });
  }, [transacoesFiltradas]);

  // Dados para gráfico de pizza
  const dadosPizza = useMemo(() => {
    return Object.entries(consolidacoes.porProduto)
      .filter(([_, dados]) => dados.valorVendido > 0)
      .map(([id, dados], index) => ({
        nome: dados.nome,
        valor: dados.valorVendido,
        cor: CORES[index % CORES.length],
      }));
  }, [consolidacoes]);

  // Handlers
  const handleRegistrarTransacao = (e) => {
    e.preventDefault();
    if (!novaTransacao.produtoId || !novaTransacao.pesoKg || !novaTransacao.precoKg) return;

    const pesoKg = parseFloat(novaTransacao.pesoKg);
    const precoKg = parseFloat(novaTransacao.precoKg);
    const valorTotal = pesoKg * precoKg;

    const transacao = {
      id: Date.now(),
      produtoId: parseInt(novaTransacao.produtoId),
      tipo: novaTransacao.tipo,
      pesoKg,
      precoKg,
      valorTotal,
      data: novaTransacao.data,
    };

    setTransacoes(prev => [transacao, ...prev]);
    setNovaTransacao({
      produtoId: '',
      tipo: 'compra',
      pesoKg: '',
      precoKg: '',
      data: formatarDataInput(new Date()),
    });
  };

  const handleExcluirTransacao = (id) => {
    if (confirm('Deseja excluir esta transação?')) {
      setTransacoes(prev => prev.filter(t => t.id !== id));
    }
  };

  const handleSalvarProduto = () => {
    if (produtoEditando) {
      setProdutos(prev => prev.map(p =>
        p.id === produtoEditando.id
          ? { ...p, ...novoProduto, precoCompraPadrao: parseFloat(novoProduto.precoCompraPadrao), precoVendaPadrao: parseFloat(novoProduto.precoVendaPadrao) }
          : p
      ));
    } else {
      const novoProd = {
        id: Date.now(),
        nome: novoProduto.nome,
        precoCompraPadrao: parseFloat(novoProduto.precoCompraPadrao),
        precoVendaPadrao: parseFloat(novoProduto.precoVendaPadrao),
      };
      setProdutos(prev => [...prev, novoProd]);
    }
    setProdutoEditando(null);
    setNovoProduto({ nome: '', precoCompraPadrao: '', precoVendaPadrao: '' });
  };

  const handleEditarProduto = (produto) => {
    setProdutoEditando(produto);
    setNovoProduto({
      nome: produto.nome,
      precoCompraPadrao: produto.precoCompraPadrao.toString(),
      precoVendaPadrao: produto.precoVendaPadrao.toString(),
    });
  };

  const handleExcluirProduto = (id) => {
    if (confirm('Deseja excluir este produto?')) {
      setProdutos(prev => prev.filter(p => p.id !== id));
    }
  };

  const getNomeProduto = (id) => {
    const produto = produtos.find(p => p.id === id);
    return produto ? produto.nome : 'Produto não encontrado';
  };

  const lucrativo = consolidacoes.totais.lucro >= 0;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl font-bold">🐟 Pescados do Alexandre</h1>
          <p className="text-blue-100 text-sm">Controle de Estoque e Lucratividade</p>
        </div>
      </header>

      {/* Navegação */}
      <nav className="bg-white shadow-md sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex overflow-x-auto">
          {[
            { id: 'dashboard', label: '📊 Dashboard' },
            { id: 'registro', label: '➕ Registrar' },
            { id: 'transacoes', label: '📋 Transações' },
            { id: 'graficos', label: '📈 Gráficos' },
            { id: 'produtos', label: '⚙️ Produtos' },
          ].map(aba => (
            <button
              key={aba.id}
              onClick={() => setAbaAtiva(aba.id)}
              className={`px-4 py-3 font-medium whitespace-nowrap transition-colors ${
                abaAtiva === aba.id
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
              }`}
            >
              {aba.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-4">
        {/* Dashboard */}
        {abaAtiva === 'dashboard' && (
          <div className="space-y-6">
            {/* Card Principal de Lucratividade */}
            <div className={`rounded-2xl p-6 shadow-lg ${lucrativo ? 'bg-green-500' : 'bg-red-500'} text-white`}>
              <div className="text-center">
                <p className="text-lg opacity-90">O negócio está lucrativo?</p>
                <p className="text-5xl font-bold my-2">{lucrativo ? '✅ SIM' : '❌ NÃO'}</p>
                <p className="text-3xl font-semibold">
                  {lucrativo ? 'Lucro: ' : 'Prejuízo: '}{formatarMoeda(Math.abs(consolidacoes.totais.lucro))}
                </p>
              </div>
            </div>

            {/* Filtros de Período */}
            <div className="bg-white rounded-xl p-4 shadow">
              <div className="flex flex-wrap gap-2 items-center">
                <span className="font-medium text-gray-700">Período:</span>
                {['dia', 'semana', 'mes', 'ano'].map(periodo => (
                  <button
                    key={periodo}
                    onClick={() => setFiltroTempo(periodo)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      filtroTempo === periodo
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {periodo === 'dia' ? 'Hoje' : periodo === 'semana' ? 'Semana' : periodo === 'mes' ? 'Mês' : 'Ano'}
                  </button>
                ))}
                <div className="flex gap-2 ml-auto">
                  <input
                    type="date"
                    value={dataInicio}
                    onChange={(e) => setDataInicio(e.target.value)}
                    className="px-3 py-2 border rounded-lg text-sm"
                  />
                  <span className="self-center text-gray-500">até</span>
                  <input
                    type="date"
                    value={dataFim}
                    onChange={(e) => setDataFim(e.target.value)}
                    className="px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Cards de Resumo */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-xl p-5 shadow">
                <p className="text-gray-500 text-sm">Total Investido</p>
                <p className="text-2xl font-bold text-orange-600">{formatarMoeda(consolidacoes.totais.valorInvestido)}</p>
                <p className="text-sm text-gray-400">{consolidacoes.totais.pesoComprado.toFixed(1)} kg comprados</p>
              </div>
              <div className="bg-white rounded-xl p-5 shadow">
                <p className="text-gray-500 text-sm">Total Vendido</p>
                <p className="text-2xl font-bold text-blue-600">{formatarMoeda(consolidacoes.totais.valorVendido)}</p>
                <p className="text-sm text-gray-400">{consolidacoes.totais.pesoVendido.toFixed(1)} kg vendidos</p>
              </div>
              <div className="bg-white rounded-xl p-5 shadow">
                <p className="text-gray-500 text-sm">Resultado</p>
                <p className={`text-2xl font-bold ${consolidacoes.totais.lucro >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatarMoeda(consolidacoes.totais.lucro)}
                </p>
                <p className="text-sm text-gray-400">{consolidacoes.totais.lucro >= 0 ? 'Lucro' : 'Prejuízo'}</p>
              </div>
            </div>

            {/* Tabela de Consolidação por Produto */}
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold text-gray-800">Consolidação por Produto</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Produto</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Comprado (kg)</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Vendido (kg)</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Investido</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Vendido</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Resultado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {Object.entries(consolidacoes.porProduto)
                      .filter(([_, dados]) => dados.valorInvestido > 0 || dados.valorVendido > 0)
                      .map(([id, dados]) => (
                        <tr key={id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-800">{dados.nome}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-600">{dados.pesoComprado.toFixed(1)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-600">{dados.pesoVendido.toFixed(1)}</td>
                          <td className="px-4 py-3 text-sm text-right text-orange-600">{formatarMoeda(dados.valorInvestido)}</td>
                          <td className="px-4 py-3 text-sm text-right text-blue-600">{formatarMoeda(dados.valorVendido)}</td>
                          <td className={`px-4 py-3 text-sm text-right font-semibold ${dados.lucro >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatarMoeda(dados.lucro)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                  <tfoot className="bg-gray-100 font-semibold">
                    <tr>
                      <td className="px-4 py-3 text-sm">TOTAL</td>
                      <td className="px-4 py-3 text-sm text-right">{consolidacoes.totais.pesoComprado.toFixed(1)}</td>
                      <td className="px-4 py-3 text-sm text-right">{consolidacoes.totais.pesoVendido.toFixed(1)}</td>
                      <td className="px-4 py-3 text-sm text-right text-orange-600">{formatarMoeda(consolidacoes.totais.valorInvestido)}</td>
                      <td className="px-4 py-3 text-sm text-right text-blue-600">{formatarMoeda(consolidacoes.totais.valorVendido)}</td>
                      <td className={`px-4 py-3 text-sm text-right ${consolidacoes.totais.lucro >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatarMoeda(consolidacoes.totais.lucro)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Registro de Transação */}
        {abaAtiva === 'registro' && (
          <div className="max-w-lg mx-auto">
            <div className="bg-white rounded-xl p-6 shadow">
              <h2 className="text-xl font-semibold text-gray-800 mb-6">Registrar Transação</h2>

              {/* Tipo de Transação */}
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => setNovaTransacao(prev => ({ ...prev, tipo: 'compra' }))}
                  className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
                    novaTransacao.tipo === 'compra'
                      ? 'bg-orange-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📥 Compra
                </button>
                <button
                  onClick={() => setNovaTransacao(prev => ({ ...prev, tipo: 'venda' }))}
                  className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
                    novaTransacao.tipo === 'venda'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📤 Venda
                </button>
              </div>

              {/* Seleção de Produto */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Selecione o Produto</label>
                <div className="grid grid-cols-2 gap-2">
                  {produtos.map(produto => (
                    <button
                      key={produto.id}
                      onClick={() => setNovaTransacao(prev => ({ ...prev, produtoId: produto.id.toString() }))}
                      className={`p-3 rounded-xl text-sm font-medium transition-all ${
                        novaTransacao.produtoId === produto.id.toString()
                          ? 'bg-blue-600 text-white ring-2 ring-blue-300'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {produto.nome}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleRegistrarTransacao} className="space-y-4">
                {/* Peso */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Peso (kg)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={novaTransacao.pesoKg}
                    onChange={(e) => setNovaTransacao(prev => ({ ...prev, pesoKg: e.target.value }))}
                    className="w-full px-4 py-3 border rounded-xl text-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Ex: 5.5"
                    required
                  />
                </div>

                {/* Preço por kg */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Preço por kg (R$)
                    <span className="text-gray-400 font-normal ml-2">
                      Padrão: {novaTransacao.produtoId && formatarMoeda(
                        novaTransacao.tipo === 'compra'
                          ? produtos.find(p => p.id === parseInt(novaTransacao.produtoId))?.precoCompraPadrao || 0
                          : produtos.find(p => p.id === parseInt(novaTransacao.produtoId))?.precoVendaPadrao || 0
                      )}
                    </span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={novaTransacao.precoKg}
                    onChange={(e) => setNovaTransacao(prev => ({ ...prev, precoKg: e.target.value }))}
                    className="w-full px-4 py-3 border rounded-xl text-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Ex: 35.00"
                    required
                  />
                </div>

                {/* Data */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data</label>
                  <input
                    type="date"
                    value={novaTransacao.data}
                    onChange={(e) => setNovaTransacao(prev => ({ ...prev, data: e.target.value }))}
                    className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>

                {/* Valor Total */}
                {novaTransacao.pesoKg && novaTransacao.precoKg && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-sm text-gray-600">Valor Total:</p>
                    <p className="text-2xl font-bold text-gray-800">
                      {formatarMoeda(parseFloat(novaTransacao.pesoKg) * parseFloat(novaTransacao.precoKg))}
                    </p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!novaTransacao.produtoId}
                  className={`w-full py-4 rounded-xl font-semibold text-white transition-colors ${
                    novaTransacao.produtoId
                      ? novaTransacao.tipo === 'compra'
                        ? 'bg-orange-500 hover:bg-orange-600'
                        : 'bg-blue-500 hover:bg-blue-600'
                      : 'bg-gray-300 cursor-not-allowed'
                  }`}
                >
                  {novaTransacao.tipo === 'compra' ? '📥 Registrar Compra' : '📤 Registrar Venda'}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Lista de Transações */}
        {abaAtiva === 'transacoes' && (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-800">Transações Recentes</h2>
              <span className="text-sm text-gray-500">{transacoes.length} transações</span>
            </div>
            <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
              {transacoes.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <p>Nenhuma transação registrada</p>
                  <p className="text-sm mt-1">Comece registrando uma compra ou venda</p>
                </div>
              ) : (
                transacoes.map(t => (
                  <div key={t.id} className="p-4 hover:bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${
                        t.tipo === 'compra' ? 'bg-orange-100' : 'bg-blue-100'
                      }`}>
                        {t.tipo === 'compra' ? '📥' : '📤'}
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{getNomeProduto(t.produtoId)}</p>
                        <p className="text-sm text-gray-500">
                          {t.pesoKg} kg × {formatarMoeda(t.precoKg)}/kg
                        </p>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-4">
                      <div>
                        <p className={`font-semibold ${t.tipo === 'compra' ? 'text-orange-600' : 'text-blue-600'}`}>
                          {t.tipo === 'compra' ? '-' : '+'}{formatarMoeda(t.valorTotal)}
                        </p>
                        <p className="text-sm text-gray-400">{formatarData(t.data)}</p>
                      </div>
                      <button
                        onClick={() => handleExcluirTransacao(t.id)}
                        className="text-red-400 hover:text-red-600 p-2"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Gráficos */}
        {abaAtiva === 'graficos' && (
          <div className="space-y-6">
            {/* Filtros de Período */}
            <div className="bg-white rounded-xl p-4 shadow">
              <div className="flex flex-wrap gap-2 items-center">
                <span className="font-medium text-gray-700">Período:</span>
                {['dia', 'semana', 'mes', 'ano'].map(periodo => (
                  <button
                    key={periodo}
                    onClick={() => setFiltroTempo(periodo)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      filtroTempo === periodo
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {periodo === 'dia' ? 'Hoje' : periodo === 'semana' ? 'Semana' : periodo === 'mes' ? 'Mês' : 'Ano'}
                  </button>
                ))}
              </div>
            </div>

            {/* Gráfico de Barras */}
            <div className="bg-white rounded-xl p-6 shadow">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Investido vs Vendido por Produto</h3>
              {dadosBarras.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dadosBarras}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="nome" />
                    <YAxis tickFormatter={(v) => `R$${v}`} />
                    <Tooltip formatter={(v) => formatarMoeda(v)} />
                    <Legend />
                    <Bar dataKey="Investido" fill="#f97316" />
                    <Bar dataKey="Vendido" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-gray-500 py-8">Nenhum dado no período selecionado</p>
              )}
            </div>

            {/* Gráfico de Linha */}
            <div className="bg-white rounded-xl p-6 shadow">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Evolução do Lucro</h3>
              {dadosLinha.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dadosLinha}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="data" />
                    <YAxis tickFormatter={(v) => `R$${v}`} />
                    <Tooltip formatter={(v) => formatarMoeda(v)} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="lucro"
                      name="Lucro Acumulado"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ fill: '#10b981' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-gray-500 py-8">Nenhum dado no período selecionado</p>
              )}
            </div>

            {/* Gráfico de Pizza */}
            <div className="bg-white rounded-xl p-6 shadow">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Distribuição de Vendas por Produto</h3>
              {dadosPizza.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={dadosPizza}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ nome, percent }) => `${nome.split(' ')[0]} (${(percent * 100).toFixed(0)}%)`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="valor"
                    >
                      {dadosPizza.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.cor} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatarMoeda(v)} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-gray-500 py-8">Nenhuma venda no período selecionado</p>
              )}
            </div>
          </div>
        )}

        {/* Gerenciamento de Produtos */}
        {abaAtiva === 'produtos' && (
          <div className="space-y-6">
            {/* Formulário de Produto */}
            <div className="bg-white rounded-xl p-6 shadow">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                {produtoEditando ? 'Editar Produto' : 'Adicionar Novo Produto'}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Produto</label>
                  <input
                    type="text"
                    value={novoProduto.nome}
                    onChange={(e) => setNovoProduto(prev => ({ ...prev, nome: e.target.value }))}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: Camarão Sete Barbas"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Preço Compra (R$/kg)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={novoProduto.precoCompraPadrao}
                    onChange={(e) => setNovoProduto(prev => ({ ...prev, precoCompraPadrao: e.target.value }))}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: 25.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Preço Venda (R$/kg)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={novoProduto.precoVendaPadrao}
                    onChange={(e) => setNovoProduto(prev => ({ ...prev, precoVendaPadrao: e.target.value }))}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: 40.00"
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleSalvarProduto}
                  disabled={!novoProduto.nome || !novoProduto.precoCompraPadrao || !novoProduto.precoVendaPadrao}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {produtoEditando ? 'Salvar Alterações' : 'Adicionar Produto'}
                </button>
                {produtoEditando && (
                  <button
                    onClick={() => {
                      setProdutoEditando(null);
                      setNovoProduto({ nome: '', precoCompraPadrao: '', precoVendaPadrao: '' });
                    }}
                    className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300"
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </div>

            {/* Lista de Produtos */}
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold text-gray-800">Produtos Cadastrados</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {produtos.map(produto => (
                  <div key={produto.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                    <div>
                      <p className="font-medium text-gray-800">{produto.nome}</p>
                      <p className="text-sm text-gray-500">
                        Compra: {formatarMoeda(produto.precoCompraPadrao)}/kg | Venda: {formatarMoeda(produto.precoVendaPadrao)}/kg
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditarProduto(produto)}
                        className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
                      >
                        ✏️ Editar
                      </button>
                      <button
                        onClick={() => handleExcluirProduto(produto.id)}
                        className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
                      >
                        🗑️ Excluir
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white p-4 mt-8">
        <div className="max-w-6xl mx-auto text-center text-sm">
          <p>Pescados do Alexandre © 2024</p>
          <p className="text-gray-400">Controle de Estoque e Lucratividade</p>
        </div>
      </footer>
    </div>
  );
}
