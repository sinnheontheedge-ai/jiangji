"""
资金引擎插件 - 复利、盈利提取、自动补足
"""
from loguru import logger
from .compounding import CompoundingManager
from .profit_extract import ProfitExtractManager
from .auto_replenish import AutoReplenishManager


class FundEnginePlugin:
    """资金引擎插件"""
    
    def __init__(self, event_bus, config: dict):
        self.event_bus = event_bus
        self.config = config
        
        # 创建复利管理器
        self.compounding_manager = CompoundingManager(event_bus)
        
        # 创建盈利提取管理器
        self.profit_extract_manager = ProfitExtractManager(event_bus)
        
        # 创建自动补足管理器
        self.auto_replenish_manager = AutoReplenishManager(event_bus)
        
        logger.info("✅ 资金引擎插件初始化完成")
    
    async def start(self):
        """启动插件"""
        logger.info("🚀 启动资金引擎插件")
        # 可以在这里启动后台任务
    
    async def stop(self):
        """停止插件"""
        logger.info("🛑 停止资金引擎插件")


def create_plugin(event_bus, config: dict):
    """
    创建资金引擎插件实例
    
    Args:
        event_bus: 事件总线实例
        config: 插件配置
    
    Returns:
        FundEnginePlugin实例
    """
    logger.info("🔌 创建资金引擎插件")
    return FundEnginePlugin(event_bus, config)
