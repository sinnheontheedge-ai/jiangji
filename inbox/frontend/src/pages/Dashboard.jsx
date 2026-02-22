import React, { useState, useEffect } from 'react';
import { systemAPI, positionAPI, orderAPI } from '../services/api';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_accounts: 0,
    active_instances: 0,
    open_positions: 0,
    total_pnl: 0,
    today_pnl: 0,
    win_rate: 0,
  });
  const [positions, setPositions] = useState([]);
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // 初始加载数据
  useEffect(() => {
    loadDashboardData();
  }, []);

  // WebSocket实时更新
  useWebSocket((message) => {
    if (message.type === 'position_update' || message.type === 'order_update' || message.type === 'balance_update') {
      // 实时更新仪表盘数据
      loadDashboardData();
    }
  });

  const loadDashboardData = async () => {
    try {
      const [statsData, positionsData, ordersData] = await Promise.all([
        systemAPI.stats(),
        positionAPI.list({ status: 'open' }),
        orderAPI.list({ limit: 10 }),
      ]);
      
      // 🔧 修复: 适配后端返回的数据格式,并提供默认值
      setStats({
        total_accounts: statsData?.accounts || 0,           // 后端字段: accounts
        active_instances: statsData?.active_instances || 0, // 后端字段: active_instances
        open_positions: statsData?.positions || 0,          // 后端字段: positions
        total_pnl: statsData?.total_pnl || 0,              // 后端字段: total_pnl
        today_pnl: statsData?.today_pnl || 0,              // 后端可能没有此字段,默认0
        win_rate: statsData?.win_rate || 0,                // 后端可能没有此字段,默认0
      });
      
      setPositions(positionsData?.items || []);
      setRecentOrders(ordersData?.items || []);
    } catch (error) {
      console.error('加载仪表盘数据失败:', error);
      // 🔧 修复: 即使失败也设置默认值,避免undefined错误
      setStats({
        total_accounts: 0,
        active_instances: 0,
        open_positions: 0,
        total_pnl: 0,
        today_pnl: 0,
        win_rate: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  // 🔧 修复: 添加安全的数字格式化函数
  const formatNumber = (value, decimals = 2) => {
    const num = parseFloat(value);
    return isNaN(num) ? '0.00' : num.toFixed(decimals);
  };

  const statCards = [
    {
      name: '账户总数',
      value: stats.total_accounts || 0,
      icon: '👥',
      color: 'bg-blue-500',
    },
    {
      name: '运行实例',
      value: stats.active_instances || 0,
      icon: '⚙️',
      color: 'bg-green-500',
    },
    {
      name: '持仓数量',
      value: stats.open_positions || 0,
      icon: '📊',
      color: 'bg-purple-500',
    },
    {
      name: '总盈亏',
      // 🔧 修复: 使用安全的格式化函数
      value: `${(stats.total_pnl || 0) >= 0 ? '+' : ''}${formatNumber(stats.total_pnl)} USDT`,
      icon: (stats.total_pnl || 0) >= 0 ? '📈' : '📉',
      color: (stats.total_pnl || 0) >= 0 ? 'bg-green-500' : 'bg-red-500',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <div
            key={card.name}
            className="bg-gray-800 overflow-hidden shadow rounded-lg border border-gray-700"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className={`flex-shrink-0 ${card.color} rounded-md p-3`}>
                  <span className="text-2xl">{card.icon}</span>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-400 truncate">{card.name}</dt>
                    <dd className="text-lg font-semibold text-white">{card.value}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 今日盈亏 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">今日盈亏</h3>
          <div className="flex items-center">
            <span
              className={`text-3xl font-bold ${
                (stats.today_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'
              }`}
            >
              {/* 🔧 修复: 使用安全的格式化函数 */}
              {(stats.today_pnl || 0) >= 0 ? '+' : ''}
              {formatNumber(stats.today_pnl)} USDT
            </span>
            {(stats.today_pnl || 0) >= 0 ? (
              <ArrowUpIcon className="ml-2 h-6 w-6 text-green-500" />
            ) : (
              <ArrowDownIcon className="ml-2 h-6 w-6 text-red-500" />
            )}
            <span className="ml-4 text-sm text-gray-400">
              {/* 🔧 修复: 使用安全的格式化函数 */}
              胜率: {formatNumber((stats.win_rate || 0) * 100, 1)}%
            </span>
          </div>
        </div>
      </div>

      {/* 持仓列表 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">当前持仓</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-700">
              <thead>
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    交易对
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    方向
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    数量
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    进场价
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    当前价
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    盈亏
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    止损价
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-3 py-4 text-center text-sm text-gray-400">
                      暂无持仓
                    </td>
                  </tr>
                ) : (
                  positions.map((position) => (
                    <tr key={position.position_id}>
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-white">
                        {position.symbol}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span
                          className={`px-2 py-1 rounded ${
                            position.side === 'LONG'
                              ? 'bg-green-900 text-green-300'
                              : 'bg-red-900 text-red-300'
                          }`}
                        >
                          {position.side === 'LONG' ? '做多' : '做空'}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {position.quantity}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {/* 🔧 修复: 使用安全的格式化函数 */}
                        {formatNumber(position.entry_price)}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {/* 🔧 修复: 使用安全的格式化函数 */}
                        {formatNumber(position.current_price)}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span
                          className={
                            (position.unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'
                          }
                        >
                          {/* 🔧 修复: 使用安全的格式化函数 */}
                          {(position.unrealized_pnl || 0) >= 0 ? '+' : ''}
                          {formatNumber(position.unrealized_pnl)}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {/* 🔧 修复: 使用安全的格式化函数 */}
                        {formatNumber(position.stop_loss)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 最近订单 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">最近订单</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-700">
              <thead>
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    时间
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    交易对
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    方向
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    数量
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    价格
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    状态
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {recentOrders.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-3 py-4 text-center text-sm text-gray-400">
                      暂无订单
                    </td>
                  </tr>
                ) : (
                  recentOrders.map((order) => (
                    <tr key={order.order_id}>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {new Date(order.created_at).toLocaleString('zh-CN')}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-white">
                        {order.symbol}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span
                          className={`px-2 py-1 rounded ${
                            order.side === 'BUY'
                              ? 'bg-green-900 text-green-300'
                              : 'bg-red-900 text-red-300'
                          }`}
                        >
                          {order.side === 'BUY' ? '买入' : '卖出'}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {order.order_type}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {order.quantity}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-300">
                        {/* 🔧 修复: 使用安全的格式化函数,或显示"市价" */}
                        {order.price ? formatNumber(order.price) : '市价'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span
                          className={`px-2 py-1 rounded ${
                            order.status === 'FILLED'
                              ? 'bg-green-900 text-green-300'
                              : order.status === 'CANCELLED'
                              ? 'bg-gray-700 text-gray-300'
                              : 'bg-yellow-900 text-yellow-300'
                          }`}
                        >
                          {order.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
