"""
事件总线 - 系统的中央神经系统
所有模块通过事件总线进行通信，实现100%解耦
"""
import asyncio
import json
import os
from typing import Callable, Dict, List, Any
from loguru import logger
import redis.asyncio as aioredis


class EventBus:
    """事件总线单例"""
    
    _instance = None
    
    def __init__(self):
        self.redis_client: aioredis.Redis = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        
    @classmethod
    def get_instance(cls):
        """获取事件总线单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def start(self):
        """启动事件总线"""
        try:
            # 连接Redis - 从环境变量读取
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            logger.info(f"🔌 连接Redis: {redis_url}")
            
            self.redis_client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            self.running = True
            
            # 启动监听任务
            asyncio.create_task(self._listen())
            
            logger.info("✅ 事件总线已启动")
        except Exception as e:
            logger.error(f"❌ 事件总线启动失败: {e}")
            raise
    
    async def stop(self):
        """停止事件总线"""
        self.running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("👋 事件总线已停止")
    
    async def publish(self, channel: str, data: Dict[str, Any]):
        """
        发布事件
        
        Args:
            channel: 事件频道，如 "market_data:kline:BTCUSDT:15m"
            data: 事件数据
        """
        try:
            message = json.dumps(data)
            await self.redis_client.publish(channel, message)
            logger.debug(f"📤 发布事件: {channel}")
        except Exception as e:
            logger.error(f"❌ 发布事件失败 [{channel}]: {e}")
    
    async def subscribe(self, pattern: str, callback: Callable):
        """
        订阅事件
        
        Args:
            pattern: 事件模式，如 "market_data:*" 或 "signal:*"
            callback: 回调函数，接收 (channel, data) 参数
        """
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
            # 订阅Redis频道
            await self.pubsub.psubscribe(pattern)
            logger.info(f"📥 订阅事件模式: {pattern}")
        
        self.subscribers[pattern].append(callback)
    
    async def _listen(self):
        """监听事件（后台任务）"""
        logger.info("👂 开始监听事件...")
        
        while self.running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message['type'] == 'pmessage':
                    channel = message['channel']
                    pattern = message['pattern']
                    data_str = message['data']
                    
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ 无法解析事件数据: {data_str}")
                        continue
                    
                    # 调用所有订阅该模式的回调函数
                    if pattern in self.subscribers:
                        for callback in self.subscribers[pattern]:
                            try:
                                # 异步调用回调
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(channel, data)
                                else:
                                    callback(channel, data)
                            except Exception as e:
                                logger.error(f"❌ 事件回调执行失败 [{channel}]: {e}")
                
                await asyncio.sleep(0.01)  # 避免CPU占用过高
                
            except Exception as e:
                logger.error(f"❌ 事件监听异常: {e}")
                # P0修复: Redis断开后尝试重连
                if "Connection" in str(e) or "Timeout" in str(e):
                    logger.warning("⚠️ Redis连接断开，尝试重连...")
                    try:
                        await self.start()  # 重新连接
                        logger.info("✅ Redis重连成功")
                    except Exception as reconnect_error:
                        logger.error(f"❌ Redis重连失败: {reconnect_error}")
                await asyncio.sleep(1)  # 发生错误时等待1秒再重试
