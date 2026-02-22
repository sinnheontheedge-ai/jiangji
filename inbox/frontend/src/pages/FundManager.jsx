import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  CurrencyDollarIcon, 
  ArrowTrendingUpIcon, 
  ShieldCheckIcon,
  FlagIcon,
  Cog6ToothIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function FundManager() {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [fundConfig, setFundConfig] = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  
  // 配置表单状态
  const [configForm, setConfigForm] = useState({
    // 全局配置
    initial_capital: 1000,
    
    // 复利配置
    compounding_mode: 'stage',
    compound_ratio: 20,
    current_base: 1000,
    
    // 盈利提取配置（单选模式）
    extraction_mode: 'wallet_threshold', // 'wallet_threshold' 或 'multiple_mode'
    threshold: 2000,      // 钱包阈值模式使用
    multiple: 2.0,        // 倍数模式使用
    
    // 初始金额保护
    enable_initial_protect: false,
    protect_multiplier: 2.0,
    max_protect_count: 1,
    protect_count: 0,             // 已触发次数（只读）
    last_protect_balance: 0,      // 上次保护后余额（只读）
    
    // 盈利倍数终点
    enable_endpoint: false,
    endpoint_multiplier: 10.0,
    endpoint_count: 0,            // 已触发次数（只读）
    
    // 自动补足余额
    enable_replenish: false,
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
      loadFundConfig();
    }
  }, [selectedAccountId]);

  const loadAccounts = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/accounts`);
      setAccounts(response.data);
      
      // 默认选择第一个账户
      if (response.data.length > 0 && !selectedAccountId) {
        setSelectedAccountId(response.data[0].id);
      }
    } catch (error) {
      console.error('加载账户列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFundConfig = async () => {
    if (!selectedAccountId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/fund-manager/config/${selectedAccountId}`);
      const config = response.data;
      setFundConfig(config);
      
      // 填充配置表单
      setConfigForm({
        initial_capital: config.initial_capital || 1000,
        compounding_mode: config.compounding_mode || 'stage',
        compound_ratio: config.compound_ratio || 20,
        current_base: config.current_base || 1000,
        extraction_mode: config.extraction_mode || 'wallet_threshold',
        threshold: config.threshold || 2000,
        multiple: config.multiple || 2.0,
        enable_initial_protect: config.enable_initial_protect || false,
        protect_multiplier: config.protect_multiplier || 2.0,
        max_protect_count: config.max_protect_count || 1,
        protect_count: config.protect_count || 0,
        last_protect_balance: config.last_protect_balance || 0,
        enable_endpoint: config.enable_endpoint || false,
        endpoint_multiplier: config.endpoint_multiplier || 10.0,
        endpoint_count: config.endpoint_count || 0,
        enable_replenish: config.enable_replenish || false,
        replenish_min_amount: config.replenish_min_amount || 10,
        replenish_enable_alert: config.replenish_enable_alert !== false,
        replenish_alert_threshold: config.replenish_alert_threshold || 0.8,
        replenish_max_per_day: config.replenish_max_per_day || 10
      });
      
    } catch (error) {
      if (error.response?.status === 404) {
        // 未配置，使用默认值
        setFundConfig(null);
      } else {
        console.error('加载资金管理配置失败:', error);
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
      const payload = {
        account_id: selectedAccountId,
        initial_capital: parseFloat(configForm.initial_capital),
        compounding_mode: configForm.compounding_mode,
        compound_ratio: parseFloat(configForm.compound_ratio),
        current_base: parseFloat(configForm.current_base),
        extraction_mode: configForm.extraction_mode,
        threshold: configForm.extraction_mode === 'wallet_threshold' ? parseFloat(configForm.threshold) : null,
        multiple: configForm.extraction_mode === 'multiple_mode' ? parseFloat(configForm.multiple) : null,
        enable_initial_protect: configForm.enable_initial_protect,
        protect_multiplier: parseFloat(configForm.protect_multiplier),
        max_protect_count: parseInt(configForm.max_protect_count),
        enable_endpoint: configForm.enable_endpoint,
        endpoint_multiplier: parseFloat(configForm.endpoint_multiplier),
        enable_replenish: configForm.enable_replenish,
        replenish_min_amount: parseFloat(configForm.replenish_min_amount),
        replenish_enable_alert: configForm.replenish_enable_alert,
        replenish_alert_threshold: parseFloat(configForm.replenish_alert_threshold),
        replenish_max_per_day: parseInt(configForm.replenish_max_per_day)
      };
      
      if (fundConfig) {
        // 更新现有配置
        await axios.put(`${API_BASE_URL}/api/fund-manager/config/${selectedAccountId}`, payload);
      } else {
        // 创建新配置
        await axios.post(`${API_BASE_URL}/api/fund-manager/config`, payload);
      }
      
      alert('配置保存成功');
      setShowConfigModal(false);
      loadFundConfig();
      
    } catch (error) {
      console.error('保存配置失败:', error);
      alert('保存配置失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg" style={{ color: 'var(--color-text-primary)' }}>加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
          资金管理
        </h1>
        <button
          onClick={() => setShowConfigModal(true)}
          className="px-4 py-2 rounded-lg flex items-center gap-2"
          style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}
        >
          <Cog6ToothIcon className="h-5 w-5" />
          配置资金管理
        </button>
      </div>

      {/* 账户选择 */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
          选择账户
        </label>
        <select
          value={selectedAccountId || ''}
          onChange={(e) => setSelectedAccountId(parseInt(e.target.value))}
          className="w-full px-4 py-2 rounded-lg border"
          style={{ 
            backgroundColor: 'var(--color-bg-secondary)', 
            borderColor: 'var(--color-border-primary)',
            color: 'var(--color-text-primary)'
          }}
        >
          <option value="">请选择账户</option>
          {accounts.map(account => (
            <option key={account.id} value={account.id}>
              {account.name} ({account.exchange})
            </option>
          ))}
        </select>
      </div>

      {/* 配置状态卡片 */}
      {fundConfig ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* 全局初始投入金额 */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
            <div className="flex items-center gap-2 mb-2">
              <CurrencyDollarIcon className="h-5 w-5" style={{ color: 'var(--color-accent-primary)' }} />
              <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>初始投入金额</h3>
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
              ${fundConfig.initial_capital}
            </p>
          </div>

          {/* 复利模式 */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
            <div className="flex items-center gap-2 mb-2">
              <ArrowTrendingUpIcon className="h-5 w-5" style={{ color: 'var(--color-accent-success)' }} />
              <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>复利模式</h3>
            </div>
            <p className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
              {fundConfig.compounding_mode === 'stage' ? '阶段复利' : '永续复利'}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              比例: {fundConfig.compound_ratio}%
            </p>
          </div>

          {/* 初始金额保护 */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheckIcon className="h-5 w-5" style={{ color: 'var(--color-accent-warning)' }} />
              <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>初始金额保护</h3>
            </div>
            <p className="text-lg font-bold" style={{ color: fundConfig.enable_initial_protect ? 'var(--color-accent-success)' : 'var(--color-text-secondary)' }}>
              {fundConfig.enable_initial_protect ? '已启用' : '未启用'}
            </p>
            {fundConfig.enable_initial_protect && (
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                已触发: {fundConfig.protect_count}/{fundConfig.max_protect_count} 次
              </p>
            )}
          </div>

          {/* 盈利倍数终点 */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
            <div className="flex items-center gap-2 mb-2">
              <FlagIcon className="h-5 w-5" style={{ color: 'var(--color-accent-error)' }} />
              <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>盈利倍数终点</h3>
            </div>
            <p className="text-lg font-bold" style={{ color: fundConfig.enable_endpoint ? 'var(--color-accent-success)' : 'var(--color-text-secondary)' }}>
              {fundConfig.enable_endpoint ? '已启用' : '未启用'}
            </p>
            {fundConfig.enable_endpoint && (
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                已触发: {fundConfig.endpoint_count} 次
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="p-8 text-center rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
          <p className="text-lg mb-4" style={{ color: 'var(--color-text-secondary)' }}>
            该账户尚未配置资金管理
          </p>
          <button
            onClick={() => setShowConfigModal(true)}
            className="px-6 py-2 rounded-lg"
            style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}
          >
            立即配置
          </button>
        </div>
      )}

      {/* 配置模态框 */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
            <form onSubmit={handleSaveConfig}>
              {/* 模态框标题 */}
              <div className="sticky top-0 px-6 py-4 border-b flex items-center justify-between" style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)' }}>
                <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                  资金管理配置
                </h2>
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="text-2xl"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  ×
                </button>
              </div>

              <div className="p-6 space-y-6">
                {/* 全局初始投入金额 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <CurrencyDollarIcon className="h-6 w-6" style={{ color: 'var(--color-accent-primary)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      全局初始投入金额
                    </h3>
                    <div className="group relative">
                      <InformationCircleIcon className="h-5 w-5 cursor-help" style={{ color: 'var(--color-text-secondary)' }} />
                      <div className="absolute left-0 top-6 w-64 p-2 rounded shadow-lg hidden group-hover:block z-10" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                        <p className="text-xs" style={{ color: 'var(--color-text-primary)' }}>
                          所有资金管理功能的基准金额，包括：<br/>
                          • 复利系统的起点<br/>
                          • 盈利提取后保留的金额<br/>
                          • 初始金额保护每次转移的金额<br/>
                          • 盈利倍数终点的计算基准<br/>
                          • 自动补足余额的最低资金水平
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                      初始投入金额 (USDT) *
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={configForm.initial_capital}
                      onChange={(e) => setConfigForm({ ...configForm, initial_capital: e.target.value })}
                      className="w-full px-4 py-2 rounded-lg border"
                      style={{ 
                        backgroundColor: 'var(--color-bg-primary)', 
                        borderColor: 'var(--color-border-primary)',
                        color: 'var(--color-text-primary)'
                      }}
                      placeholder="例如: 1000"
                    />
                    <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                      这是所有资金管理功能的基准金额，请谨慎设置
                    </p>
                  </div>
                </div>

                {/* 复利配置 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <ArrowTrendingUpIcon className="h-6 w-6" style={{ color: 'var(--color-accent-success)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      复利系统
                    </h3>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        复利模式 *
                      </label>
                      <select
                        value={configForm.compounding_mode}
                        onChange={(e) => setConfigForm({ ...configForm, compounding_mode: e.target.value })}
                        className="w-full px-4 py-2 rounded-lg border"
                        style={{ 
                          backgroundColor: 'var(--color-bg-primary)', 
                          borderColor: 'var(--color-border-primary)',
                          color: 'var(--color-text-primary)'
                        }}
                      >
                        <option value="stage">阶段复利</option>
                        <option value="perpetual">永续复利</option>
                      </select>
                      <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                        阶段复利: 每个阶段内交易资金固定，达到门槛后进入下一阶段<br/>
                        永续复利: 每笔交易都用当前全部余额，所有盈利立即加入下一笔
                      </p>
                    </div>

                    {configForm.compounding_mode === 'stage' && (
                      <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                          复利比例 (%) *
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          required
                          value={configForm.compound_ratio}
                          onChange={(e) => setConfigForm({ ...configForm, compound_ratio: e.target.value })}
                          className="w-full px-4 py-2 rounded-lg border"
                          style={{ 
                            backgroundColor: 'var(--color-bg-primary)', 
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-primary)'
                          }}
                          placeholder="例如: 20"
                        />
                        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                          每个阶段的增长幅度，例如20%表示从$100增长到$120
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 盈利提取配置 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <CurrencyDollarIcon className="h-6 w-6" style={{ color: 'var(--color-accent-primary)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      盈利提取
                    </h3>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                        提取模式 *
                      </label>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 p-3 rounded-lg border cursor-pointer" style={{ 
                          backgroundColor: configForm.extraction_mode === 'wallet_threshold' ? 'var(--color-interactive-hover)' : 'transparent',
                          borderColor: 'var(--color-border-primary)'
                        }}>
                          <input
                            type="radio"
                            name="extraction_mode"
                            value="wallet_threshold"
                            checked={configForm.extraction_mode === 'wallet_threshold'}
                            onChange={(e) => setConfigForm({ ...configForm, extraction_mode: e.target.value })}
                          />
                          <div>
                            <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>钱包阈值模式</p>
                            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>当钱包余额达到设定阈值时，提取超出初始投入金额的部分</p>
                          </div>
                        </label>
                        
                        <label className="flex items-center gap-2 p-3 rounded-lg border cursor-pointer" style={{ 
                          backgroundColor: configForm.extraction_mode === 'multiple_mode' ? 'var(--color-interactive-hover)' : 'transparent',
                          borderColor: 'var(--color-border-primary)'
                        }}>
                          <input
                            type="radio"
                            name="extraction_mode"
                            value="multiple_mode"
                            checked={configForm.extraction_mode === 'multiple_mode'}
                            onChange={(e) => setConfigForm({ ...configForm, extraction_mode: e.target.value })}
                          />
                          <div>
                            <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>倍数模式</p>
                            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>当钱包余额达到初始投入金额的N倍时，提取超出初始投入金额的部分</p>
                          </div>
                        </label>
                      </div>
                    </div>

                    {configForm.extraction_mode === 'wallet_threshold' && (
                      <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                          钱包阈值 (USDT) *
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          required
                          value={configForm.threshold}
                          onChange={(e) => setConfigForm({ ...configForm, threshold: e.target.value })}
                          className="w-full px-4 py-2 rounded-lg border"
                          style={{ 
                            backgroundColor: 'var(--color-bg-primary)', 
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-primary)'
                          }}
                          placeholder="例如: 2000"
                        />
                      </div>
                    )}

                    {configForm.extraction_mode === 'multiple_mode' && (
                      <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                          提取倍数 *
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          required
                          value={configForm.multiple}
                          onChange={(e) => setConfigForm({ ...configForm, multiple: e.target.value })}
                          className="w-full px-4 py-2 rounded-lg border"
                          style={{ 
                            backgroundColor: 'var(--color-bg-primary)', 
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-primary)'
                          }}
                          placeholder="例如: 2.0"
                        />
                        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                          例如设置为2.0，当余额达到初始投入金额的2倍时触发提取
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 初始金额保护配置 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <ShieldCheckIcon className="h-6 w-6" style={{ color: 'var(--color-accent-warning)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      初始金额保护
                    </h3>
                    <div className="group relative">
                      <InformationCircleIcon className="h-5 w-5 cursor-help" style={{ color: 'var(--color-text-secondary)' }} />
                      <div className="absolute left-0 top-6 w-64 p-2 rounded shadow-lg hidden group-hover:block z-10" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                        <p className="text-xs" style={{ color: 'var(--color-text-primary)' }}>
                          当账户余额达到触发点时，自动转移固定金额（初始投入金额）到现货账户，保护本金安全。<br/><br/>
                          第1次触发点 = 初始投入金额 × 保护倍数<br/>
                          第N次触发点 = 上次保护后的余额 + 初始投入金额
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enable_initial_protect"
                        checked={configForm.enable_initial_protect}
                        onChange={(e) => setConfigForm({ ...configForm, enable_initial_protect: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="enable_initial_protect" className="text-sm font-medium cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                        启用初始金额保护
                      </label>
                    </div>

                    {configForm.enable_initial_protect && (
                      <>
                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            保护倍数 *
                          </label>
                          <input
                            type="number"
                            step="0.1"
                            required
                            value={configForm.protect_multiplier}
                            onChange={(e) => setConfigForm({ ...configForm, protect_multiplier: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 2.0"
                          />
                          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                            第1次触发点 = 初始投入金额 × 保护倍数
                          </p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            最大保护次数 *
                          </label>
                          <input
                            type="number"
                            step="1"
                            required
                            value={configForm.max_protect_count}
                            onChange={(e) => setConfigForm({ ...configForm, max_protect_count: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 1"
                          />
                          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                            达到最大次数后自动禁用保护功能
                          </p>
                        </div>

                        {fundConfig && (
                          <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
                            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                              已触发次数: {configForm.protect_count}/{configForm.max_protect_count}
                            </p>
                            {configForm.last_protect_balance > 0 && (
                              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                                上次保护后余额: ${configForm.last_protect_balance.toFixed(2)}
                              </p>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* 盈利倍数终点配置 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <FlagIcon className="h-6 w-6" style={{ color: 'var(--color-accent-error)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      盈利倍数终点
                    </h3>
                    <div className="group relative">
                      <InformationCircleIcon className="h-5 w-5 cursor-help" style={{ color: 'var(--color-text-secondary)' }} />
                      <div className="absolute left-0 top-6 w-64 p-2 rounded shadow-lg hidden group-hover:block z-10" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                        <p className="text-xs" style={{ color: 'var(--color-text-primary)' }}>
                          当账户余额达到初始投入金额的N倍时，自动提取全部盈利（保留初始投入金额），然后继续交易（不停止实例）。<br/><br/>
                          触发点 = 初始投入金额 × 终点倍数<br/>
                          提取金额 = 当前余额 - 初始投入金额
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enable_endpoint"
                        checked={configForm.enable_endpoint}
                        onChange={(e) => setConfigForm({ ...configForm, enable_endpoint: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="enable_endpoint" className="text-sm font-medium cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                        启用盈利倍数终点
                      </label>
                    </div>

                    {configForm.enable_endpoint && (
                      <>
                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            终点倍数 *
                          </label>
                          <input
                            type="number"
                            step="0.1"
                            required
                            value={configForm.endpoint_multiplier}
                            onChange={(e) => setConfigForm({ ...configForm, endpoint_multiplier: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 10.0"
                          />
                          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                            当余额达到初始投入金额的N倍时触发提取，然后继续交易
                          </p>
                        </div>

                        {fundConfig && configForm.endpoint_count > 0 && (
                          <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
                            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                              已触发次数: {configForm.endpoint_count}
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* 自动补足余额配置 */}
                <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border-primary)' }}>
                  <div className="flex items-center gap-2 mb-4">
                    <ArrowTrendingUpIcon className="h-6 w-6" style={{ color: 'var(--color-accent-success)' }} />
                    <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      自动补足余额
                    </h3>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enable_replenish"
                        checked={configForm.enable_replenish}
                        onChange={(e) => setConfigForm({ ...configForm, enable_replenish: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="enable_replenish" className="text-sm font-medium cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                        启用自动补足余额
                      </label>
                    </div>

                    {configForm.enable_replenish && (
                      <>
                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            最小转账金额 (USDT) *
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            required
                            value={configForm.replenish_min_amount}
                            onChange={(e) => setConfigForm({ ...configForm, replenish_min_amount: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 10"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            预警阈值 (%) *
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            required
                            value={configForm.replenish_alert_threshold * 100}
                            onChange={(e) => setConfigForm({ ...configForm, replenish_alert_threshold: parseFloat(e.target.value) / 100 })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 80"
                          />
                          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                            当余额低于初始投入金额的N%时触发补足
                          </p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                            每日最大补足次数 *
                          </label>
                          <input
                            type="number"
                            step="1"
                            required
                            value={configForm.replenish_max_per_day}
                            onChange={(e) => setConfigForm({ ...configForm, replenish_max_per_day: e.target.value })}
                            className="w-full px-4 py-2 rounded-lg border"
                            style={{ 
                              backgroundColor: 'var(--color-bg-primary)', 
                              borderColor: 'var(--color-border-primary)',
                              color: 'var(--color-text-primary)'
                            }}
                            placeholder="例如: 10"
                          />
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="replenish_enable_alert"
                            checked={configForm.replenish_enable_alert}
                            onChange={(e) => setConfigForm({ ...configForm, replenish_enable_alert: e.target.checked })}
                            className="rounded"
                          />
                          <label htmlFor="replenish_enable_alert" className="text-sm font-medium cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                            启用余额不足预警
                          </label>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* 模态框底部按钮 */}
              <div className="sticky bottom-0 px-6 py-4 border-t flex justify-end gap-3" style={{ backgroundColor: 'var(--color-bg-primary)', borderColor: 'var(--color-border-primary)' }}>
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="px-6 py-2 rounded-lg"
                  style={{ backgroundColor: 'var(--color-border-secondary)', color: 'var(--color-text-primary)' }}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 rounded-lg"
                  style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-inverse)' }}
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
