"""
交易安全工具函数
包含持仓检查、幂等性检查等安全机制
"""
from typing import Dict, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from core.database import Position, IdempotencyKey
from core.binance_client import BinanceClient


class TradingSafety:
    """交易安全检查器"""
    
    @staticmethod
    async def check_position_before_close(
        client: BinanceClient,
        symbol: str,
        expected_side: str,
        expected_amount: float,
        db_position_id: int
    ) -> bool:
        """
        平仓前检查持仓方向和数量
        
        Args:
            client: Binance客户端
            symbol: 交易对
            expected_side: 预期持仓方向 (LONG/SHORT)
            expected_amount: 预期持仓数量
            db_position_id: 数据库持仓ID
        
        Returns:
            是否通过检查
        
        Raises:
            ValueError: 检查失败时抛出异常
        """
        try:
            logger.info(
                f"🔍 平仓前检查: {symbol} 预期方向={expected_side} "
                f"预期数量={expected_amount} 持仓ID={db_position_id}"
            )
            
            # 获取交易所当前持仓
            positions = await client.get_positions()
            exchange_position = next(
                (p for p in positions if p['symbol'] == symbol),
                None
            )
            
            if not exchange_position:
                raise ValueError(
                    f"❌ 交易所无持仓: {symbol}，无法平仓"
                )
            
            # 检查持仓方向
            exchange_side = exchange_position.get('side', '').upper()
            if exchange_side != expected_side:
                raise ValueError(
                    f"❌ 持仓方向不匹配: "
                    f"数据库={expected_side}, "
                    f"交易所={exchange_side}"
                )
            
            # 检查持仓数量
            exchange_amount = abs(float(exchange_position.get('contracts', 0)))
            if exchange_amount == 0:
                raise ValueError(
                    f"❌ 交易所持仓数量为0，无法平仓"
                )
            
            # 允许一定的数量误差（0.1%）
            amount_diff = abs(exchange_amount - expected_amount) / expected_amount
            if amount_diff > 0.001:
                logger.warning(
                    f"⚠️ 持仓数量不完全匹配: "
                    f"数据库={expected_amount}, "
                    f"交易所={exchange_amount}, "
                    f"误差={amount_diff*100:.2f}%"
                )
            
            logger.info(
                f"✅ 平仓前检查通过: {symbol} 方向={exchange_side} "
                f"数量={exchange_amount}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ 平仓前检查失败: {e}")
            raise
    
    @staticmethod
    async def check_idempotency(
        db: AsyncSession,
        idempotency_key: str,
        operation: str
    ) -> bool:
        """
        检查幂等性，防止重复下单
        
        Args:
            db: 数据库会话
            idempotency_key: 幂等性键
            operation: 操作类型
        
        Returns:
            是否通过检查（True=可以执行，False=重复操作）
        
        Raises:
            ValueError: 重复操作时抛出异常
        """
        try:
            logger.debug(f"🔍 幂等性检查: key={idempotency_key} op={operation}")
            
            # 查询是否存在相同的幂等性键
            stmt = select(IdempotencyKey).where(
                IdempotencyKey.key == idempotency_key
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # 检查是否在有效期内（60秒）
                if existing.created_at > datetime.utcnow() - timedelta(seconds=60):
                    logger.warning(
                        f"⚠️ 检测到重复操作: key={idempotency_key} "
                        f"status={existing.status} "
                        f"created_at={existing.created_at}"
                    )
                    raise ValueError(
                        f"❌ 重复操作，禁止执行: {idempotency_key}"
                    )
                else:
                    # 过期的幂等性键，可以删除
                    await db.delete(existing)
                    await db.commit()
                    logger.debug(f"🗑️ 删除过期幂等性键: {idempotency_key}")
            
            # 创建新的幂等性键
            new_key = IdempotencyKey(
                key=idempotency_key,
                operation=operation,
                status="PROCESSING",
                created_at=datetime.utcnow()
            )
            db.add(new_key)
            await db.commit()
            
            logger.info(f"✅ 幂等性检查通过: {idempotency_key}")
            return True
            
        except ValueError:
            # 重复操作，直接抛出
            raise
        except Exception as e:
            logger.error(f"❌ 幂等性检查失败: {e}")
            raise
    
    @staticmethod
    async def complete_idempotency(
        db: AsyncSession,
        idempotency_key: str,
        success: bool,
        result: Optional[Dict] = None
    ):
        """
        完成幂等性记录
        
        Args:
            db: 数据库会话
            idempotency_key: 幂等性键
            success: 是否成功
            result: 结果数据
        """
        try:
            stmt = select(IdempotencyKey).where(
                IdempotencyKey.key == idempotency_key
            )
            result_obj = await db.execute(stmt)
            key_obj = result_obj.scalar_one_or_none()
            
            if key_obj:
                key_obj.status = "COMPLETED" if success else "FAILED"
                key_obj.result = result
                await db.commit()
                
                logger.debug(
                    f"✅ 幂等性记录已更新: {idempotency_key} "
                    f"status={key_obj.status}"
                )
        except Exception as e:
            logger.error(f"❌ 更新幂等性记录失败: {e}")
