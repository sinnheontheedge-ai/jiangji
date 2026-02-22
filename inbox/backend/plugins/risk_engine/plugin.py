"""
风控引擎插件 - TP/SL管理和Step Lock
"""
from loguru import logger
from .tpsl_manager import TPSLManager


class RiskEnginePlugin:
    """风控引擎插件"""
    
    def __init__(self, event_bus, config: dict):
        self.event_bus = event_bus
        self.config = config
        
        # 创建TP/SL管理器
        self.tpsl_manager = TPSLManager(event_bus)
        
        logger.info("✅ 风控引擎插件初始化完成")
    
    async def start(self):
        """启动插件"""
        logger.info("🚀 启动风控引擎插件")
        # 订阅价格更新事件
        self.event_bus.subscribe("price:update", self.tpsl_manager.on_price_update)
    
    async def stop(self):
        """停止插件"""
        logger.info("🛑 停止风控引擎插件")


def create_plugin(event_bus, config: dict):
    """
    创建风控引擎插件实例
    
    Args:
        event_bus: 事件总线实例
        config: 插件配置
    
    Returns:
        RiskEnginePlugin实例
    """
    logger.info("🔌 创建风控引擎插件")
    return RiskEnginePlugin(event_bus, config)
