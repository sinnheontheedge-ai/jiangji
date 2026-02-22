import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PlusIcon, PencilIcon, TrashIcon, EyeIcon, EyeSlashIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [showApiSecret, setShowApiSecret] = useState({});
  const [balances, setBalances] = useState({});
  const [loadingBalances, setLoadingBalances] = useState({});
  const [formData, setFormData] = useState({
    name: '',
    exchange: 'binance',
    api_key: '',
    api_secret: '',
    testnet: false,
    proxy_enabled: false,
    proxy_host: '127.0.0.1',
    proxy_port: '7890'
  });

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get('/api/v1/accounts');
      setAccounts(response.data);
    } catch (error) {
      console.error('获取账户失败:', error);
    }
  };

  const refreshBalance = async (accountId) => {
    setLoadingBalances(prev => ({ ...prev, [accountId]: true }));
    try {
      const response = await axios.get(`/api/v1/accounts/${accountId}/balance`);
      setBalances(prev => ({ ...prev, [accountId]: response.data }));
      alert('余额刷新成功！');
    } catch (error) {
      console.error('刷新余额失败:', error);
      alert('刷新余额失败！');
    } finally {
      setLoadingBalances(prev => ({ ...prev, [accountId]: false }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // 构建提交数据
    const submitData = {
      name: formData.name,
      exchange: formData.exchange,
      api_key: formData.api_key,
      api_secret: formData.api_secret,
      testnet: formData.testnet,
      proxy_config: formData.proxy_enabled ? {
        host: formData.proxy_host,
        port: parseInt(formData.proxy_port)
      } : null
    };
    
    try {
      if (editingAccount) {
        await axios.put(`/api/v1/accounts/${editingAccount.id}`, submitData);
      } else {
        await axios.post('/api/v1/accounts', submitData);
      }
      setShowModal(false);
      setEditingAccount(null);
      setFormData({
        name: '',
        exchange: 'binance',
        api_key: '',
        api_secret: '',
        testnet: false
      });
      fetchAccounts();
    } catch (error) {
      console.error('保存账户失败:', error);
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确定要删除这个账户吗?')) return;
    try {
      await axios.delete(`/api/v1/accounts/${id}`);
      fetchAccounts();
    } catch (error) {
      console.error('删除账户失败:', error);
      alert('删除失败');
    }
  };

  const openEditModal = (account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      exchange: account.exchange,
      api_key: account.api_key,
      api_secret: account.api_secret || '',
      testnet: account.testnet || false,
      proxy_enabled: account.proxy_config ? true : false,
      proxy_host: account.proxy_config?.host || '127.0.0.1',
      proxy_port: account.proxy_config?.port || '7890'
    });
    setShowModal(true);
  };

  const openCreateModal = () => {
    setEditingAccount(null);
    setFormData({
      name: '',
      exchange: 'binance',
      api_key: '',
      api_secret: '',
      testnet: false,
      proxy_enabled: false,
      proxy_host: '127.0.0.1',
      proxy_port: '7890'
    });
    setShowModal(true);
  };

  const toggleSecretVisibility = (accountId) => {
    setShowApiSecret(prev => ({
      ...prev,
      [accountId]: !prev[accountId]
    }));
  };

  const maskSecret = (secret) => {
    if (!secret) return '未设置';
    return '•'.repeat(20);
  };

  return (
    <div className="p-6" style={{ backgroundColor: 'var(--color-bg-primary)', minHeight: '100vh' }}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>账户管理</h1>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
          style={{
            backgroundColor: 'var(--color-accent-primary)',
            color: 'var(--color-text-inverse)'
          }}
          onMouseEnter={(e) => e.currentTarget.style.filter = 'brightness(1.1)'}
          onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(1)'}
        >
          <PlusIcon className="h-5 w-5" />
          添加账户
        </button>
      </div>

      <div className="rounded-lg shadow overflow-hidden" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
        <table className="min-w-full divide-y" style={{ borderColor: 'var(--color-border-primary)' }}>
          <thead style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                账户名称
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                交易所
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                API Key
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                API Secret
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                测试网
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                余额 (USDT)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--color-border-primary)' }}>
            {accounts.map((account) => (
              <tr key={account.id} className="transition-colors" onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'} onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}>
                <td className="px-6 py-4 whitespace-nowrap font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  {account.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>
                  <span
                    className="px-2 py-1 text-xs rounded-full font-medium"
                    style={{
                      backgroundColor: 'var(--color-accent-info)',
                      color: 'var(--color-text-inverse)'
                    }}
                  >
                    {account.exchange.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-mono text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  {account.api_key ? account.api_key.substring(0, 16) + '...' : '未设置'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-mono text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  <div className="flex items-center gap-2">
                    <span>
                      {showApiSecret[account.id] ? account.api_secret : maskSecret(account.api_secret)}
                    </span>
                    <button
                      onClick={() => toggleSecretVisibility(account.id)}
                      className="p-1 rounded transition-colors"
                      style={{ color: 'var(--color-text-tertiary)' }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)';
                        e.currentTarget.style.color = 'var(--color-accent-primary)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.color = 'var(--color-text-tertiary)';
                      }}
                    >
                      {showApiSecret[account.id] ? (
                        <EyeSlashIcon className="h-4 w-4" />
                      ) : (
                        <EyeIcon className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {account.testnet ? (
                    <span
                      className="px-2 py-1 text-xs rounded-full font-medium"
                      style={{
                        backgroundColor: 'var(--color-accent-warning)',
                        color: 'var(--color-text-inverse)'
                      }}
                    >
                      测试网
                    </span>
                  ) : (
                    <span
                      className="px-2 py-1 text-xs rounded-full font-medium"
                      style={{
                        backgroundColor: 'var(--color-accent-success)',
                        color: 'var(--color-text-inverse)'
                      }}
                    >
                      正式网
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center gap-2">
                    {balances[account.id] ? (
                      <span className="font-mono font-medium" style={{ color: 'var(--color-accent-success)' }}>
                        {parseFloat(balances[account.id].totalWalletBalance || 0).toFixed(2)}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-text-tertiary)' }}>--</span>
                    )}
                    <button
                      onClick={() => refreshBalance(account.id)}
                      disabled={loadingBalances[account.id]}
                      className="p-1 rounded transition-colors"
                      style={{ color: 'var(--color-text-secondary)' }}
                      onMouseEnter={(e) => {
                        if (!loadingBalances[account.id]) {
                          e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)';
                          e.currentTarget.style.color = 'var(--color-accent-primary)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                      }}
                      title="刷新余额"
                    >
                      <ArrowPathIcon className={`h-4 w-4 ${loadingBalances[account.id] ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openEditModal(account)}
                      className="p-1 rounded transition-colors"
                      style={{ color: 'var(--color-text-secondary)' }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)';
                        e.currentTarget.style.color = 'var(--color-accent-primary)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                      }}
                      title="编辑"
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(account.id)}
                      className="p-1 rounded transition-colors"
                      style={{ color: 'var(--color-text-secondary)' }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)';
                        e.currentTarget.style.color = 'var(--color-accent-error)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                      }}
                      title="删除"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {accounts.length === 0 && (
          <div className="text-center py-12">
            <p style={{ color: 'var(--color-text-secondary)' }}>
              暂无账户,点击右上角"添加账户"按钮创建第一个账户
            </p>
          </div>
        )}
      </div>

      {/* 创建/编辑模态框 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="rounded-lg shadow-xl max-w-md w-full" style={{ backgroundColor: 'var(--color-bg-modal)' }}>
            <div className="p-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                {editingAccount ? '编辑账户' : '添加账户'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    账户名称
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2"
                    style={{
                      backgroundColor: 'var(--color-bg-tertiary)',
                      borderColor: 'var(--color-border-primary)',
                      color: 'var(--color-text-primary)'
                    }}
                    placeholder="例如: 我的币安账户"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    交易所
                  </label>
                  <select
                    value={formData.exchange}
                    onChange={(e) => setFormData({ ...formData, exchange: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2"
                    style={{
                      backgroundColor: 'var(--color-bg-tertiary)',
                      borderColor: 'var(--color-border-primary)',
                      color: 'var(--color-text-primary)'
                    }}
                    required
                  >
                    <option value="binance">Binance (币安)</option>
                    <option value="okx">OKX (欧易)</option>
                    <option value="bybit">Bybit</option>
                    <option value="gate">Gate.io</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    API Key
                  </label>
                  <input
                    type="text"
                    value={formData.api_key}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 font-mono text-sm"
                    style={{
                      backgroundColor: 'var(--color-bg-tertiary)',
                      borderColor: 'var(--color-border-primary)',
                      color: 'var(--color-text-primary)'
                    }}
                    placeholder="粘贴您的API Key"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    API Secret
                  </label>
                  <input
                    type="password"
                    value={formData.api_secret}
                    onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 font-mono text-sm"
                    style={{
                      backgroundColor: 'var(--color-bg-tertiary)',
                      borderColor: 'var(--color-border-primary)',
                      color: 'var(--color-text-primary)'
                    }}
                    placeholder="粘贴您的API Secret"
                    required
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="testnet"
                    checked={formData.testnet}
                    onChange={(e) => setFormData({ ...formData, testnet: e.target.checked })}
                    className="h-4 w-4 rounded"
                    style={{ accentColor: 'var(--color-accent-primary)' }}
                  />
                  <label htmlFor="testnet" className="ml-2 text-sm" style={{ color: 'var(--color-text-primary)' }}>
                    使用测试网 (Testnet)
                  </label>
                </div>

                {/* 代理配置 */}
                <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center mb-3">
                    <input
                      type="checkbox"
                      id="proxy_enabled"
                      checked={formData.proxy_enabled}
                      onChange={(e) => setFormData({ ...formData, proxy_enabled: e.target.checked })}
                      className="h-4 w-4 rounded"
                      style={{ accentColor: 'var(--color-accent-primary)' }}
                    />
                    <label htmlFor="proxy_enabled" className="ml-2 text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                      🌐 使用代理连接 (中国大陆用户必需)
                    </label>
                  </div>
                  
                  {formData.proxy_enabled && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                          代理主机
                        </label>
                        <input
                          type="text"
                          value={formData.proxy_host}
                          onChange={(e) => setFormData({ ...formData, proxy_host: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 text-sm"
                          style={{
                            backgroundColor: 'var(--color-bg-tertiary)',
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-primary)'
                          }}
                          placeholder="127.0.0.1"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                          代理端口
                        </label>
                        <input
                          type="number"
                          value={formData.proxy_port}
                          onChange={(e) => setFormData({ ...formData, proxy_port: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 text-sm"
                          style={{
                            backgroundColor: 'var(--color-bg-tertiary)',
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-primary)'
                          }}
                          placeholder="7890"
                        />
                      </div>
                    </div>
                  )}
                  
                  {formData.proxy_enabled && (
                    <p className="text-xs mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                      💡 常见代理端口: Clash(7890), V2Ray(10809), Shadowsocks(1080)
                    </p>
                  )}
                </div>

                <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border-primary)' }}>
                  <p className="text-xs mb-3" style={{ color: 'var(--color-text-tertiary)' }}>
                    ⚠️ 请确保API密钥仅具有交易权限,不要授予提现权限
                  </p>
                </div>

                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingAccount(null);
                    }}
                    className="px-4 py-2 rounded-lg transition-colors"
                    style={{
                      backgroundColor: 'var(--color-bg-secondary)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid var(--color-border-primary)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg font-medium transition-colors"
                    style={{
                      backgroundColor: 'var(--color-accent-primary)',
                      color: 'var(--color-text-inverse)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.filter = 'brightness(1.1)'}
                    onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(1)'}
                  >
                    {editingAccount ? '保存' : '添加'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
