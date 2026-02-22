import { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowPathIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export default function Symbols() {
  const [symbols, setSymbols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedExchange, setSelectedExchange] = useState('binance');

  useEffect(() => {
    loadSymbols();
  }, [selectedExchange]);

  const loadSymbols = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/symbols/exchanges/${selectedExchange}/symbols`);
      setSymbols(response.data || []);
    } catch (error) {
      console.error('加载交易对失败:', error);
      alert('加载交易对失败！');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`/api/symbols/exchanges/${selectedExchange}/symbols/refresh`);
      alert('刷新成功！');
      await loadSymbols();
    } catch (error) {
      console.error('刷新交易对失败:', error);
      alert('刷新交易对失败！');
    } finally {
      setRefreshing(false);
    }
  };

  const filteredSymbols = symbols.filter(symbol =>
    symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>交易对管理</h1>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
          style={{
            backgroundColor: 'var(--color-accent-primary)',
            color: 'var(--color-text-inverse)'
          }}
          onMouseEnter={(e) => !refreshing && (e.currentTarget.style.filter = 'brightness(1.1)')}
          onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(1)'}
        >
          <ArrowPathIcon className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? '刷新中...' : '刷新交易对'}
        </button>
      </div>

      {/* 筛选区域 */}
      <div className="rounded-lg shadow p-4" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 交易所选择 */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
              交易所
            </label>
            <select
              value={selectedExchange}
              onChange={(e) => setSelectedExchange(e.target.value)}
              className="w-full rounded-lg px-3 py-2"
              style={{
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border-primary)'
              }}
            >
              <option value="binance">Binance</option>
              <option value="okx">OKX</option>
              <option value="bybit">Bybit</option>
            </select>
          </div>

          {/* 搜索框 */}
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
              搜索交易对
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="输入交易对名称..."
                className="w-full rounded-lg px-3 py-2 pl-10"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border-primary)'
                }}
              />
              <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-2.5" style={{ color: 'var(--color-text-tertiary)' }} />
            </div>
          </div>
        </div>
      </div>

      {/* 统计信息 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg shadow p-4" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>总交易对数</div>
          <div className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
            {symbols.length}
          </div>
        </div>
        <div className="rounded-lg shadow p-4" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>筛选结果</div>
          <div className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
            {filteredSymbols.length}
          </div>
        </div>
        <div className="rounded-lg shadow p-4" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>交易所</div>
          <div className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
            {selectedExchange.toUpperCase()}
          </div>
        </div>
      </div>

      {/* 交易对列表 */}
      <div className="rounded-lg shadow overflow-hidden" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2" style={{ color: 'var(--color-text-tertiary)' }} />
              <p style={{ color: 'var(--color-text-secondary)' }}>加载中...</p>
            </div>
          </div>
        ) : filteredSymbols.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <p style={{ color: 'var(--color-text-secondary)' }}>
              {searchTerm ? '没有找到匹配的交易对' : '暂无交易对数据'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 p-4">
            {filteredSymbols.map((symbol, index) => (
              <div
                key={index}
                className="px-3 py-2 rounded text-center font-mono text-sm transition-colors"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border-primary)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)'}
              >
                {symbol}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
