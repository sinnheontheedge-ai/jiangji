import { useState, useEffect } from 'react';
import { systemAPI } from '../services/api';

export default function Settings() {
  const [settings, setSettings] = useState({
    proxy_enabled: false,
    proxy_type: 'http',
    proxy_host: '',
    proxy_port: '',
    proxy_username: '',
    proxy_password: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await systemAPI.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('加载设置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await systemAPI.updateSettings(settings);
      alert('设置保存成功');
    } catch (error) {
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const handleTestProxy = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await systemAPI.testProxy(settings);
      setTestResult({
        success: true,
        message: `连接成功！延迟: ${result.latency}ms`,
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || '连接失败',
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">加载中...</div></div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">系统设置</h2>

      {/* 代理设置 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">代理设置</h3>
          <p className="text-sm text-gray-400 mb-4">
            配置代理服务器以访问币安等交易所（中国大陆用户需要）
          </p>

          <form onSubmit={handleSave} className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.proxy_enabled}
                onChange={(e) => setSettings({ ...settings, proxy_enabled: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
              />
              <label className="ml-2 block text-sm text-gray-300">启用代理</label>
            </div>

            {settings.proxy_enabled && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">代理类型</label>
                    <select
                      value={settings.proxy_type}
                      onChange={(e) => setSettings({ ...settings, proxy_type: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="http">HTTP/HTTPS</option>
                      <option value="socks5">SOCKS5</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">代理主机</label>
                    <input
                      type="text"
                      value={settings.proxy_host}
                      onChange={(e) => setSettings({ ...settings, proxy_host: e.target.value })}
                      placeholder="127.0.0.1"
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                      required={settings.proxy_enabled}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">端口</label>
                    <input
                      type="number"
                      value={settings.proxy_port}
                      onChange={(e) => setSettings({ ...settings, proxy_port: e.target.value })}
                      placeholder="7890"
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                      required={settings.proxy_enabled}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">用户名（可选）</label>
                    <input
                      type="text"
                      value={settings.proxy_username}
                      onChange={(e) => setSettings({ ...settings, proxy_username: e.target.value })}
                      placeholder="留空表示无需认证"
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">密码（可选）</label>
                  <input
                    type="password"
                    value={settings.proxy_password}
                    onChange={(e) => setSettings({ ...settings, proxy_password: e.target.value })}
                    placeholder="留空表示无需认证"
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={handleTestProxy}
                    disabled={testing}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-600"
                  >
                    {testing ? '测试中...' : '测试连接'}
                  </button>
                  {testResult && (
                    <div className={`flex items-center px-4 py-2 rounded-md ${
                      testResult.success ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                    }`}>
                      {testResult.message}
                    </div>
                  )}
                </div>

                <div className="mt-4 p-4 bg-gray-900 rounded-md">
                  <h4 className="text-sm font-medium text-white mb-2">常见VPN代理配置：</h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>• Clash: HTTP代理 127.0.0.1:7890</li>
                    <li>• V2Ray: SOCKS5代理 127.0.0.1:1080</li>
                    <li>• Shadowsocks: SOCKS5代理 127.0.0.1:1080</li>
                    <li>• 确保您的VPN客户端已启动并开启了本地代理端口</li>
                  </ul>
                </div>
              </>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-600"
              >
                {saving ? '保存中...' : '保存设置'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* 系统信息 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">系统信息</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">版本:</span>
              <span className="ml-2 text-white">v1.0.0</span>
            </div>
            <div>
              <span className="text-gray-400">后端:</span>
              <span className="ml-2 text-white">Python 3.11 + FastAPI</span>
            </div>
            <div>
              <span className="text-gray-400">数据库:</span>
              <span className="ml-2 text-white">PostgreSQL + Redis</span>
            </div>
            <div>
              <span className="text-gray-400">架构:</span>
              <span className="ml-2 text-white">事件驱动 + 100%插件化</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
