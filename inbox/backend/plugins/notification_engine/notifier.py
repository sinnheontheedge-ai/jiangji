"""
通知引擎 - 信号触发通知
当策略生成做多/做空信号时立即发送通知
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""
    TELEGRAM = "telegram"
    WECHAT = "wechat"
    EMAIL = "email"
    WEBHOOK = "webhook"
    FRONTEND = "frontend"


class SignalNotifier:
    """信号通知器 - 当策略生成信号时发送通知"""
    
    def __init__(self, event_bus, config: Dict[str, Any] = None):
        self.event_bus = event_bus
        self.config = config or {}
        self.enabled_channels = self.config.get('enabled_channels', [])
        self.channel_configs = self.config.get('channel_configs', {})
        
        # 通知历史
        self.notification_history = []
        
        logger.info(f"信号通知器初始化完成，启用渠道: {self.enabled_channels}")
    
    async def start(self):
        """启动通知器，订阅信号事件"""
        await self.event_bus.subscribe("signal.generated", self.on_signal_generated)
        logger.info("信号通知器已启动，监听 signal.generated 事件")
    
    async def on_signal_generated(self, event_data: Dict[str, Any]):
        """
        处理信号生成事件
        
        event_data 包含:
        - symbol: 交易对 (如 BTCUSDT)
        - direction: 信号方向 (LONG/SHORT)
        - price: 当前价格
        - strategy_name: 策略名称
        - timestamp: 触发时间
        - account_id: 账户ID
        """
        try:
            # 构建通知消息
            notification = self._build_notification(event_data)
            
            # 保存到历史记录
            self.notification_history.append(notification)
            if len(self.notification_history) > 1000:
                self.notification_history = self.notification_history[-1000:]
            
            # 发送到所有启用的渠道
            tasks = []
            for channel in self.enabled_channels:
                task = self._send_to_channel(channel, notification)
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"✅ 信号通知已发送: {notification['symbol']} {notification['direction']}")
            
        except Exception as e:
            logger.error(f"❌ 发送信号通知失败: {e}", exc_info=True)
    
    def _build_notification(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建通知消息"""
        direction_text = "做多" if event_data['direction'] == 'LONG' else "做空"
        
        notification = {
            'id': f"signal_{event_data['timestamp']}_{event_data['symbol']}",
            'type': 'signal',
            'symbol': event_data['symbol'],
            'direction': event_data['direction'],
            'direction_text': direction_text,
            'price': event_data['price'],
            'strategy_name': event_data['strategy_name'],
            'timestamp': event_data['timestamp'],
            'account_id': event_data.get('account_id'),
            'created_at': datetime.now().isoformat(),
        }
        
        # 构建文本消息
        notification['title'] = f"🔔 交易信号触发"
        notification['message'] = (
            f"策略: {event_data['strategy_name']}\n"
            f"交易对: {event_data['symbol']}\n"
            f"信号方向: {direction_text}\n"
            f"当前价格: {event_data['price']}\n"
            f"触发时间: {event_data['timestamp']}"
        )
        
        return notification
    
    async def _send_to_channel(self, channel: str, notification: Dict[str, Any]):
        """发送通知到指定渠道"""
        try:
            if channel == NotificationChannel.TELEGRAM:
                await self._send_telegram(notification)
            elif channel == NotificationChannel.WECHAT:
                await self._send_wechat(notification)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(notification)
            elif channel == NotificationChannel.FRONTEND:
                await self._send_frontend(notification)
            else:
                logger.warning(f"未知的通知渠道: {channel}")
        
        except Exception as e:
            logger.error(f"发送到 {channel} 失败: {e}", exc_info=True)
    
    async def _send_telegram(self, notification: Dict[str, Any]):
        """发送Telegram通知"""
        config = self.channel_configs.get('telegram', {})
        if not config.get('enabled'):
            return
        
        bot_token = config.get('bot_token')
        chat_id = config.get('chat_id')
        
        if not bot_token or not chat_id:
            logger.warning("Telegram配置不完整，跳过发送")
            return
        
        try:
            import aiohttp
            
            # 构建Telegram消息
            message = f"<b>{notification['title']}</b>\n\n{notification['message']}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"✅ Telegram通知发送成功")
                    else:
                        logger.error(f"❌ Telegram通知发送失败: {response.status}")
        
        except Exception as e:
            logger.error(f"Telegram通知发送异常: {e}", exc_info=True)
    
    async def _send_wechat(self, notification: Dict[str, Any]):
        """发送企业微信通知"""
        config = self.channel_configs.get('wechat', {})
        if not config.get('enabled'):
            return
        
        webhook_url = config.get('webhook_url')
        
        if not webhook_url:
            logger.warning("企业微信配置不完整，跳过发送")
            return
        
        try:
            import aiohttp
            
            # 构建企业微信消息
            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': f"## {notification['title']}\n\n{notification['message']}"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"✅ 企业微信通知发送成功")
                    else:
                        logger.error(f"❌ 企业微信通知发送失败: {response.status}")
        
        except Exception as e:
            logger.error(f"企业微信通知发送异常: {e}", exc_info=True)
    
    async def _send_email(self, notification: Dict[str, Any]):
        """发送邮件通知"""
        config = self.channel_configs.get('email', {})
        if not config.get('enabled'):
            return
        
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        username = config.get('username')
        password = config.get('password')
        to_email = config.get('to_email')
        
        if not all([smtp_server, username, password, to_email]):
            logger.warning("邮件配置不完整，跳过发送")
            return
        
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = notification['title']
            
            body = notification['message']
            msg.attach(MIMEText(body, 'plain'))
            
            # 发送邮件
            await aiosmtplib.send(
                msg,
                hostname=smtp_server,
                port=smtp_port,
                username=username,
                password=password,
                use_tls=True
            )
            
            logger.info(f"✅ 邮件通知发送成功")
        
        except Exception as e:
            logger.error(f"邮件通知发送异常: {e}", exc_info=True)
    
    async def _send_webhook(self, notification: Dict[str, Any]):
        """发送Webhook通知"""
        config = self.channel_configs.get('webhook', {})
        if not config.get('enabled'):
            return
        
        url = config.get('url')
        
        if not url:
            logger.warning("Webhook配置不完整，跳过发送")
            return
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=notification) as response:
                    if response.status == 200:
                        logger.info(f"✅ Webhook通知发送成功")
                    else:
                        logger.error(f"❌ Webhook通知发送失败: {response.status}")
        
        except Exception as e:
            logger.error(f"Webhook通知发送异常: {e}", exc_info=True)
    
    async def _send_frontend(self, notification: Dict[str, Any]):
        """发送前端通知（通过事件总线）"""
        try:
            await self.event_bus.publish("notification.frontend", notification)
            logger.info(f"✅ 前端通知已发布")
        except Exception as e:
            logger.error(f"前端通知发布异常: {e}", exc_info=True)
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取通知历史"""
        return self.notification_history[-limit:]
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config = config
        self.enabled_channels = config.get('enabled_channels', [])
        self.channel_configs = config.get('channel_configs', {})
        logger.info(f"通知配置已更新，启用渠道: {self.enabled_channels}")


# 测试代码
if __name__ == "__main__":
    import sys
    sys.path.append('/home/ubuntu/trading-bot/backend')
    
    from core.event_bus import EventBus
    
    async def test():
        # 创建事件总线
        event_bus = EventBus()
        await event_bus.start()
        
        # 创建通知器（仅启用日志输出，不启用实际渠道）
        config = {
            'enabled_channels': ['frontend'],
            'channel_configs': {}
        }
        notifier = SignalNotifier(event_bus, config)
        await notifier.start()
        
        # 模拟信号生成事件
        signal_event = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'price': 50000.0,
            'strategy_name': 'MA均线金叉策略',
            'timestamp': datetime.now().isoformat(),
            'account_id': 'account_001'
        }
        
        print("\n🔔 模拟信号触发...")
        await event_bus.publish("signal.generated", signal_event)
        
        # 等待处理
        await asyncio.sleep(1)
        
        # 查看历史
        history = notifier.get_history()
        print(f"\n📋 通知历史记录: {len(history)} 条")
        for notif in history:
            print(f"  - {notif['symbol']} {notif['direction_text']} @ {notif['price']}")
        
        print("\n✅ 测试完成")
    
    asyncio.run(test())
