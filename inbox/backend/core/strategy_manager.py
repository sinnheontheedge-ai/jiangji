"""
策略管理器 - 管理策略实例的生命周期
"""
import asyncio
from typing import Dict, Optional
from loguru import logger

from core.strategy_base import BaseStrategy, Signal
from core.event_bus import EventBus
from core.strategy_loader import strategy_loader


class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        """初始化策略管理器"""
        self.instances: Dict[int, BaseStrategy] = {}  # instance_id -> strategy对象
        self.event_bus = EventBus.get_in    async def start(self):
        """启动策略管理器"""
        # 订阅K线事件
        await self.event_bus.subscribe("market_data:kline:*", self._on_kline_event)
        # 订阅Tick事件
        await self.event_bus.subscribe("market_data:tick:*", self._on_tick_event)
        logger.info("✅ 策略管理器已启动")
        logger.info("✅ Step Lock tick级检查已集成到tick链路")    
    def create_instance(self, instance_id: int, strategy_name: str, config: dict) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            instance_id: 策略实例ID
            strategy_name: 策略类名
            config: 策略配置
        
        Returns:
            策略实例
        """
        try:
            # 获取策略类
            strategy_class = strategy_loader.get_strategy(strategy_name)
            
            # 创建实例
            strategy_instance = strategy_class(config)
            
            # 添加异常隔离包装
            wrapped_instance = self._wrap_with_isolation(instance_id, strategy_instance)
            
            # 保存实例
            self.instances[instance_id] = wrapped_instance
            
            logger.info(f"✅ 创建策略实例: ID={instance_id}, 策略={strategy_name}")
            return wrapped_instance
            
        except Exception as e:
            logger.error(f"❌ 创建策略实例失败: {e}")
            raise
    
    def _wrap_with_isolation(self, instance_id: int, strategy: BaseStrategy) -> BaseStrategy:
        """
        为策略实例添加异常隔离包装
        
        Args:
            instance_id: 实例ID
            strategy: 原始策略实例
        
        Returns:
            包装后的策略实例
        """
        original_on_kline = strategy.on_kline
        original_on_tick = strategy.on_tick
        
        def safe_on_kline(kline):
            try:
                return original_on_kline(kline)
            except Exception as e:
                logger.error(f"❌ 策略实例 {instance_id} on_kline异常: {e}")
                # 发布错误事件
                asyncio.create_task(self.event_bus.publish(
                    f"strategy:error:{instance_id}",
                    {"error": str(e), "method": "on_kline"}
                ))
        
        def safe_on_tick(tick):
            try:
                return original_on_tick(tick)
            except Exception as e:
                logger.error(f"❌ 策略实例 {instance_id} on_tick异常: {e}")
                # 发布错误事件
                asyncio.create_task(self.event_bus.publish(
                    f"strategy:error:{instance_id}",
                    {"error": str(e), "method": "on_tick"}
                ))
                return None
        
        strategy.on_kline = safe_on_kline
        strategy.on_tick = safe_on_tick
        
        return strategy
    
    def remove_instance(self, instance_id: int):
        """
        移除策略实例
        
        Args:
            instance_id: 策略实例ID
        """
        if instance_id in self.instances:
            del self.instances[instance_id]
            logger.info(f"🗑️ 移除策略实例: ID={instance_id}")
    
    async def _on_kline_event(self, channel: str, data: dict):
        """
        处理K线事件
        
        Args:
            channel: 事件频道，如 "market_data:kline:BTCUSDT:15m"
            data: K线数据
        """
        # 解析频道获取交易对和周期
        parts = channel.split(":")
        if len(parts) < 4:
            return
        
        symbol = parts[2]
        timeframe = parts[3]
        
        # 分发给相关的策略实例
        for instance_id, strategy in self.instances.items():
            if strategy.symbol == symbol and strategy.timeframe == timeframe:
                strategy.on_kline(data)
    
    async def _on_tick_event(self, channel: str, data: dict):
        """
        处理Tick事件
        
        Args:
            channel: 事件频道，如 "market_data:tick:BTCUSDT"
            data: Tick数据
        """
        # 解析频道获取交易对
        parts = channel.split(":")
        if len(parts) < 3:
            return
        
        symbol = parts[2        # 分发给相关的策略实例
        for instance_id, strategy in self.instances.items():
            if strategy.symbol == symbol:
                signal = strategy.on_tick(data)
                
                # 如果生成了交易信号，发布到事件总线
                if signal:
                    await self.event_bus.publish(
                        f"signal:trade:{instance_id}",
                        {
                            "instance_id": instance_id,
                            "action": signal.action,
                            "symbol": signal.symbol,
                            "quantity": signal.quantity,
                            "price": signal.price,
                            "reason": signal.reason
                        }
                    )
                    logger.info(f"📊Strategy instance {instance_id} generated trade signal: {signal.action} {signal.symbol}")
        
        # P0修复: Step Lock tick级检查 - 每个tick都要检查所有持仓的Step Lock状态
        current_price = data.get('price')
        if current_price:
            await self.event_bus.publish(
                f"risk:step_lock:tick:{symbol}",
                {
                    "symbol": symbol,
                    "price": current_price,
                    "timestamp": data.get('timestamp')
                }
            )rategy_manager = StrategyManager()
