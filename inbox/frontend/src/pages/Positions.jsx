import React, { useState, useEffect } from 'react';
import { positionAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Positions() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  // 初始加载持仓
  useEffect(() => {
    loadPositions();
  }, []);

  // WebSocket实时更新
  useWebSocket((message) => {
    if (message.type === 'position_update') {
      // 实时更新持仓数据
      setPositions(prevPositions => {
        const updatedPosition = message.data;
        const index = prevPositions.findIndex(p => p.id === updatedPosition.id);
        if (index >= 0) {
          const newPositions = [...prevPositions];
          newPositions[index] = updatedPosition;
          return newPositions;
        } else {
          return [...prevPositions, updatedPosition];
        }
      });
      console.log('📊 持仓实时更新:', message.data.symbol);
    } else if (message.type === 'step_lock_triggered') {
      // STEP LOCKING触发通知
      console.log('🔒 STEP LOCKING触发:', message.data);
      // 可以显示通知提示
    }
  });

  const loadPositions = async () => {
    try {
      const data = await positionAPI.list({ status: 'open' });
      setPositions(data.items || []);
    } catch (error) {
      console.error('加载持仓失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = async (positionId) => {
    if (!confirm('确定要平仓吗？')) return;
    try {
      await positionAPI.close(positionId);
      await loadPositions();
    } catch (error) {
      alert('平仓失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">加载中...</div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">持仓管理</h2>
        <div className="text-sm text-gray-400">
          实时更新 · 当前持仓: {positions.length}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {positions.length === 0 ? (
          <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-12 text-center">
            <p className="text-gray-400">暂无持仓</p>
          </div>
        ) : (
          positions.map((position) => {
            const pnlPercent = position.entry_price
              ? ((position.current_price - position.entry_price) / position.entry_price) * 100 * (position.side === 'LONG' ? 1 : -1)
              : 0;
            
            return (
              <div key={position.position_id} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-xl font-bold text-white">{position.symbol}</h3>
                      <span className={`px-3 py-1 rounded ${
                        position.side === 'LONG' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {position.side === 'LONG' ? '做多' : '做空'}
                      </span>
                      <span className="text-sm text-gray-400">
                        {position.leverage}x 杠杆
                      </span>
                    </div>

                    <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-xs text-gray-400">数量</div>
                        <div className="text-lg font-medium text-white">{position.quantity}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">进场价</div>
                        <div className="text-lg font-medium text-white">{position.entry_price?.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">当前价</div>
                        <div className="text-lg font-medium text-white">{position.current_price?.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">浮动盈亏</div>
                        <div className={`text-lg font-bold ${
                          position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                        }`}>
                          {position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl?.toFixed(2)} USDT
                          <span className="text-sm ml-2">
                            ({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%)
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-xs text-gray-400">止盈价</div>
                        <div className="text-sm text-green-400">{position.take_profit?.toFixed(2) || '-'}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">止损价</div>
                        <div className="text-sm text-red-400">{position.stop_loss?.toFixed(2) || '-'}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">🔒 Step Lock档位</div>
                        <div className="text-sm text-blue-400">
                          {position.step_lock_level ? `档位${position.step_lock_level}` : '未触发'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400">保证金</div>
                        <div className="text-sm text-white">{position.margin?.toFixed(2)} USDT</div>
                      </div>
                    </div>

                    {position.step_lock_level && (
                      <div className="mt-3 p-3 bg-blue-900 bg-opacity-20 border border-blue-700 rounded">
                        <div className="flex items-center space-x-2">
                          <span className="text-blue-400 text-sm">🔒 STEP LOCKING 已触发</span>
                          <span className="text-white text-sm">
                            档位{position.step_lock_level} - 锁盈止损: {position.step_lock_price?.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="ml-6">
                    <button
                      onClick={() => handleClose(position.position_id)}
                      className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                    >
                      平仓
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
