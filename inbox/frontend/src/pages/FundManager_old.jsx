import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  CurrencyDollarIcon, 
  ArrowTrendingUpIcon, 
  ShieldCheckIcon,
  FlagIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function FundManager() {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [status, setStatus] = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configForm, setConfigForm] = useState({
    // 复利配置
    compounding_mode: 'stage',
    compound_ratio: 20,
    initial_base: 1000,
    position_percent: 10,
    concurrent_positions: 1,
    
    // 盈利提取配置
    extraction_mode: 'wallet_threshold',
    initial_margin: 1000,
    threshold: 2000,
    multiple: 2.0,
    max_extract_ratio: null,
    
    // 初始金额保护
    protection_enabled: false,
    protection_initial_amount: 1000,
    protection_multiple: 2.0,
    protection_max_count: 1,
    protection_transfer_step: 10,
    
    // 盈利倍数终点
    endpoint_enabled: false,
    endpoint_initial_amount: 1000,
    endpoint_multiple: 10.0,
    endpoint_transfer_step: 10,
    
    // 自动补足余额
    replenish_enabled: false,
    replenish_initial_capital: 1000,
    replenish_check_interval: 60,
    replenish_min_amount: 10,
    replenish_enable_alert: true,
    replenish_alert_threshold: 0.8,
    replenish_max_per_day: 10
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccountId) {
      loadStatus();
    }
  }, [selectedAccountId]);

  const loadAccounts = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/accounts`);
      setAccounts(response.data);
      
      // 默认选择第一个账户
      if (response.data.length > 0 && !selectedAccountId) {
        setSelectedAccountId(response.data[0].account_id);
      }
    } catch (error) {
      console.error('加载账户列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    if (!selectedAccountId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/fund-manager/status/${selectedAccountId}`);
      setStatus(response.data);
      
      // 填充配置表单
      if (response.data.compounding_status) {
        const cs = response.data.compounding_status;
        setConfigForm(prev => ({
          ...prev,
          compounding_mode: cs.mode,
          compound_ratio: cs.compound_ratio,
          initial_base: cs.initial_base,
          position_percent: cs.position_percent,
          concurrent_positions: cs.concurrent_positions
        }));
      }
      
      if (response.data.profit_extraction_status) {
        const ps = response.data.profit_extraction_status;
        setConfigForm(prev => ({
          ...prev,
          extraction_mode: ps.mode,
          initial_margin: ps.initial_margin,
          threshold: ps.threshold || 2000,
          multiple: ps.multiple || 2.0,
          max_extract_ratio: ps.max_extract_ratio
        }));
      }
      
    } catch (error) {
      if (error.response?.status === 404) {
        // 未配置,显示配置模态框
        setStatus(null);
      } else {
        console.error('加载资金管理状态失败:', error);
      }
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    
    if (!selectedAccountId) {
      alert('请先选择账户');
      return;
    }
    
    try {
      const config = {
        account_id: selectedAccountId,
        compounding: {
          mode: configForm.compounding_mode,
          compound_ratio: parseFloat(configForm.compound_ratio),
          initial_base: parseFloat(configForm.initial_base),
          position_percent: parseFloat(configForm.position_percent),
          concurrent_positions: parseInt(configForm.concurrent_positions)
        },
        profit_extraction: {
          mode: configForm.extraction_mode,
          initial_margin: parseFloat(configForm.initial_margin),
          threshold: configForm.extraction_mode === 'wallet_threshold' ? parseFloat(configForm.threshold) : null,
          multiple: configForm.extraction_mode === 'multiple_mode' ? parseFloat(configForm.multiple) : null,
          max_extract_ratio: configForm.max_extract_ratio ? parseFloat(configForm.max_extract_ratio) : null
        }
      };
      
      // 添加初始金额保护配置
      if (configForm.protection_enabled) {
        config.capital_protection = {
          enabled: true,
          initial_amount: parseFloat(configForm.protection_initial_amount),
          protect_multiple: parseFloat(configForm.protection_multiple),
          max_protect_count: parseInt(configForm.protection_max_count),
          transfer_step: parseFloat(configForm.protection_transfer_step)
        };
      } else {
        config.capital_protection = { enabled: false };
      }
      
      // 添加盈利倍数终点配置
      if (configForm.endpoint_enabled) {
        config.profit_endpoint = {
          enabled: true,
          initial_amount: parseFloat(configForm.endpoint_initial_amount),
          endpoint_multiple: parseFloat(configForm.endpoint_multiple),
          transfer_step: parseFloat(configForm.endpoint_transfer_step)
        };
      } else {
        config.profit_endpoint = { enabled: false };
      }
      
      // 添加自动补足余额配置
      if (configForm.replenish_enabled) {
        config.auto_replenish = {
          enabled: true,
          initial_capital: parseFloat(configForm.replenish_initial_capital),
          check_interval: parseInt(configForm.replenish_check_interval),
          min_transfer_amount: parseFloat(configForm.replenish_min_amount),
          enable_alert: configForm.replenish_enable_alert,
          alert_threshold: parseFloat(configForm.replenish_alert_threshold),
          max_replenish_per_day: parseInt(configForm.replenish_max_per_day)
        };
      } else {
        config.auto_replenish = { enabled: false };
      }
      
      await axios.post(`${API_BASE_URL}/api/fund-manager/config`, config);
      alert('配置保存成功!');
      setShowConfigModal(false);
      await loadStatus();
      
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || '保存失败';
      alert('保存配置失败: ' + errorMsg);
      console.error('保存配置失败:', error);
    }
  };

  const handleReset = async () => {
    if (!selectedAccountId) {
      alert('请先选择账户');
      return;
    }
    
    if (!confirm('确定要重置该账户的资金管理状态吗?这将清除所有运行时数据。')) return;
    
    try {
      await axios.post(`${API_BASE_URL}/api/fund-manager/reset/${selectedAccountId}`);
      alert('重置成功!');
      await loadStatus();
    } catch (error) {
      alert('重置失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteConfig = async () => {
    if (!selectedAccountId) {
      alert('请先选择账户');
      return;
    }
    
    if (!confirm('确定要删除该账户的资金管理配置吗?')) return;
    
    try {
      await axios.delete(`${API_BASE_URL}/api/fund-manager/config/${selectedAccountId}`);
      alert('配置删除成功!');
      setStatus(null);
    } catch (error) {
      alert('删除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <p className="text-yellow-800 mb-4">尚未添加任何账户</p>
        <p className="text-sm text-yellow-600">请先在"账户管理"中添加账户</p>
      </div>
    );
  }

  const selectedAccount = accounts.find(acc => acc.account_id === selectedAccountId);

  return (
    <div className="space-y-6">
      {/* 标题栏和账户选择 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">资金管理</h1>
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(parseInt(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            {accounts.map(account => (
              <option key={account.account_id} value={account.account_id}>
                {account.name} ({account.exchange})
              </option>
            ))}
          </select>
        </div>
        <div className="space-x-3">
          <button
            onClick={() => setShowConfigModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <Cog6ToothIcon className="h-5 w-5 mr-2" />
            配置
          </button>
          {status && (
            <>
              <button
                onClick={handleReset}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                重置状态
              </button>
              <button
                onClick={handleDeleteConfig}
                className="inline-flex items-center px-4 py-2 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-white hover:bg-red-50"
              >
                删除配置
              </button>
            </>
          )}
        </div>
      </div>

      {!status ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800 mb-4">账户 "{selectedAccount?.name}" 尚未配置资金管理</p>
          <button
            onClick={() => setShowConfigModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            立即配置
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 复利系统状态 */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center mb-4">
              <ArrowTrendingUpIcon className="h-6 w-6 text-green-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">复利系统</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">模式:</span>
                <span className="font-medium">
                  {status.compounding_status.mode === 'stage' ? '阶段复利' : '永续复利'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">复利比例:</span>
                <span className="font-medium">{status.compounding_status.compound_ratio}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">复利因子:</span>
                <span className="font-medium">{status.compounding_status.compound_factor.toFixed(2)}</span>
              </div>
              {status.compounding_status.mode === 'stage' && (
                <>
                  <div className="flex justify-between">
                    <span className="text-gray-600">初始起点:</span>
                    <span className="font-medium">${status.compounding_status.initial_base.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">当前起点:</span>
                    <span className="font-medium text-green-600">
                      ${status.compounding_status.current_base.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">下次升档阈值:</span>
                    <span className="font-medium text-blue-600">
                      ${status.compounding_status.next_threshold.toFixed(2)}
                    </span>
                  </div>
                </>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">仓位百分比:</span>
                <span className="font-medium">{status.compounding_status.position_percent}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">并发仓位数:</span>
                <span className="font-medium">{status.compounding_status.concurrent_positions}</span>
              </div>
            </div>
          </div>

          {/* 盈利提取状态 */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center mb-4">
              <CurrencyDollarIcon className="h-6 w-6 text-blue-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">盈利提取</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">模式:</span>
                <span className="font-medium">
                  {status.profit_extraction_status.mode === 'wallet_threshold' ? '钱包阈值' : '倍数模式'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">初始保证金:</span>
                <span className="font-medium">${status.profit_extraction_status.initial_margin.toFixed(2)}</span>
              </div>
              {status.profit_extraction_status.threshold && (
                <div className="flex justify-between">
                  <span className="text-gray-600">提取阈值:</span>
                  <span className="font-medium text-blue-600">
                    ${status.profit_extraction_status.threshold.toFixed(2)}
                  </span>
                </div>
              )}
              {status.profit_extraction_status.multiple && (
                <div className="flex justify-between">
                  <span className="text-gray-600">提取倍数:</span>
                  <span className="font-medium text-blue-600">
                    {status.profit_extraction_status.multiple.toFixed(1)}x
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">下次提取阈值:</span>
                <span className="font-medium text-green-600">
                  ${status.profit_extraction_status.next_threshold.toFixed(2)}
                </span>
              </div>
              {status.profit_extraction_status.max_extract_ratio && (
                <div className="flex justify-between">
                  <span className="text-gray-600">最大提取比例:</span>
                  <span className="font-medium">
                    {(status.profit_extraction_status.max_extract_ratio * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* 初始金额保护状态 */}
          {status.capital_protection_status && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center mb-4">
                <ShieldCheckIcon className="h-6 w-6 text-yellow-600 mr-2" />
                <h2 className="text-lg font-semibold text-gray-900">初始金额保护</h2>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">初始金额:</span>
                  <span className="font-medium">${status.capital_protection_status.initial_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">保护倍数:</span>
                  <span className="font-medium">{status.capital_protection_status.protect_multiple.toFixed(1)}x</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">保护阈值:</span>
                  <span className="font-medium text-blue-600">
                    ${status.capital_protection_status.threshold.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">已执行次数:</span>
                  <span className="font-medium">
                    {status.capital_protection_status.protect_count} / {status.capital_protection_status.max_protect_count}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 盈利倍数终点状态 */}
          {status.profit_endpoint_status && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center mb-4">
                <FlagIcon className="h-6 w-6 text-red-600 mr-2" />
                <h2 className="text-lg font-semibold text-gray-900">盈利倍数终点</h2>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">初始金额:</span>
                  <span className="font-medium">${status.profit_endpoint_status.initial_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">终点倍数:</span>
                  <span className="font-medium">{status.profit_endpoint_status.endpoint_multiple.toFixed(1)}x</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">终点阈值:</span>
                  <span className="font-medium text-blue-600">
                    ${status.profit_endpoint_status.threshold.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">状态:</span>
                  <span className={`font-medium ${status.profit_endpoint_status.triggered ? 'text-green-600' : 'text-gray-600'}`}>
                    {status.profit_endpoint_status.triggered ? '已触发' : '未触发'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 配置模态框 - 与之前相同,这里省略以节省空间 */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full m-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-6">
              配置资金管理 - {selectedAccount?.name}
            </h2>
            <form onSubmit={handleSaveConfig} className="space-y-6">
              {/* 复利配置 */}
              <div className="border-b pb-4">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <ArrowTrendingUpIcon className="h-5 w-5 mr-2 text-green-600" />
                  复利系统
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">复利模式</label>
                    <select
                      value={configForm.compounding_mode}
                      onChange={(e) => setConfigForm({...configForm, compounding_mode: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    >
                      <option value="stage">阶段复利</option>
                      <option value="perpetual">永续复利</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">复利比例 (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={configForm.compound_ratio}
                      onChange={(e) => setConfigForm({...configForm, compound_ratio: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">初始复利起点 ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={configForm.initial_base}
                      onChange={(e) => setConfigForm({...configForm, initial_base: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">仓位百分比 (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={configForm.position_percent}
                      onChange={(e) => setConfigForm({...configForm, position_percent: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">并发仓位数</label>
                    <input
                      type="number"
                      min="1"
                      value={configForm.concurrent_positions}
                      onChange={(e) => setConfigForm({...configForm, concurrent_positions: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>

              {/* 盈利提取配置 */}
              <div className="border-b pb-4">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <CurrencyDollarIcon className="h-5 w-5 mr-2 text-blue-600" />
                  盈利提取
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">提取模式</label>
                    <select
                      value={configForm.extraction_mode}
                      onChange={(e) => setConfigForm({...configForm, extraction_mode: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    >
                      <option value="wallet_threshold">钱包阈值模式</option>
                      <option value="multiple_mode">倍数模式</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">初始保证金 ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={configForm.initial_margin}
                      onChange={(e) => setConfigForm({...configForm, initial_margin: e.target.value})}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                  {configForm.extraction_mode === 'wallet_threshold' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">提取阈值 ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={configForm.threshold}
                        onChange={(e) => setConfigForm({...configForm, threshold: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                  )}
                  {configForm.extraction_mode === 'multiple_mode' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">提取倍数</label>
                      <input
                        type="number"
                        step="0.1"
                        value={configForm.multiple}
                        onChange={(e) => setConfigForm({...configForm, multiple: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* 初始金额保护配置 */}
              <div className="border-b pb-4">
                <div className="flex items-center mb-4">
                  <input
                    type="checkbox"
                    checked={configForm.protection_enabled}
                    onChange={(e) => setConfigForm({...configForm, protection_enabled: e.target.checked})}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 text-lg font-semibold flex items-center">
                    <ShieldCheckIcon className="h-5 w-5 mr-2 text-yellow-600" />
                    初始金额保护 (可选)
                  </label>
                </div>
                {configForm.protection_enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">初始金额 ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={configForm.protection_initial_amount}
                        onChange={(e) => setConfigForm({...configForm, protection_initial_amount: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">保护倍数</label>
                      <input
                        type="number"
                        step="0.1"
                        value={configForm.protection_multiple}
                        onChange={(e) => setConfigForm({...configForm, protection_multiple: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">最大保护次数</label>
                      <input
                        type="number"
                        min="1"
                        value={configForm.protection_max_count}
                        onChange={(e) => setConfigForm({...configForm, protection_max_count: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">划转步长 ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={configForm.protection_transfer_step}
                        onChange={(e) => setConfigForm({...configForm, protection_transfer_step: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* 盈利倍数终点配置 */}
              <div>
                <div className="flex items-center mb-4">
                  <input
                    type="checkbox"
                    checked={configForm.endpoint_enabled}
                    onChange={(e) => setConfigForm({...configForm, endpoint_enabled: e.target.checked})}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 text-lg font-semibold flex items-center">
                    <FlagIcon className="h-5 w-5 mr-2 text-red-600" />
                    盈利倍数终点 (可选)
                  </label>
                </div>
                {configForm.endpoint_enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">初始金额 ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={configForm.endpoint_initial_amount}
                        onChange={(e) => setConfigForm({...configForm, endpoint_initial_amount: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">终点倍数</label>
                      <input
                        type="number"
                        step="0.1"
                        value={configForm.endpoint_multiple}
                        onChange={(e) => setConfigForm({...configForm, endpoint_multiple: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">划转步长 ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={configForm.endpoint_transfer_step}
                        onChange={(e) => setConfigForm({...configForm, endpoint_transfer_step: e.target.value})}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* 自动补足余额配置 */}
              <div>
                <div className="flex items-center mb-4">
                  <input
                    type="checkbox"
                    checked={configForm.replenish_enabled}
                    onChange={(e) => setConfigForm({...configForm, replenish_enabled: e.target.checked})}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 text-lg font-semibold flex items-center">
                    <ArrowTrendingUpIcon className="h-5 w-5 mr-2 text-green-600" />
                    自动补足余额 (可选)
                  </label>
                </div>
                {configForm.replenish_enabled && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                      <p className="text-sm text-blue-800">
                        <strong>功能说明：</strong>当合约账户总余额低于初始资金时，自动从现货账户转入USDT。<br/>
                        <strong>公式：</strong>B_total &lt; Y_initial 时，补足金额 = Y_initial - B_total
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          初始资金 ($)
                          <span className="text-xs text-gray-500 ml-1">(合约总余额的目标值)</span>
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={configForm.replenish_initial_capital}
                          onChange={(e) => setConfigForm({...configForm, replenish_initial_capital: e.target.value})}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          检查间隔 (秒)
                          <span className="text-xs text-gray-500 ml-1">(多久检查一次余额)</span>
                        </label>
                        <input
                          type="number"
                          value={configForm.replenish_check_interval}
                          onChange={(e) => setConfigForm({...configForm, replenish_check_interval: e.target.value})}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          最小转账金额 ($)
                          <span className="text-xs text-gray-500 ml-1">(低于此值不转账)</span>
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={configForm.replenish_min_amount}
                          onChange={(e) => setConfigForm({...configForm, replenish_min_amount: e.target.value})}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          每日最大补足次数
                          <span className="text-xs text-gray-500 ml-1">(防止频繁转账)</span>
                        </label>
                        <input
                          type="number"
                          value={configForm.replenish_max_per_day}
                          onChange={(e) => setConfigForm({...configForm, replenish_max_per_day: e.target.value})}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          告警阈值 (百分比)
                          <span className="text-xs text-gray-500 ml-1">(余额低于此比例时告警)</span>
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={configForm.replenish_alert_threshold}
                          onChange={(e) => setConfigForm({...configForm, replenish_alert_threshold: e.target.value})}
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        />
                      </div>
                      <div>
                        <label className="flex items-center text-sm font-medium text-gray-700">
                          <input
                            type="checkbox"
                            checked={configForm.replenish_enable_alert}
                            onChange={(e) => setConfigForm({...configForm, replenish_enable_alert: e.target.checked})}
                            className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mr-2"
                          />
                          启用余额不足告警
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 按钮 */}
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  保存配置
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
