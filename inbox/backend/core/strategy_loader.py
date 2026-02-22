"""
策略加载器 - 动态加载策略插件（5个耦合点之一：插件加载机制）
"""
import os
import importlib.util
import inspect
from typing import Dict, Type
from pathlib import Path
from loguru import logger

from core.strategy_base import BaseStrategy


class StrategyLoader:
    """策略加载器"""
    
    def __init__(self, strategies_dir: str = "strategies"):
        """
        初始化策略加载器
        
        Args:
            strategies_dir: 策略文件目录
        """
        self.strategies_dir = Path(strategies_dir)
        self.strategies: Dict[str, Type[BaseStrategy]] = {}
    
    def load_all(self):
        """
        自动扫描并加载所有策略
        
        扫描规则：
        1. 扫描strategies目录下的所有.py文件
        2. 查找继承自BaseStrategy的类
        3. 注册到策略字典中
        """
        if not self.strategies_dir.exists():
            logger.warning(f"⚠️ 策略目录不存在: {self.strategies_dir}")
            self.strategies_dir.mkdir(parents=True, exist_ok=True)
            return
        
        logger.info(f"📂 开始扫描策略目录: {self.strategies_dir}")
        
        # 遍历所有.py文件
        for file_path in self.strategies_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue  # 跳过私有文件
            
            try:
                self._load_strategy_file(file_path)
            except Exception as e:
                logger.error(f"❌ 加载策略文件失败 [{file_path.name}]: {e}")
        
        logger.info(f"✅ 策略加载完成，共加载 {len(self.strategies)} 个策略")
        for name in self.strategies.keys():
            logger.info(f"  - {name}")
    
    def _load_strategy_file(self, file_path: Path):
        """
        加载单个策略文件
        
        Args:
            file_path: 策略文件路径
        """
        module_name = file_path.stem
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            logger.warning(f"⚠️ 无法加载模块: {file_path}")
            return
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找继承自BaseStrategy的类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                self.strategies[name] = obj
                logger.info(f"  ✅ 发现策略: {name} (文件: {file_path.name})")
    
    def load_from_code(self, code: str, strategy_name: str) -> Type[BaseStrategy]:
        """
        从代码字符串动态加载策略（用于策略上传功能）
        
        Args:
            code: 策略代码字符串
            strategy_name: 策略名称
        
        Returns:
            策略类
        """
        try:
            # 创建临时模块
            module_name = f"strategy_{strategy_name}"
            module = type(module_name, (), {})
            
            # 执行代码
            exec(code, module.__dict__)
            
            # 查找策略类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                    self.strategies[name] = obj
                    logger.info(f"✅ 动态加载策略: {name}")
                    return obj
            
            raise ValueError("未找到继承自BaseStrategy的策略类")
            
        except Exception as e:
            logger.error(f"❌ 动态加载策略失败: {e}")
            raise
    
    def get_strategy(self, name: str) -> Type[BaseStrategy]:
        """
        获取策略类
        
        Args:
            name: 策略类名
        
        Returns:
            策略类
        """
        if name not in self.strategies:
            raise ValueError(f"策略不存在: {name}")
        return self.strategies[name]
    
    def list_strategies(self) -> list:
        """列出所有已加载的策略"""
        return list(self.strategies.keys())


# 全局策略加载器实例
strategy_loader = StrategyLoader()
