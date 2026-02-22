"""
WebSocket管理器 - 实时推送数据到前端
"""
import asyncio
import logging
import json
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.active_connections: Set[WebSocket] = set()
        self._running = False
        
        logger.info("WebSocket管理器初始化完成")
    
    async def start(self):
        """启动WebSocket管理器，订阅所有需要推送的事件"""
        self._running = True
        
        # P0修复: 订阅所有需要推送到前端的事件
        await self.event_bus.subscribe("position.updated", self._on_position_updated)
        await self.event_bus.subscribe("order.updated", self._on_order_updated)
        await self.event_bus.subscribe("order.created", self._on_order_created)
        await self.event_bus.subscribe("order.filled", self._on_order_filled)
        await self.event_bus.subscribe("notification.frontend", self._on_notification)
        await self.event_bus.subscribe("step_lock.triggered", self._on_step_lock_triggered)
        await self.event_bus.subscribe("risk:step_lock:triggered", self._on_step_lock_triggered)
        await self.event_bus.subscribe("account.balance_updated", self._on_balance_updated)
        await self.event_bus.subscribe("trade:rejected", self._on_trade_rejected)
        await self.event_bus.subscribe("instance.status_changed", self._on_instance_status_changed)
        
        logger.info("✅ WebSocket管理器已启动，监听10个实时事件频道")
    
    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
        
        # 发送欢迎消息
        await self._send_to_client(websocket, {
            'type': 'connected',
            'message': '实时数据推送已连接'
        })
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def _on_position_updated(self, channel: str, event_data: Dict[str, Any]):
        """持仓更新事件 - 推送到所有客户端"""
        message = {
            'type': 'position_update',
            'data': event_data
        }
        await self.broadcast(message)
        logger.debug(f"📤 推送持仓更新: {event_data.get('symbol')}")
    
    async def _on_order_updated(self, channel: str, event_data: Dict[str, Any]):
        """订单更新事件 - 推送到所有客户端"""
        message = {
            'type': 'order_update',
            'data': event_data
        }
        await self.broadcast(message)
        logger.debug(f"📤 推送订单更新: {event_data.get('order_id')}")
    
    async def _on_notification(self, channel: str, event_data: Dict[str, Any]):
        """通知事件 - 推送到所有客户端"""
        message = {
            'type': 'notification',
            'data': event_data
        }
        await self.broadcast(message)
        logger.info(f"🔔 推送通知: {event_data.get('title')}")
    
    async def _on_step_lock_triggered(self, channel: str, event_data: Dict[str, Any]):
        """STEP LOCKING触发事件 - 推送到所有客户端"""
        message = {
            'type': 'step_lock_triggered',
            'data': event_data
        }
        await self.broadcast(message)
        logger.info(f"🔒 推送STEP LOCKING触发: {event_data.get('symbol')} 档位{event_data.get('level')}")
    
    async def _on_balance_updated(self, channel: str, event_data: Dict[str, Any]):
        """账户余额更新事件 - 推送到所有客户端"""
        message = {
            'type': 'balance_update',
            'data': event_data
        }
        await self.broadcast(message)
        logger.debug(f"📤 推送余额更新: {event_data.get('account_id')}")
    
    async def _on_order_created(self, channel: str, event_data: Dict[str, Any]):
        """订单创建事件 - 推送到所有客户端"""
        message = {
            'type': 'order_created',
            'data': event_data
        }
        await self.broadcast(message)
        logger.debug(f"📤 推送订单创建: {event_data.get('order_id')}")
    
    async def _on_order_filled(self, channel: str, event_data: Dict[str, Any]):
        """订单成交事件 - 推送到所有客户端"""
        message = {
            'type': 'order_filled',
            'data': event_data
        }
        await self.broadcast(message)
        logger.debug(f"📤 推送订单成交: {event_data.get('order_id')}")
    
    async def _on_trade_rejected(self, channel: str, event_data: Dict[str, Any]):
        """交易拒绝事件 - 推送到所有客户端"""
        message = {
            'type': 'trade_rejected',
            'data': event_data
        }
        await self.broadcast(message)
        logger.info(f"⚠️ 推送交易拒绝: {event_data.get('reason')}")
    
    async def _on_instance_status_changed(self, channel: str, event_data: Dict[str, Any]):
        """实例状态变化事件 - 推送到所有客户端"""
        message = {
            'type': 'instance_status_changed',
            'data': event_data
        }
        await self.broadcast(message)
        logger.info(f"📤 推送实例状态变化: instance_id={event_data.get('instance_id')}, status={event_data.get('status')}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接的客户端"""
        if not self.active_connections:
            return
        
        # 序列化消息
        message_json = json.dumps(message, ensure_ascii=False)
        
        # 发送到所有客户端
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"❌ 发送WebSocket消息失败: {e}")
                disconnected.add(connection)
        
        # 移除断开的连接
        for connection in disconnected:
            self.disconnect(connection)
    
    async def _send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """发送消息到特定客户端"""
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"❌ 发送WebSocket消息失败: {e}")
            self.disconnect(websocket)
    
    async def stop(self):
        """停止WebSocket管理器"""
        self._running = False
        
        # 关闭所有连接
        for connection in list(self.active_connections):
            try:
                await connection.close()
            except:
                pass
        
        self.active_connections.clear()
        logger.info("WebSocket管理器已停止")


# 全局WebSocket管理器实例
_ws_manager = None


def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器实例"""
    global _ws_manager
    if _ws_manager is None:
        raise RuntimeError("WebSocket管理器未初始化")
    return _ws_manager


def init_websocket_manager(event_bus) -> WebSocketManager:
    """初始化全局WebSocket管理器"""
    global _ws_manager
    _ws_manager = WebSocketManager(event_bus)
    return _ws_manager
