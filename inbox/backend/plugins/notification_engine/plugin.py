"""
通知引擎插件 - 多渠道通知
"""
from loguru import logger
from .notifier import Notifier


def create_plugin(event_bus, config: dict):
    """
    创建通知引擎插件实例
    
    Args:
        event_bus: 事件总线实例
        config: 插件配置
    
    Returns:
        Notifier实例
    """
    logger.info("🔌 创建通知引擎插件")
    
    # 创建通知器实例
    notifier = Notifier(event_bus, config)
    
    logger.info("✅ 通知引擎插件创建成功")
    return notifier
