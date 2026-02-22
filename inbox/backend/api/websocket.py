"""
WebSocket API端点 - 实时数据推送
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点 - 实时推送数据到前端
    
    推送的消息类型:
    - position_update: 持仓更新（含STEP LOCKING状态）
    - order_update: 订单更新
    - notification: 通知消息
    - step_lock_triggered: STEP LOCKING档位触发
    - balance_update: 账户余额更新
    """
    ws_manager = get_websocket_manager()
    
    # 建立连接
    await ws_manager.connect(websocket)
    
    try:
        # 保持连接，接收客户端消息（如心跳）
        while True:
            data = await websocket.receive_text()
            logger.debug(f"收到WebSocket消息: {data}")
            
            # 处理ping/pong心跳
            try:
                import json
                message = json.loads(data)
                if message.get('type') == 'ping':
                    # 响应pong
                    await websocket.send_text(json.dumps({'type': 'pong'}))
                    logger.debug("🏓 响应pong")
                    continue
            except json.JSONDecodeError:
                pass
            
            # 可以处理客户端发送的消息（如订阅特定数据）
            # 目前只是保持连接
            
    except WebSocketDisconnect:
        logger.info("WebSocket客户端主动断开连接")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        ws_manager.disconnect(websocket)
