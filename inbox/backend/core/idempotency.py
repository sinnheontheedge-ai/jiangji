"""
幂等性保证中间件

功能:
1. 基于幂等键（Idempotency-Key）识别重复请求
2. 缓存请求结果，重复请求返回相同响应
3. 防止网络重试导致的重复操作
4. 支持请求去重和结果缓存
5. 自动清理过期记录
"""
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete


class IdempotencyStatus(str, Enum):
    """幂等性状态"""
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 已失败


class IdempotencyError(Exception):
    """幂等性错误"""
    pass


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """幂等性中间件"""
    
    def __init__(self, app, db_session_factory, ttl: int = 86400):
        """
        初始化幂等性中间件
        
        参数:
        - app: FastAPI应用
        - db_session_factory: 数据库会话工厂
        - ttl: 幂等记录过期时间（秒），默认24小时
        """
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.ttl = ttl
        
        logger.info("✅ 幂等性中间件初始化完成")
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 只处理POST/PUT/DELETE请求
        if request.method not in ['POST', 'PUT', 'DELETE']:
            return await call_next(request)
        
        # 跳过不需要幂等性的路径
        if self._should_skip(request.url.path):
            return await call_next(request)
        
        # 获取幂等键
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            # 如果没有幂等键，正常处理请求
            return await call_next(request)
        
        # 处理幂等请求
        return await self._handle_idempotent_request(
            request,
            idempotency_key,
            call_next
        )
    
    def _should_skip(self, path: str) -> bool:
        """判断是否跳过幂等性检查"""
        skip_paths = [
            '/health',
            '/docs',
            '/openapi.json',
            '/ws',  # WebSocket
        ]
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _handle_idempotent_request(
        self,
        request: Request,
        idempotency_key: str,
        call_next
    ):
        """处理幂等请求"""
        async with self.db_session_factory() as db:
            # 读取请求体
            body = await request.body()
            
            # 计算请求哈希
            request_hash = self._compute_request_hash(
                request.method,
                request.url.path,
                body
            )
            
            # 检查是否已处理
            existing = await self._get_idempotency_record(
                db,
                idempotency_key
            )
            
            if existing:
                return await self._handle_existing_request(
                    existing,
                    request_hash
                )
            
            # 创建幂等记录（状态：处理中）
            await self._create_idempotency_record(
                db,
                idempotency_key,
                request_hash,
                IdempotencyStatus.PROCESSING
            )
            
            try:
                # 执行请求
                response = await call_next(request)
                
                # 读取响应体
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # 保存响应
                await self._update_idempotency_record(
                    db,
                    idempotency_key,
                    IdempotencyStatus.COMPLETED,
                    json.loads(response_body.decode()) if response_body else None
                )
                
                logger.info(f"✅ 幂等请求处理成功: {idempotency_key}")
                
                # 返回响应
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            
            except Exception as e:
                # 标记为失败
                await self._update_idempotency_record(
                    db,
                    idempotency_key,
                    IdempotencyStatus.FAILED,
                    None
                )
                
                logger.error(f"❌ 幂等请求处理失败: {idempotency_key} - {e}")
                raise
    
    async def _handle_existing_request(
        self,
        existing: dict,
        request_hash: str
    ):
        """处理已存在的请求"""
        # 验证请求哈希
        if existing['request_hash'] != request_hash:
            raise HTTPException(
                status_code=422,
                detail={
                    'error': 'idempotency_key_mismatch',
                    'message': '幂等键已存在，但请求内容不同'
                }
            )
        
        # 根据状态返回响应
        if existing['status'] == IdempotencyStatus.COMPLETED:
            # 返回之前的响应
            logger.info(f"🔄 返回缓存的幂等响应: {existing['idempotency_key']}")
            return JSONResponse(
                content=existing['response_data'],
                status_code=200,
                headers={'X-Idempotency-Replay': 'true'}
            )
        
        elif existing['status'] == IdempotencyStatus.PROCESSING:
            # 请求正在处理中
            raise HTTPException(
                status_code=409,
                detail={
                    'error': 'request_in_progress',
                    'message': '请求正在处理中，请稍后重试'
                }
            )
        
        elif existing['status'] == IdempotencyStatus.FAILED:
            # 之前的请求失败了，允许重试
            logger.info(f"🔄 重试失败的幂等请求: {existing['idempotency_key']}")
            # 删除失败记录，允许重新处理
            await self._delete_idempotency_record(
                existing['idempotency_key']
            )
            # 继续处理请求（通过抛出异常让外层重新处理）
            raise IdempotencyError("重试失败的请求")
    
    def _compute_request_hash(
        self,
        method: str,
        path: str,
        body: bytes
    ) -> str:
        """计算请求哈希"""
        content = f"{method}:{path}:{body.decode()}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _get_idempotency_record(
        self,
        db: AsyncSession,
        idempotency_key: str
    ) -> Optional[dict]:
        """获取幂等记录"""
        query = """
        SELECT * FROM idempotency_keys
        WHERE idempotency_key = :key AND expires_at > NOW()
        """
        
        result = await db.execute(
            query,
            {'key': idempotency_key}
        )
        
        row = result.fetchone()
        return dict(row) if row else None
    
    async def _create_idempotency_record(
        self,
        db: AsyncSession,
        idempotency_key: str,
        request_hash: str,
        status: IdempotencyStatus
    ):
        """创建幂等记录"""
        expires_at = datetime.now() + timedelta(seconds=self.ttl)
        
        query = """
        INSERT INTO idempotency_keys
        (idempotency_key, request_hash, status, expires_at, created_at)
        VALUES (:key, :hash, :status, :expires_at, NOW())
        """
        
        await db.execute(
            query,
            {
                'key': idempotency_key,
                'hash': request_hash,
                'status': status.value,
                'expires_at': expires_at
            }
        )
        await db.commit()
    
    async def _update_idempotency_record(
        self,
        db: AsyncSession,
        idempotency_key: str,
        status: IdempotencyStatus,
        response_data: Optional[dict]
    ):
        """更新幂等记录"""
        query = """
        UPDATE idempotency_keys
        SET status = :status,
            response_data = :response_data,
            updated_at = NOW()
        WHERE idempotency_key = :key
        """
        
        await db.execute(
            query,
            {
                'key': idempotency_key,
                'status': status.value,
                'response_data': json.dumps(response_data) if response_data else None
            }
        )
        await db.commit()
    
    async def _delete_idempotency_record(
        self,
        idempotency_key: str
    ):
        """删除幂等记录"""
        async with self.db_session_factory() as db:
            query = "DELETE FROM idempotency_keys WHERE idempotency_key = :key"
            await db.execute(query, {'key': idempotency_key})
            await db.commit()
    
    async def cleanup_expired_records(self):
        """清理过期记录（定时任务）"""
        async with self.db_session_factory() as db:
            query = "DELETE FROM idempotency_keys WHERE expires_at < NOW()"
            result = await db.execute(query)
            await db.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"🧹 清理过期幂等记录: {deleted_count}条")


class IdempotencyHelper:
    """幂等性辅助类"""
    
    @staticmethod
    def generate_key() -> str:
        """生成幂等键"""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def with_idempotency_key(func):
        """装饰器：自动添加幂等键"""
        async def wrapper(*args, **kwargs):
            # 检查是否已有幂等键
            if 'idempotency_key' not in kwargs:
                kwargs['idempotency_key'] = IdempotencyHelper.generate_key()
            
            return await func(*args, **kwargs)
        
        return wrapper
