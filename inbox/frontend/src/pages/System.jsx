import { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowPathIcon, CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function System() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadSystemData();
    // 每30秒自动刷新
    const interval = setInterval(loadSystemData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSystemData = async () => {
    try {
      const [healthRes, statsRes] = await Promise.all([
        axios.get('/api/v1/system/health'),
        axios.get('/api/v1/system/stats')
      ]);
      setHealth(healthRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('加载系统数据失败:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadSystemData();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return <CheckCircleIcon className="h-6 w-6" style={{ color: 'var(--color-accent-success)' }} />;
      case 'degraded':
      case 'warning':
        return <ExclamationTriangleIcon className="h-6 w-6" style={{ color: 'var(--color-accent-warning)' }} />;
      case 'unhealthy':
      case 'error':
        return <XCircleIcon className="h-6 w-6" style={{ color: 'var(--color-accent-error)' }} />;
      default:
        return <ExclamationTriangleIcon className="h-6 w-6" style={{ color: 'var(--color-text-tertiary)' }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'var(--color-accent-success)';
      case 'degraded':
      case 'warning':
        return 'var(--color-accent-warning)';
      case 'unhealthy':
      case 'error':
        return 'var(--color-accent-error)';
      default:
        return 'var(--color-text-tertiary)';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2" style={{ color: 'var(--color-text-tertiary)' }} />
          <p style={{ color: 'var(--color-text-secondary)' }}>加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>系统监控</h1>
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
          {refreshing ? '刷新中...' : '刷新数据'}
        </button>
      </div>

      {/* 系统健康状态 */}
      {health && (
        <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>系统健康状态</h2>
            <div className="flex items-center gap-2">
              {getStatusIcon(health.status)}
              <span className="text-lg font-semibold" style={{ color: getStatusColor(health.status) }}>
                {health.status === 'healthy' ? '健康' : health.status === 'degraded' ? '降级' : '异常'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 数据库状态 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>数据库</span>
                {getStatusIcon(health.database)}
              </div>
              <div className="text-lg font-semibold" style={{ color: getStatusColor(health.database) }}>
                {health.database === 'ok' ? '正常' : '异常'}
              </div>
            </div>

            {/* WebSocket状态 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>WebSocket</span>
                {getStatusIcon(health.websocket || 'ok')}
              </div>
              <div className="text-lg font-semibold" style={{ color: getStatusColor(health.websocket || 'ok') }}>
                {health.websocket === 'ok' ? '正常' : '异常'}
              </div>
            </div>

            {/* API状态 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>API服务</span>
                {getStatusIcon('ok')}
              </div>
              <div className="text-lg font-semibold" style={{ color: getStatusColor('ok') }}>
                正常
              </div>
            </div>

            {/* 系统时间 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>系统时间</span>
              </div>
              <div className="text-sm font-mono" style={{ color: 'var(--color-text-primary)' }}>
                {health.timestamp ? new Date(health.timestamp).toLocaleString('zh-CN') : '--'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 系统统计数据 */}
      {stats && (
        <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <h2 className="text-xl font-bold mb-6" style={{ color: 'var(--color-text-primary)' }}>系统统计</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 账户数量 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>账户总数</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-primary)' }}>
                {stats.accounts || 0}
              </div>
            </div>

            {/* 策略数量 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>策略总数</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-info)' }}>
                {stats.strategies || 0}
              </div>
            </div>

            {/* 实例数量 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>实例总数</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-success)' }}>
                {stats.instances?.total || 0}
              </div>
              <div className="mt-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                运行中: {stats.instances?.running || 0} / 已停止: {stats.instances?.stopped || 0}
              </div>
            </div>

            {/* 订单数量 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>订单总数</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-warning)' }}>
                {stats.orders?.total || 0}
              </div>
              <div className="mt-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                今日: {stats.orders?.today || 0}
              </div>
            </div>

            {/* 持仓数量 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>当前持仓</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-success)' }}>
                {stats.positions?.open || 0}
              </div>
            </div>

            {/* 总盈亏 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>总盈亏 (USDT)</div>
              <div 
                className="text-3xl font-bold font-mono"
                style={{ 
                  color: (stats.profit?.total || 0) >= 0 
                    ? 'var(--color-accent-success)' 
                    : 'var(--color-accent-error)' 
                }}
              >
                {(stats.profit?.total || 0) >= 0 ? '+' : ''}{(stats.profit?.total || 0).toFixed(2)}
              </div>
              <div className="mt-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                今日: {(stats.profit?.today || 0) >= 0 ? '+' : ''}{(stats.profit?.today || 0).toFixed(2)}
              </div>
            </div>

            {/* 胜率 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>胜率</div>
              <div className="text-3xl font-bold" style={{ color: 'var(--color-accent-primary)' }}>
                {stats.winRate ? `${(stats.winRate * 100).toFixed(1)}%` : '--'}
              </div>
            </div>

            {/* 系统运行时间 */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
              <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>系统运行时间</div>
              <div className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {stats.uptime || '--'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 版本信息 */}
      <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
        <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>版本信息</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>系统版本</div>
            <div className="text-lg font-semibold mt-1" style={{ color: 'var(--color-text-primary)' }}>v6.0</div>
          </div>
          <div>
            <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>后端版本</div>
            <div className="text-lg font-semibold mt-1" style={{ color: 'var(--color-text-primary)' }}>
              {stats?.version || 'v6.0'}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>前端版本</div>
            <div className="text-lg font-semibold mt-1" style={{ color: 'var(--color-text-primary)' }}>v6.0</div>
          </div>
        </div>
      </div>
    </div>
  );
}
