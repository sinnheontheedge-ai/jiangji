import React, { useState, useEffect } from 'react';
import { orderAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ status: 'all', symbol: '' });

  useEffect(() => {
    loadOrders();
  }, [filter]);

  // WebSocket实时更新订单
  useWebSocket((message) => {
    if (message.type === 'order_update') {
      setOrders(prevOrders => {
        const updatedOrder = message.data;
        const index = prevOrders.findIndex(o => o.id === updatedOrder.id);
        if (index >= 0) {
          const newOrders = [...prevOrders];
          newOrders[index] = updatedOrder;
          return newOrders;
        } else {
          return [updatedOrder, ...prevOrders];
        }
      });
      console.log('📝 订单实时更新:', message.data.order_id);
    }
  });

  const loadOrders = async () => {
    try {
      const params = {};
      if (filter.status !== 'all') params.status = filter.status;
      if (filter.symbol) params.symbol = filter.symbol;
      
      const data = await orderAPI.list(params);
      setOrders(data.items || []);
    } catch (error) {
      console.error('加载订单失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (orderId) => {
    if (!confirm('确定要取消这个订单吗？')) return;
    try {
      await orderAPI.cancel(orderId);
      await loadOrders();
    } catch (error) {
      alert('取消失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">加载中...</div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">订单记录</h2>
        <div className="flex space-x-3">
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">全部状态</option>
            <option value="PENDING">待成交</option>
            <option value="FILLED">已成交</option>
            <option value="CANCELLED">已取消</option>
          </select>
          <input
            type="text"
            placeholder="搜索交易对..."
            value={filter.symbol}
            onChange={(e) => setFilter({ ...filter, symbol: e.target.value })}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <div className="bg-gray-800 shadow rounded-lg border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">交易对</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">方向</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">类型</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">数量</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">价格</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">成交均价</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">手续费</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">状态</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {orders.length === 0 ? (
                <tr>
                  <td colSpan="10" className="px-4 py-8 text-center text-sm text-gray-400">
                    暂无订单记录
                  </td>
                </tr>
              ) : (
                orders.map((order) => (
                  <tr key={order.order_id} className="hover:bg-gray-750">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">
                      {new Date(order.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-white">
                      {order.symbol}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded ${
                        order.side === 'BUY' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {order.side === 'BUY' ? '买入' : '卖出'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{order.order_type}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{order.quantity}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">
                      {order.price ? order.price.toFixed(2) : '市价'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">
                      {order.avg_price ? order.avg_price.toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">
                      {order.fee ? order.fee.toFixed(4) : '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded ${
                        order.status === 'FILLED' ? 'bg-green-900 text-green-300' :
                        order.status === 'CANCELLED' ? 'bg-gray-700 text-gray-300' :
                        'bg-yellow-900 text-yellow-300'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {order.status === 'PENDING' && (
                        <button
                          onClick={() => handleCancel(order.order_id)}
                          className="text-red-400 hover:text-red-300"
                        >
                          取消
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
