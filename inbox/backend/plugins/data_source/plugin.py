"""
数据源插件 - 提供市场数据
"""
from loguru import logger
from .market_data import MarketDataSource


def create_plugin(event_bus, config: dict):
    """
    创建数据源插件实例
    
    Args:
        event_bus: 事件总线实例
        config: 插件配置
    
    Returns:
        MarketDataSource实例
    """
    logger.info("🔌 创建数据源插件")
    
    # 创建市场数据源实例
    market_data = MarketDataSource(event_bus)
    
    logger.info("✅ 数据源插件创建成功")
    return market_data
