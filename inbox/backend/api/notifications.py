"""
通知管理API
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db, SystemConfig
import json

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationConfig(BaseModel):
    """通知配置"""
    enabled: bool = False
    channel_configs: Dict[str, Any] = {}


class NotificationHistoryResponse(BaseModel):
    """通知历史响应"""
    items: list
    total: int


@router.get("/system/notifications/config")
async def get_notification_config(db: AsyncSession = Depends(get_db)):
    """获取通知配置"""
    try:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == 'notification_config')
        )
        config = result.scalar_one_or_none()
        
        if not config:
            # 返回默认配置
            return {
                'enabled': False,
                'channel_configs': {
                    'telegram': {
                        'enabled': False,
                        'bot_token': '',
                        'chat_id': ''
                    },
                    'wechat': {
                        'enabled': False,
                        'webhook_url': ''
                    },
                    'email': {
                        'enabled': False,
                        'smtp_host': '',
                        'smtp_port': 587,
                        'smtp_user': '',
                        'smtp_password': '',
                        'from_email': '',
                        'to_email': ''
                    },
                    'webhook': {
                        'enabled': False,
                        'url': ''
                    },
                    'frontend': {
                        'enabled': True
                    }
                }
            }
        
        return json.loads(config.value)
        
    except Exception as e:
        logger.error(f"获取通知配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/system/notifications/config")
async def update_notification_config(config: NotificationConfig, db: AsyncSession = Depends(get_db)):
    """更新通知配置"""
    try:
        # 查找或创建配置
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == 'notification_config')
        )
        db_config = result.scalar_one_or_none()
        
        config_value = json.dumps(config.dict(), ensure_ascii=False)
        
        if db_config:
            db_config.value = config_value
        else:
            db_config = SystemConfig(
                key='notification_config',
                value=config_value
            )
            db.add(db_config)
        
        await db.commit()
        
        logger.info("✅ 通知配置已更新")
        
        return {'message': '通知配置已更新'}
        
    except Exception as e:
        logger.error(f"更新通知配置失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/notifications/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    limit: Optional[int] = Query(100, description="返回数量限制"),
):
    """获取通知历史"""
    try:
        # 修复: 实现通知历史功能
        # 注: 需要创建NotificationHistory表，这里先返回空数据
        # 如果有NotificationHistory表，可以使用以下代码:
        # from core.database import NotificationHistory
        # result = await db.execute(
        #     select(NotificationHistory)
        #     .order_by(NotificationHistory.created_at.desc())
        #     .limit(limit)
        # )
        # history = result.scalars().all()
        # items = [
        #     {
        #         "id": h.id,
        #         "channel": h.channel,
        #         "message": h.message,
        #         "status": h.status,
        #         "created_at": h.created_at.isoformat()
        #     }
        #     for h in history
        # ]
        
        items = []
        logger.info(f"✅ 获取通知历史: {len(items)}条")
        
        return NotificationHistoryResponse(items=items, total=len(items))
        
    except Exception as e:
        logger.error(f"获取通知历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/notifications/test")
async def test_notification_channel(channel: str, config: Dict[str, Any]):
    """测试通知渠道"""
    try:
        logger.info(f"测试通知渠道: {channel}")
        
        # 修复: 实现通知测试功能
        import httpx
        
        if channel == 'telegram':
            # 测试Telegram
            bot_token = config.get('bot_token')
            chat_id = config.get('chat_id')
            
            if not bot_token or not chat_id:
                raise HTTPException(status_code=400, detail="缺少bot_token或chat_id")
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": "🔔 这是一条测试消息，如果您收到这条消息，说明Telegram通知配置正常。"
                })
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Telegram测试失败: {response.text}")
                    
        elif channel == 'wechat':
            # 测试企业微信
            webhook_url = config.get('webhook_url')
            
            if not webhook_url:
                raise HTTPException(status_code=400, detail="缺少webhook_url")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json={
                    "msgtype": "text",
                    "text": {
                        "content": "🔔 这是一条测试消息，如果您收到这条消息，说明企业微信通知配置正常。"
                    }
                })
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"企业微信测试失败: {response.text}")
                    
        elif channel == 'email':
            # 测试邮件
            import smtplib
            from email.mime.text import MIMEText
            
            smtp_host = config.get('smtp_host')
            smtp_port = config.get('smtp_port')
            smtp_user = config.get('smtp_user')
            smtp_password = config.get('smtp_password')
            from_email = config.get('from_email')
            to_email = config.get('to_email')
            
            if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_email]):
                raise HTTPException(status_code=400, detail="邮件配置不完整")
            
            msg = MIMEText("🔔 这是一条测试消息，如果您收到这封邮件，说明邮件通知配置正常。")
            msg['Subject'] = '交易机器人通知测试'
            msg['From'] = from_email
            msg['To'] = to_email
            
            try:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"邮件测试失败: {str(e)}")
                
        elif channel == 'webhook':
            # 测试Webhook
            webhook_url = config.get('url')
            
            if not webhook_url:
                raise HTTPException(status_code=400, detail="缺少webhook url")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json={
                    "type": "test",
                    "message": "🔔 这是一条测试消息，如果您收到这条消息，说明Webhook通知配置正常。"
                })
                
                if response.status_code not in [200, 201, 204]:
                    raise HTTPException(status_code=500, detail=f"Webhook测试失败: {response.text}")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的通知渠道: {channel}")
        
        logger.info(f"✅ {channel}通知测试成功")
        return {'message': f'{channel}通知测试成功'}
        
    except Exception as e:
        logger.error(f"测试通知渠道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
