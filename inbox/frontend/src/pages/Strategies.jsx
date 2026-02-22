import { useState, useEffect } from 'react';
import { strategyAPI } from '../services/api';
import { ArrowUpTrayIcon, TrashIcon, DocumentTextIcon, EyeIcon, PencilIcon } from '@heroicons/react/24/outline';

export default function Strategies() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [viewingStrategy, setViewingStrategy] = useState(null);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [editCode, setEditCode] = useState('');

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      const data = await strategyAPI.list();
      setStrategies(data.items || []);
    } catch (error) {
      console.error('加载策略列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    if (!file.name.endsWith('.py')) {
      setUploadError('只能上传Python文件(.py)');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      await strategyAPI.upload(file);
      await loadStrategies();
      event.target.value = ''; // 清空文件输入
    } catch (error) {
      setUploadError(error.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (strategyId) => {
    if (!confirm('确定要删除这个策略吗？')) return;

    try {
      await strategyAPI.delete(strategyId);
      await loadStrategies();
    } catch (error) {
      alert('删除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleViewDetails = async (strategyId) => {
    try {
      const data = await strategyAPI.get(strategyId);
      setViewingStrategy(data);
    } catch (error) {
      alert('获取策略详情失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleEdit = async (strategyId) => {
    try {
      const data = await strategyAPI.get(strategyId);
      setEditingStrategy(data);
      setEditCode(data.code || '');
    } catch (error) {
      alert('获取策略代码失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleSaveEdit = async () => {
    if (!editingStrategy) return;

    try {
      await strategyAPI.update(editingStrategy.id, {
        name: editingStrategy.name,
        description: editingStrategy.description,
        code: editCode
      });
      await loadStrategies();
      setEditingStrategy(null);
      setEditCode('');
      alert('保存成功！');
    } catch (error) {
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 上传区域 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">上传策略文件</h3>
          
          <div className="flex items-center space-x-4">
            <label className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer">
              <ArrowUpTrayIcon className="h-5 w-5 mr-2" />
              {uploading ? '上传中...' : '选择文件'}
              <input
                type="file"
                accept=".py"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
            
            <span className="text-sm text-gray-400">
              支持Python策略文件(.py)，必须继承BaseStrategy类
            </span>
          </div>

          {uploadError && (
            <div className="mt-4 p-3 bg-red-900 border border-red-700 rounded-md">
              <p className="text-sm text-red-300">{uploadError}</p>
            </div>
          )}

          <div className="mt-4 p-4 bg-gray-900 rounded-md">
            <h4 className="text-sm font-medium text-white mb-2">策略文件要求：</h4>
            <ul className="text-sm text-gray-400 space-y-1 list-disc list-inside">
              <li>必须继承自 <code className="text-blue-400">BaseStrategy</code> 类</li>
              <li>必须实现 <code className="text-blue-400">on_kline()</code> 方法（计算指标、设置TRIGGER）</li>
              <li>必须实现 <code className="text-blue-400">on_tick()</code> 方法（检查TRIGGER、返回信号）</li>
              <li>文件名将作为策略名称（如 ma_cross_long.py → ma_cross_long）</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 策略列表 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">
            已上传策略 ({strategies.length})
          </h3>

          {strategies.length === 0 ? (
            <div className="text-center py-12">
              <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-600" />
              <p className="mt-2 text-sm text-gray-400">还没有上传任何策略</p>
              <p className="text-xs text-gray-500 mt-1">点击上方按钮上传您的第一个策略</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {strategies.map((strategy) => (
                <div
                  key={strategy.strategy_id}
                  className="bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="text-base font-medium text-white">{strategy.name}</h4>
                      <p className="mt-1 text-sm text-gray-400 line-clamp-2">
                        {strategy.description || '暂无描述'}
                      </p>
                    </div>
                    <div className="ml-2 flex gap-1">
                      <button
                        onClick={() => handleViewDetails(strategy.strategy_id)}
                        className="p-1 text-gray-400 hover:text-blue-500 transition-colors"
                        title="查看详情"
                      >
                        <EyeIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleEdit(strategy.strategy_id)}
                        className="p-1 text-gray-400 hover:text-green-500 transition-colors"
                        title="编辑策略"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(strategy.strategy_id)}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                        title="删除策略"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                    <span>文件: {strategy.file_name}</span>
                    <span>{new Date(strategy.created_at).toLocaleDateString('zh-CN')}</span>
                  </div>

                  {strategy.parameters && Object.keys(strategy.parameters).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <p className="text-xs text-gray-500 mb-2">参数:</p>
                      <div className="space-y-1">
                        {Object.entries(strategy.parameters).slice(0, 3).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-400">{key}:</span>
                            <span className="text-gray-300">{JSON.stringify(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 示例策略代码 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">策略示例代码</h3>
          
          <pre className="bg-gray-900 rounded-md p-4 overflow-x-auto text-sm">
            <code className="text-gray-300">{`from core.strategy_base import BaseStrategy, Signal

class MACrossStrategy(BaseStrategy):
    """均线金叉策略示例"""
    
    def __init__(self, config):
        super().__init__(config)
        self.fast_period = config.get('fast_period', 10)
        self.slow_period = config.get('slow_period', 20)
        self.trigger_active = False
    
    def on_kline(self, kline):
        """计算指标，检测事件，设置TRIGGER"""
        # 计算快慢均线
        fast_ma = self.calculate_ma(self.fast_period)
        slow_ma = self.calculate_ma(self.slow_period)
        
        # 检测金叉事件
        if fast_ma > slow_ma and not self.trigger_active:
            self.trigger_active = True  # 设置TRIGGER
            self.logger.info(f"金叉信号: fast={fast_ma}, slow={slow_ma}")
    
    def on_tick(self, tick):
        """检查TRIGGER，瞬间响应价格变化"""
        if self.trigger_active:
            # TRIGGER激活，立即返回进场信号
            self.trigger_active = False  # 重置TRIGGER
            return Signal(
                action='OPEN',
                side='LONG',
                reason='MA金叉'
            )
        return None
`}</code>
          </pre>
        </div>
      </div>

      {/* 查看详情模态框 */}
      {viewingStrategy && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setViewingStrategy(null)}>
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">策略详情</h3>
              <button onClick={() => setViewingStrategy(null)} className="text-gray-400 hover:text-white">×</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300">策略名称</label>
                <p className="mt-1 text-white">{viewingStrategy.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">描述</label>
                <p className="mt-1 text-gray-400">{viewingStrategy.description || '无'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">文件名</label>
                <p className="mt-1 text-gray-400">{viewingStrategy.file_name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">创建时间</label>
                <p className="mt-1 text-gray-400">{new Date(viewingStrategy.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">策略代码</label>
                <pre className="mt-1 bg-gray-900 rounded p-4 overflow-x-auto text-sm text-gray-300">
                  <code>{viewingStrategy.code}</code>
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 编辑模态框 */}
      {editingStrategy && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setEditingStrategy(null)}>
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">编辑策略</h3>
              <button onClick={() => setEditingStrategy(null)} className="text-gray-400 hover:text-white">×</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300">策略名称</label>
                <input
                  type="text"
                  value={editingStrategy.name}
                  onChange={(e) => setEditingStrategy({...editingStrategy, name: e.target.value})}
                  className="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">描述</label>
                <input
                  type="text"
                  value={editingStrategy.description || ''}
                  onChange={(e) => setEditingStrategy({...editingStrategy, description: e.target.value})}
                  className="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">策略代码</label>
                <textarea
                  value={editCode}
                  onChange={(e) => setEditCode(e.target.value)}
                  rows={20}
                  className="mt-1 block w-full rounded-md bg-gray-900 border-gray-600 text-gray-300 px-3 py-2 font-mono text-sm"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setEditingStrategy(null)}
                  className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600"
                >
                  取消
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
