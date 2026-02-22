import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { PlusIcon, PencilIcon, TrashIcon, PlayIcon, StopIcon, ChevronDownIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

export default function Instances() {
  const [instances, setInstances] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [tradingPairs, setTradingPairs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingInstance, setEditingInstance] = useState(null);
  const [pairSearchQuery, setPairSearchQuery] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    account_id: '',
    strategy_id: '',
    symbols: [],
    timeframe: '1h',
    take_profit: null,
    stop_loss: null,
    position_mode: 'single',
    use_step_locking: false,
    step_config: { steps: [] },
    enable_trailing_stop: false,
    trailing_stop_percent: null,
    leverage: 10,
    status: 'stopped'
  });
  const [showPairDropdown, setShowPairDropdown] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetchInstances();
    fetchAccounts();
    fetchStrategies();
    fetchTradingPairs();
  }, []);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowPairDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchInstances = async () => {
    try {
      const response = await axios.get('/api/v1/instances');
      setInstances(response.data);
    } catch (error) {
      console.error('获取实例失败:', error);
    }
  };

  const fetchAccounts = async () => {
    try {
      const response = await axios.get('/api/v1/accounts');
      setAccounts(response.data);
    } catch (error) {
      console.error('获取账户失败:', error);
    }
  };

  const fetchStrategies = async () => {
    try {
      const response = await axios.get('/api/v1/strategies');
      setStrategies(response.data);
    } catch (error) {
      console.error('获取策略失败:', error);
    }
  };

  const fetchTradingPairs = async () => {
    try {
      const response = await axios.get('/api/symbols');
      setTradingPairs(response.data);
    } catch (error) {
      console.error('获取交易对失败:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // 构建提交数据
      const submitData = {
        name: formData.name,
        account_id: parseInt(formData.account_id),
        strategy_id: parseInt(formData.strategy_id),
        symbols: formData.symbols,
        timeframe: formData.timeframe,
        take_profit: formData.take_profit ? parseFloat(formData.take_profit) : null,
        stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : null,
        position_mode: formData.position_mode,
        use_step_locking: formData.use_step_locking,
        step_config: formData.use_step_locking ? formData.step_config : null,
        enable_trailing_stop: formData.enable_trailing_stop,
        trailing_stop_percent: formData.enable_trailing_stop && formData.trailing_stop_percent ? parseFloat(formData.trailing_stop_percent) : null,
        leverage: parseInt(formData.leverage)
      };

      if (editingInstance) {
        await axios.put(`/api/v1/instances/${editingInstance.id}`, submitData);
      } else {
        await axios.post('/api/v1/instances', submitData);
      }
      setShowModal(false);
      setEditingInstance(null);
      resetForm();
      fetchInstances();
    } catch (error) {
      console.error('保存实例失败:', error);
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      account_id: '',
      strategy_id: '',
      symbols: [],
      timeframe: '1h',
      take_profit: null,
      stop_loss: null,
      position_mode: 'single',
      use_step_locking: false,
      step_config: { steps: [] },
      enable_trailing_stop: false,
      trailing_stop_percent: null,
      leverage: 10,
      status: 'stopped'
    });
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确定要删除这个实例吗?')) return;
    try {
      await axios.delete(`/api/v1/instances/${id}`);
      fetchInstances();
    } catch (error) {
      console.error('删除实例失败:', error);
      alert('删除失败');
    }
  };

  const handleStatusToggle = async (instance) => {
    try {
      // P0修复: 调用正确的start/stop API
      if (instance.status === 'running') {
        await axios.post(`/api/v1/instances/${instance.id}/stop`);
      } else {
        await axios.post(`/api/v1/instances/${instance.id}/start`);
      }
      fetchInstances();
    } catch (error) {
      console.error('切换状态失败:', error);
      alert('操作失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const openEditModal = (instance) => {
    setEditingInstance(instance);
    setFormData({
      name: instance.name,
      account_id: instance.account_id,
      strategy_id: instance.strategy_id,
      symbols: instance.symbols || [],
      timeframe: instance.timeframe || '1h',
      take_profit: instance.take_profit,
      stop_loss: instance.stop_loss,
      position_mode: instance.position_mode || 'single',
      use_step_locking: instance.use_step_locking || false,
      step_config: instance.step_config || { steps: [] },
      enable_trailing_stop: instance.enable_trailing_stop || false,
      trailing_stop_percent: instance.trailing_stop_percent,
      leverage: instance.leverage || 10,
      status: instance.status
    });
    setShowModal(true);
  };

  const openCreateModal = () => {
    setEditingInstance(null);
    resetForm();
    setShowModal(true);
  };

  // 处理交易对选择
  const handlePairToggle = (pair) => {
    const currentPairs = formData.symbols || [];
    if (currentPairs.includes(pair)) {
      setFormData({
        ...formData,
        symbols: currentPairs.filter(p => p !== pair)
      });
    } else {
      setFormData({
        ...formData,
        symbols: [...currentPairs, pair]
      });
    }
  };

  // 过滤交易对
  const filteredTradingPairs = tradingPairs.filter(pair => 
    pair.symbol.toLowerCase().includes(pairSearchQuery.toLowerCase())
  );

  // 全选交易对（只全选过滤后的）
  const handleSelectAll = () => {
    setFormData({
      ...formData,
      symbols: [...new Set([...formData.symbols, ...filteredTradingPairs.map(p => p.symbol)])]
    });
  };

  // 清空选择
  const handleClearAll = () => {
    setFormData({
      ...formData,
      symbols: []
    });
  };

  // 移除单个交易对标签
  const handleRemovePair = (pair) => {
    setFormData({
      ...formData,
      symbols: formData.symbols.filter(p => p !== pair)
    });
  };

  // 添加分档锁盈档位
  const addStepLockLevel = () => {
    const newSteps = [...(formData.step_config.steps || []), { profit_percent: 0, lock_percent: 0 }];
    setFormData({
      ...formData,
      step_config: { steps: newSteps }
    });
  };

  // 删除分档锁盈档位
  const removeStepLockLevel = (index) => {
    const newSteps = formData.step_config.steps.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      step_config: { steps: newSteps }
    });
  };

  // 更新分档锁盈档位
  const updateStepLockLevel = (index, field, value) => {
    const newSteps = [...formData.step_config.steps];
    newSteps[index] = { ...newSteps[index], [field]: parseFloat(value) || 0 };
    setFormData({
      ...formData,
      step_config: { steps: newSteps }
    });
  };

  return (
    <div className="p-6" style={{ backgroundColor: 'var(--color-bg-primary)', minHeight: '100vh' }}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>交易实例</h1>
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
          创建实例
        </button>
      </div>

      <div className="rounded-lg shadow overflow-hidden" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
        <table className="min-w-full divide-y" style={{ borderColor: 'var(--color-border-primary)' }}>
          <thead style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>账户</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>策略</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>周期</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>交易对</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>操作</th>
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--color-border-primary)' }}>
            {instances.map((instance) => (
              <tr key={instance.id} className="transition-colors" onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'} onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}>
                <td className="px-6 py-4 whitespace-nowrap" style={{ color: 'var(--color-text-primary)' }}>{instance.name}</td>
                <td className="px-6 py-4 whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>
                  {accounts.find(a => a.id === instance.account_id)?.name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>
                  {strategies.find(s => s.id === instance.strategy_id)?.name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>{instance.timeframe || '-'}</td>
                <td className="px-6 py-4" style={{ color: 'var(--color-text-secondary)' }}>
                  <div className="flex flex-wrap gap-1">
                    {(instance.symbols || []).slice(0, 3).map(pair => (
                      <span key={pair} className="px-2 py-1 text-xs rounded" style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}>
                        {pair}
                      </span>
                    ))}
                    {(instance.symbols || []).length > 3 && (
                      <span className="px-2 py-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        +{(instance.symbols || []).length - 3}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs rounded-full font-medium" style={{ backgroundColor: instance.status === 'running' ? 'var(--color-accent-success)' : 'var(--color-border-secondary)', color: 'var(--color-text-inverse)' }}>
                    {instance.status === 'running' ? '运行中' : '已停止'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleStatusToggle(instance)} className="p-1 rounded transition-colors" style={{ color: 'var(--color-text-secondary)' }} title={instance.status === 'running' ? '停止' : '启动'}>
                      {instance.status === 'running' ? <StopIcon className="h-5 w-5" /> : <PlayIcon className="h-5 w-5" />}
                    </button>
                    <button onClick={() => openEditModal(instance)} className="p-1 rounded transition-colors" style={{ color: 'var(--color-text-secondary)' }} title="编辑">
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button onClick={() => handleDelete(instance.id)} className="p-1 rounded transition-colors" style={{ color: 'var(--color-text-secondary)' }} title="删除">
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 创建/编辑模态框 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
            <div className="p-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                {editingInstance ? '编辑实例' : '创建实例'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* 基本信息 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>实例名称 *</label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border"
                      style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>选择账户 *</label>
                    <select
                      required
                      value={formData.account_id}
                      onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border"
                      style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                    >
                      <option value="">请选择账户</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>{account.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>选择策略 *</label>
                    <select
                      required
                      value={formData.strategy_id}
                      onChange={(e) => setFormData({ ...formData, strategy_id: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border"
                      style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                    >
                      <option value="">请选择策略</option>
                      {strategies.map((strategy) => (
                        <option key={strategy.id} value={strategy.id}>{strategy.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                      K线时间周期 *
                      <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                        (策略执行的时间周期)
                      </span>
                    </label>
                    <select
                      required
                      value={formData.timeframe}
                      onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border"
                      style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                    >
                      <option value="1m">1分钟 (1m)</option>
                      <option value="3m">3分钟 (3m)</option>
                      <option value="5m">5分钟 (5m)</option>
                      <option value="15m">15分钟 (15m)</option>
                      <option value="30m">30分钟 (30m)</option>
                      <option value="1h">1小时 (1h)</option>
                      <option value="2h">2小时 (2h)</option>
                      <option value="4h">4小时 (4h)</option>
                      <option value="6h">6小时 (6h)</option>
                      <option value="8h">8小时 (8h)</option>
                      <option value="12h">12小时 (12h)</option>
                      <option value="1d">1天 (1d)</option>
                      <option value="3d">3天 (3d)</option>
                    </select>
                  </div>
                </div>

                {/* 风控配置 */}
                <div className="border-t pt-4" style={{ borderColor: 'var(--color-border-primary)' }}>
                  <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>风控配置 (可选)</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        止盈百分比 (%)
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (公式: TP_price = P_entry × (1 ± TP% / 100))
                        </span>
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={formData.take_profit || ''}
                        onChange={(e) => setFormData({ ...formData, take_profit: e.target.value })}
                        placeholder="例如: 5 表示5%"
                        className="w-full px-3 py-2 rounded-lg border"
                        style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        止损百分比 (%)
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (公式: SL_price = P_entry × (1 ∓ SL% / 100))
                        </span>
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={formData.stop_loss || ''}
                        onChange={(e) => setFormData({ ...formData, stop_loss: e.target.value })}
                        placeholder="例如: 2 表示2%"
                        className="w-full px-3 py-2 rounded-lg border"
                        style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        仓位模式
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (单仓/多仓)
                        </span>
                      </label>
                      <select
                        value={formData.position_mode}
                        onChange={(e) => setFormData({ ...formData, position_mode: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border"
                        style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                      >
                        <option value="single">单仓模式</option>
                        <option value="multiple">多仓模式</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        杠杆倍数 (Leverage)
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (公式: 仓位价值 = 保证金 × 杠杆)
                        </span>
                      </label>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        max="125"
                        value={formData.leverage}
                        onChange={(e) => setFormData({ ...formData, leverage: e.target.value })}
                        placeholder="例如: 10 表示10倍杠杆"
                        className="w-full px-3 py-2 rounded-lg border"
                        style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                      />
                    </div>
                  </div>

                  {/* 移动止损配置 */}
                  <div className="mt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        id="enable_trailing_stop"
                        checked={formData.enable_trailing_stop}
                        onChange={(e) => setFormData({ ...formData, enable_trailing_stop: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="enable_trailing_stop" className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                        启用移动止损 (Trailing Stop)
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (做多: Trailing_SL = P_peak × (1 - Trail% / 100))
                        </span>
                      </label>
                    </div>

                    {formData.enable_trailing_stop && (
                      <div className="mt-3 p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                          移动止损百分比 (%)
                          <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                            (根据最高价/最低价自动调整止损)
                          </span>
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          value={formData.trailing_stop_percent || ''}
                          onChange={(e) => setFormData({ ...formData, trailing_stop_percent: e.target.value })}
                          placeholder="例如: 1 表示1%"
                          className="w-full px-3 py-2 rounded-lg border"
                          style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                        />
                      </div>
                    )}
                  </div>

                  {/* 分档锁盈配置 */}
                  <div className="mt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        id="use_step_locking"
                        checked={formData.use_step_locking}
                        onChange={(e) => setFormData({ ...formData, use_step_locking: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="use_step_locking" className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                        启用分档锁盈 (Step Lock)
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--color-text-secondary)' }}>
                          (达到盈利百分比时，锁定部分利润)
                        </span>
                      </label>
                    </div>

                    {formData.use_step_locking && (
                      <div className="mt-3 p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>锁盈档位配置</span>
                          <button
                            type="button"
                            onClick={addStepLockLevel}
                            className="px-3 py-1 text-sm rounded-lg"
                            style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}
                          >
                            + 添加档位
                          </button>
                        </div>

                        {formData.step_config.steps.map((step, index) => (
                          <div key={index} className="flex items-center gap-2 mb-2">
                            <input
                              type="number"
                              step="0.1"
                              value={step.profit_percent}
                              onChange={(e) => updateStepLockLevel(index, 'profit_percent', e.target.value)}
                              placeholder="盈利%"
                              className="flex-1 px-3 py-2 rounded-lg border"
                              style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                            />
                            <span style={{ color: 'var(--color-text-secondary)' }}>时锁定</span>
                            <input
                              type="number"
                              step="0.1"
                              value={step.lock_percent}
                              onChange={(e) => updateStepLockLevel(index, 'lock_percent', e.target.value)}
                              placeholder="锁定%"
                              className="flex-1 px-3 py-2 rounded-lg border"
                              style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                            />
                            <button
                              type="button"
                              onClick={() => removeStepLockLevel(index)}
                              className="p-2 rounded-lg text-red-500 hover:bg-red-50"
                            >
                              <XMarkIcon className="h-5 w-5" />
                            </button>
                          </div>
                        ))}

                        {formData.step_config.steps.length === 0 && (
                          <p className="text-sm text-center py-4" style={{ color: 'var(--color-text-secondary)' }}>
                            暂无档位，点击"添加档位"开始配置
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* 交易对选择 */}
                <div className="border-t pt-4" style={{ borderColor: 'var(--color-border-primary)' }}>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>选择交易对 *</label>
                  
                  <div className="relative" ref={dropdownRef}>
                    <button
                      type="button"
                      onClick={() => setShowPairDropdown(!showPairDropdown)}
                      className="w-full px-3 py-2 rounded-lg border flex items-center justify-between"
                      style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                    >
                      <span>{formData.symbols.length > 0 ? `已选择 ${formData.symbols.length} 个交易对` : '请选择交易对'}</span>
                      <ChevronDownIcon className="h-5 w-5" />
                    </button>

                    {showPairDropdown && (
                      <div className="absolute z-10 mt-1 w-full rounded-lg shadow-lg border max-h-96 overflow-y-auto" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                        {/* 搜索框 */}
                        <div className="sticky top-0 p-3 border-b" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                          <input
                            type="text"
                            placeholder="搜索交易对 (例如: BTC, ETH, BNB)"
                            value={pairSearchQuery}
                            onChange={(e) => setPairSearchQuery(e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border"
                            style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)', color: 'var(--color-text-primary)' }}
                          />
                          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>提示: 输入关键词过滤USDT本位交易对</p>
                        </div>
                        
                        {/* 全选/清空按钮 */}
                        <div className="sticky top-[72px] p-2 border-b flex gap-2" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                          <button type="button" onClick={handleSelectAll} className="flex-1 px-3 py-1 text-sm rounded" style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}>全选</button>
                          <button type="button" onClick={handleClearAll} className="flex-1 px-3 py-1 text-sm rounded" style={{ backgroundColor: 'var(--color-border-secondary)', color: 'var(--color-text-primary)' }}>清空</button>
                        </div>
                        
                        {/* 交易对列表 */}
                        <div className="p-2">
                          {filteredTradingPairs.length > 0 ? (
                            filteredTradingPairs.map((pair) => (
                            <label key={pair.symbol} className="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-opacity-50" style={{ backgroundColor: formData.symbols.includes(pair.symbol) ? 'var(--color-interactive-hover)' : 'transparent' }}>
                              <input
                                type="checkbox"
                                checked={formData.symbols.includes(pair.symbol)}
                                onChange={() => handlePairToggle(pair.symbol)}
                                className="rounded"
                              />
                              <span style={{ color: 'var(--color-text-primary)' }}>{pair.symbol}</span>
                              {formData.symbols.includes(pair.symbol) && <CheckIcon className="h-4 w-4 ml-auto" style={{ color: 'var(--color-accent-success)' }} />}
                            </label>
                          )))
                          ) : (
                            <div className="p-4 text-center" style={{ color: 'var(--color-text-secondary)' }}>
                              未找到匹配的交易对，请尝试其他关键词
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 已选择的交易对标签 */}
                  {formData.symbols.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {formData.symbols.map((pair) => (
                        <span key={pair} className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm" style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}>
                          {pair}
                          <button type="button" onClick={() => handleRemovePair(pair)} className="hover:bg-white hover:bg-opacity-20 rounded-full p-0.5">
                            <XMarkIcon className="h-4 w-4" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* 按钮 */}
                <div className="flex justify-end gap-3 pt-4 border-t" style={{ borderColor: 'var(--color-border-primary)' }}>
                  <button
                    type="button"
                    onClick={() => { setShowModal(false); resetForm(); }}
                    className="px-4 py-2 rounded-lg"
                    style={{ backgroundColor: 'var(--color-border-secondary)', color: 'var(--color-text-primary)' }}
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg"
                    style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}
                  >
                    {editingInstance ? '保存' : '创建'}
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
