import { useState, useEffect } from 'react';
import { systemAPI } from '../services/api';

export default function Notifications() {
  const [config, setConfig] = useState({
    enabled_channels: [],
    channel_configs: {
      telegram: { enabled: false, bot_token: '', chat_id: '' },
      wechat: { enabled: false, webhook_url: '' },
      email: { enabled: false, smtp_server: '', smtp_port: 587, username: '', password: '', to_email: '' },
      webhook: { enabled: false, url: '' },
      frontend: { enabled: true }
    }
  });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingChannel, setTestingChannel] = useState(null);

  useEffect(() => {
    loadConfig();
    loadHistory();
    const interval = setInterval(loadHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadConfig = async () => {
    try {
      const data = await systemAPI.getNotificationConfig();
      if (data) {
        setConfig(data);
      }
    } catch (error) {
      console.error('加载通知配置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await systemAPI.getNotificationHistory();
      setHistory(data.items || []);
    } catch (error) {
      console.error('加载通知历史失败:', error);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      // 更新enabled_channels列表
      const enabledChannels = Object.keys(config.channel_configs).filter(
        channel => config.channel_configs[channel].enabled
      );
      const updatedConfig = { ...config, enabled_channels: enabledChannels };
      
      await systemAPI.updateNotificationConfig(updatedConfig);
      setConfig(updatedConfig);
      alert('通知配置保存成功');
    } catch (error) {
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const handleTestChannel = async (channel) => {
    setTestingChannel(channel);
    try {
      await systemAPI.testNotificationChannel(channel, config.channel_configs[channel]);
      alert(`${channel} 测试成功！`);
    } catch (error) {
      alert(`${channel} 测试失败: ` + (error.response?.data?.detail || error.message));
    } finally {
      setTestingChannel(null);
    }
  };

  const updateChannelConfig = (channel, field, value) => {
    setConfig({
      ...config,
      channel_configs: {
        ...config.channel_configs,
        [channel]: {
          ...config.channel_configs[channel],
          [field]: value
        }
      }
    });
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">加载中...</div></div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">通知配置</h2>
      
      <div className="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-4">
        <div className="flex items-start">
          <span className="text-2xl mr-3">🔔</span>
          <div>
            <h3 className="text-blue-300 font-medium">信号触发通知</h3>
            <p className="text-sm text-gray-400 mt-1">
              当策略生成做多/做空信号时，系统会立即通过您启用的渠道发送通知，包含交易对、信号方向、当前价格、策略名称和触发时间。
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Telegram */}
        <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config.channel_configs.telegram.enabled}
                onChange={(e) => updateChannelConfig('telegram', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
              />
              <label className="ml-2 text-lg font-medium text-white">Telegram</label>
            </div>
            {config.channel_configs.telegram.enabled && (
              <button
                type="button"
                onClick={() => handleTestChannel('telegram')}
                disabled={testingChannel === 'telegram'}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:bg-gray-600"
              >
                {testingChannel === 'telegram' ? '测试中...' : '测试'}
              </button>
            )}
          </div>

          {config.channel_configs.telegram.enabled && (
            <div className="space-y-3 ml-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Bot Token</label>
                <input
                  type="text"
                  value={config.channel_configs.telegram.bot_token}
                  onChange={(e) => updateChannelConfig('telegram', 'bot_token', e.target.value)}
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Chat ID</label>
                <input
                  type="text"
                  value={config.channel_configs.telegram.chat_id}
                  onChange={(e) => updateChannelConfig('telegram', 'chat_id', e.target.value)}
                  placeholder="123456789"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <p className="text-xs text-gray-400">
                1. 在Telegram中搜索 @BotFather 创建机器人获取Token<br/>
                2. 在Telegram中搜索 @userinfobot 获取您的Chat ID
              </p>
            </div>
          )}
        </div>

        {/* 企业微信 */}
        <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config.channel_configs.wechat.enabled}
                onChange={(e) => updateChannelConfig('wechat', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
              />
              <label className="ml-2 text-lg font-medium text-white">企业微信</label>
            </div>
            {config.channel_configs.wechat.enabled && (
              <button
                type="button"
                onClick={() => handleTestChannel('wechat')}
                disabled={testingChannel === 'wechat'}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:bg-gray-600"
              >
                {testingChannel === 'wechat' ? '测试中...' : '测试'}
              </button>
            )}
          </div>

          {config.channel_configs.wechat.enabled && (
            <div className="space-y-3 ml-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Webhook URL</label>
                <input
                  type="url"
                  value={config.channel_configs.wechat.webhook_url}
                  onChange={(e) => updateChannelConfig('wechat', 'webhook_url', e.target.value)}
                  placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <p className="text-xs text-gray-400">
                在企业微信群聊中添加机器人，获取Webhook地址
              </p>
            </div>
          )}
        </div>

        {/* 邮件 */}
        <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config.channel_configs.email.enabled}
                onChange={(e) => updateChannelConfig('email', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
              />
              <label className="ml-2 text-lg font-medium text-white">邮件</label>
            </div>
            {config.channel_configs.email.enabled && (
              <button
                type="button"
                onClick={() => handleTestChannel('email')}
                disabled={testingChannel === 'email'}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:bg-gray-600"
              >
                {testingChannel === 'email' ? '测试中...' : '测试'}
              </button>
            )}
          </div>

          {config.channel_configs.email.enabled && (
            <div className="space-y-3 ml-6">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">SMTP服务器</label>
                  <input
                    type="text"
                    value={config.channel_configs.email.smtp_server}
                    onChange={(e) => updateChannelConfig('email', 'smtp_server', e.target.value)}
                    placeholder="smtp.gmail.com"
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">端口</label>
                  <input
                    type="number"
                    value={config.channel_configs.email.smtp_port}
                    onChange={(e) => updateChannelConfig('email', 'smtp_port', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">发件邮箱</label>
                <input
                  type="email"
                  value={config.channel_configs.email.username}
                  onChange={(e) => updateChannelConfig('email', 'username', e.target.value)}
                  placeholder="your@email.com"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">密码/授权码</label>
                <input
                  type="password"
                  value={config.channel_configs.email.password}
                  onChange={(e) => updateChannelConfig('email', 'password', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">收件邮箱</label>
                <input
                  type="email"
                  value={config.channel_configs.email.to_email}
                  onChange={(e) => updateChannelConfig('email', 'to_email', e.target.value)}
                  placeholder="recipient@email.com"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
            </div>
          )}
        </div>

        {/* Webhook */}
        <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config.channel_configs.webhook.enabled}
                onChange={(e) => updateChannelConfig('webhook', 'enabled', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
              />
              <label className="ml-2 text-lg font-medium text-white">Webhook</label>
            </div>
            {config.channel_configs.webhook.enabled && (
              <button
                type="button"
                onClick={() => handleTestChannel('webhook')}
                disabled={testingChannel === 'webhook'}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:bg-gray-600"
              >
                {testingChannel === 'webhook' ? '测试中...' : '测试'}
              </button>
            )}
          </div>

          {config.channel_configs.webhook.enabled && (
            <div className="space-y-3 ml-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Webhook URL</label>
                <input
                  type="url"
                  value={config.channel_configs.webhook.url}
                  onChange={(e) => updateChannelConfig('webhook', 'url', e.target.value)}
                  placeholder="https://your-server.com/webhook"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <p className="text-xs text-gray-400">
                系统会将通知数据以JSON格式POST到此URL
              </p>
            </div>
          )}
        </div>

        {/* 前端弹窗 */}
        <div className="bg-gray-800 shadow rounded-lg border border-gray-700 p-6">
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={config.channel_configs.frontend.enabled}
              onChange={(e) => updateChannelConfig('frontend', 'enabled', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded"
            />
            <label className="ml-2 text-lg font-medium text-white">前端实时弹窗</label>
          </div>
          <p className="text-sm text-gray-400 mt-2 ml-6">
            在浏览器中实时显示通知弹窗（推荐始终启用）
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-600"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </form>

      {/* 通知历史 */}
      <div className="bg-gray-800 shadow rounded-lg border border-gray-700">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">通知历史</h3>
          
          {history.length === 0 ? (
            <p className="text-gray-400 text-center py-8">暂无通知记录</p>
          ) : (
            <div className="space-y-3">
              {history.map((notif, index) => (
                <div key={index} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">🔔</span>
                        <span className="font-medium text-white">{notif.symbol}</span>
                        <span className={`px-2 py-1 rounded text-sm ${
                          notif.direction === 'LONG' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                        }`}>
                          {notif.direction_text}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-gray-400 space-y-1">
                        <div>策略: {notif.strategy_name}</div>
                        <div>价格: {notif.price}</div>
                        <div>时间: {notif.timestamp}</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
