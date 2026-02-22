"""
插件加载器 - 动态加载和管理插件
"""
import os
import json
import importlib.util
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginLoader:
    """插件加载器"""
    
    def __init__(self, plugins_dir: str = "/app/plugins"):
        """
        初始化插件加载器
        
        参数:
        - plugins_dir: 插件目录路径
        """
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, Any] = {}
        
        logger.info(f"插件加载器初始化: {plugins_dir}")
    
    def discover_plugins(self) -> List[str]:
        """
        发现所有可用插件
        
        返回: 插件名称列表
        """
        plugins = []
        
        if not self.plugins_dir.exists():
            logger.warning(f"插件目录不存在: {self.plugins_dir}")
            return plugins
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                # 检查是否包含plugin.json
                plugin_json = item / "plugin.json"
                if plugin_json.exists():
                    plugins.append(item.name)
        
        logger.info(f"发现插件: {plugins}")
        return plugins
    
    def load_plugin(self, plugin_name: str, event_bus, config: Dict = None) -> Any:
        """
        加载插件
        
        参数:
        - plugin_name: 插件名称
        - event_bus: 事件总线实例
        - config: 插件配置
        
        返回: 插件实例
        """
        try:
            plugin_dir = self.plugins_dir / plugin_name
            
            # 读取插件元数据
            plugin_json = plugin_dir / "plugin.json"
            with open(plugin_json, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"加载插件: {plugin_name} v{metadata['version']}")
            
            # 加载插件模块
            plugin_file = plugin_dir / "plugin.py"
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}",
                plugin_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 创建插件实例
            if hasattr(module, 'create_plugin'):
                plugin_config = config or {}
                plugin_instance = module.create_plugin(event_bus, plugin_config)
                
                # 保存插件实例
                self.loaded_plugins[plugin_name] = {
                    'instance': plugin_instance,
                    'metadata': metadata,
                    'config': plugin_config
                }
                
                logger.info(f"✅ 插件加载成功: {plugin_name}")
                return plugin_instance
            else:
                raise ValueError(f"插件{plugin_name}缺少create_plugin函数")
                
        except Exception as e:
            logger.error(f"加载插件失败: {plugin_name} - {e}")
            raise
    
    def load_all_plugins(self, event_bus, configs: Dict[str, Dict] = None) -> Dict[str, Any]:
        """
        加载所有插件
        
        参数:
        - event_bus: 事件总线实例
        - configs: 插件配置字典 {plugin_name: config}
        
        返回: 插件实例字典 {plugin_name: instance}
        """
        configs = configs or {}
        plugin_names = self.discover_plugins()
        
        plugins = {}
        for name in plugin_names:
            try:
                config = configs.get(name, {})
                plugin = self.load_plugin(name, event_bus, config)
                plugins[name] = plugin
            except Exception as e:
                logger.error(f"加载插件失败: {name} - {e}")
        
        logger.info(f"✅ 已加载{len(plugins)}个插件")
        return plugins
    
    async def start_all_plugins(self):
        """启动所有插件"""
        logger.info("启动所有插件...")
        
        for name, plugin_data in self.loaded_plugins.items():
            try:
                plugin = plugin_data['instance']
                if hasattr(plugin, 'start'):
                    await plugin.start()
                    logger.info(f"✅ 插件已启动: {name}")
            except Exception as e:
                logger.error(f"启动插件失败: {name} - {e}")
    
    async def stop_all_plugins(self):
        """停止所有插件"""
        logger.info("停止所有插件...")
        
        for name, plugin_data in self.loaded_plugins.items():
            try:
                plugin = plugin_data['instance']
                if hasattr(plugin, 'stop'):
                    await plugin.stop()
                    logger.info(f"✅ 插件已停止: {name}")
            except Exception as e:
                logger.error(f"停止插件失败: {name} - {e}")
    
    def get_plugin(self, plugin_name: str) -> Any:
        """获取插件实例"""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]['instance']
        return None
    
    def get_plugin_metadata(self, plugin_name: str) -> Dict:
        """获取插件元数据"""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]['metadata']
        return None


# 全局插件加载器实例
_plugin_loader = None


def get_plugin_loader() -> PluginLoader:
    """获取全局插件加载器实例"""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader
