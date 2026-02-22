"""
策略实例管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from core.database import get_db, Instance, InstanceStatus, Strategy, Account
from core.strategy_manager import strategy_manager
from core.trade_executor import trade_executor
from core.fund_monitor import fund_monitor
from core.risk_monitor import risk_monitor
from plugins.data_source.market_data import MarketDataSource
from core.binance_client import BinanceClient


router = APIRouter()


class InstanceCreate(BaseModel):
    """创建策略实例请求"""
    name: str
    account_id: int
    strategy_id: int
    symbols: List[str]
    timeframe: str
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    position_mode: str = "single"
    use_step_locking: bool = False
    step_config: Optional[dict] = None


class InstanceResponse(BaseModel):
    """策略实例响应"""
    id: int
    name: str
    account_id: int
    strategy_id: int
    symbols: List[str]
    timeframe: str
    take_profit: Optional[float]
    stop_loss: Optional[float]
    position_mode: str
    use_step_locking: bool
    step_config: Optional[dict]
    status: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=InstanceResponse)
async def create_instance(instance: InstanceCreate, db: AsyncSession = Depends(get_db)):
    """创建策略实例"""
    try:
        # 创建数据库记录
        new_instance = Instance(
            name=instance.name,
            account_id=instance.account_id,
            strategy_id=instance.strategy_id,
            symbols=instance.symbols,
            timeframe=instance.timeframe,
            take_profit=instance.take_profit,
            stop_loss=instance.stop_loss,
            position_mode=instance.position_mode,
            use_step_locking=instance.use_step_locking,
            step_config=instance.step_config,
            status=InstanceStatus.IDLE.value
        )
        
        db.add(new_instance)
        await db.commit()
        await db.refresh(new_instance)
        
        logger.info(f"✅ 创建策略实例: ID={new_instance.id}, Name={new_instance.name}")
        return new_instance
        
    except Exception as e:
        logger.error(f"❌ 创建策略实例失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/start")
async def start_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    """启动策略实例"""
    try:
        # 查询实例
        result = await db.execute(
            select(Instance).where(Instance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")
        
        # 查询策略信息
        strategy_result = await db.execute(
            select(Strategy).where(Strategy.id == instance.strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 准备配置
        config = {
            "symbols": instance.symbols,
            "timeframe": instance.timeframe,
            "take_profit": instance.take_profit,
            "stop_loss": instance.stop_loss,
            "position_mode": instance.position_mode,
            "use_step_locking": instance.use_step_locking,
            "step_config": instance.step_config
        }
        
        # 修复: 从数据库加载策略代码并动态创建实例
        strategy_name = strategy.name
        strategy_code = strategy.code
        
        # 动态加载策略类
        try:
            # 创建临时模块
            import types
            import sys
            
            module_name = f"strategy_{strategy.id}_{strategy_name}"
            module = types.ModuleType(module_name)
            
            # 导入必要的基类
            from core.strategy_base import BaseStrategy
            module.BaseStrategy = BaseStrategy
            
            # 执行策略代码
            exec(strategy_code, module.__dict__)
            
            # 查找策略类（继承自BaseStrategy的类）
            strategy_class = None
            for item_name in dir(module):
                item = getattr(module, item_name)
                if isinstance(item, type) and issubclass(item, BaseStrategy) and item is not BaseStrategy:
                    strategy_class = item
                    break
            
            if not strategy_class:
                raise ValueError(f"策略代码中未找到继承自BaseStrategy的类")
            
            # 创建策略实例
            strategy_instance = strategy_class(config)
            
            # 注册到策略管理器
            strategy_manager.instances[instance_id] = strategy_instance
            
            logger.info(f"✅ 从数据库加载策略成功: {strategy_name} (ID={strategy.id})")
            
            # --- 🔴 新增逻辑: 预加载历史数据 ---
            required_length = strategy_instance.get_required_history_length()
            if required_length > 0:
                logger.info(f"策略需要 {required_length} 根历史数据，开始加载...")
                rest_client = None
                try:
                    # 查询账户信息
                    account_result = await db.execute(
                        select(Account).where(Account.id == instance.account_id)
                    )
                    account = account_result.scalar_one_or_none()
                    
                    if not account:
                        raise ValueError(f"账户 ID={instance.account_id} 不存在")
                    
                    # 创建临时的REST API客户端
                    rest_client = BinanceClient(
                        api_key=account.api_key,
                        api_secret=account.api_secret,
                        testnet=account.testnet,
                        proxy=account.proxy_config
                    )
                    
                    # 调用策略的数据准备方法
                    await strategy_instance.prepare_data(rest_client)
                    
                    logger.info(f"✅ 历史数据加载完成")
                    
                except Exception as e:
                    logger.error(f"❌ 历史数据加载失败: {e}")
                    # 清理已创建的策略实例
                    strategy_manager.remove_instance(instance_id)
                    raise HTTPException(status_code=500, detail=f"历史数据加载失败: {str(e)}")
                finally:
                    if rest_client:
                        await rest_client.close()  # 确保关闭临时客户端
            # --- 🔴 新增逻辑结束 ---
            
            # 加载交易执行器的引擎
            await trade_executor.load_engines_for_instance(instance_id, db)
            logger.info(f"✅ 为实例 {instance_id} 加载交易执行器引擎")
            
            # P0修复: 启动交易执行器，订阅signal:trade:*事件
            if not hasattr(trade_executor, '_started'):
                await trade_executor.start()
                trade_executor._started = True
                logger.info("✅ 交易执行器已启动，订阅 signal:trade:* 事件")
            
            # 加载资金监控器的引擎（WebSocket实时版本）
            await fund_monitor.load_manager_for_instance(instance_id, db)
            logger.info(f"✅ 为实例 {instance_id} 加载资金监控器（WebSocket实时推送）")
            
            # 加载风控监控器的引擎（WebSocket实时版本）
            await risk_monitor.load_manager_for_instance(instance_id, db)
            logger.info(f"✅ 为实例 {instance_id} 加载风控监控器（WebSocket实时推送）")
            
            # P0修复: 启动Step Lock Tick监听器
            from core.step_lock_tick_listener import step_lock_tick_listener
            # 注意: 全局单例，只需启动一次
            if not hasattr(step_lock_tick_listener, '_started'):
                await step_lock_tick_listener.start()
                step_lock_tick_listener._started = True
                logger.info("✅ Step Lock Tick监听器已启动")
            
            logger.info(f"✅ 市场数据源准备就绪（由策略管理器订阅）")
            
        except Exception as e:
            logger.error(f"❌ 加载策略失败: {e}")
            raise HTTPException(status_code=500, detail=f"加载策略失败: {str(e)}")
        
        # 更新状态
        instance.status = InstanceStatus.RUNNING.value
        await db.commit()
        
        logger.info(f"✅ 启动策略实例: ID={instance_id}, Name={instance.name}, Strategy={strategy_name}")
        return {"success": True, "message": "实例已启动"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 启动策略实例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/stop")
async def stop_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    """停止策略实例"""
    try:
        # 查询实例
        result = await db.execute(
            select(Instance).where(Instance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")
        
        # 移除策略实例
        strategy_manager.remove_instance(instance_id)
        
        # 更新状态
        instance.status = InstanceStatus.STOPPED.value
        await db.commit()
        
        logger.info(f"🛑 停止策略实例: ID={instance_id}, Name={instance.name}")
        return {"success": True, "message": "实例已停止"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 停止策略实例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[InstanceResponse])
async def list_instances(db: AsyncSession = Depends(get_db)):
    """获取所有策略实例"""
    try:
        result = await db.execute(select(Instance))
        instances = result.scalars().all()
        return instances
    except Exception as e:
        logger.error(f"❌ 获取实例列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个策略实例详情"""
    try:
        result = await db.execute(
            select(Instance).where(Instance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")
        
        return instance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取实例详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: int, 
    instance_update: InstanceCreate, 
    db: AsyncSession = Depends(get_db)
):
    """更新策略实例"""
    try:
        # 查询实例
        result = await db.execute(
            select(Instance).where(Instance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")
        
        # 更新字段
        instance.name = instance_update.name
        instance.account_id = instance_update.account_id
        instance.strategy_id = instance_update.strategy_id
        instance.symbols = instance_update.symbols
        instance.timeframe = instance_update.timeframe
        instance.take_profit = instance_update.take_profit
        instance.stop_loss = instance_update.stop_loss
        instance.position_mode = instance_update.position_mode
        instance.use_step_locking = instance_update.use_step_locking
        instance.step_config = instance_update.step_config
        
        await db.commit()
        await db.refresh(instance)
        
        logger.info(f"✅ 更新策略实例: ID={instance_id}, Name={instance.name}")
        return instance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新策略实例失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{instance_id}")
async def delete_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    """删除策略实例"""
    try:
        # 查询实例
        result = await db.execute(
            select(Instance).where(Instance.id == instance_id)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="实例不存在")
        
        # 如果实例正在运行,先停止
        if instance.status == InstanceStatus.RUNNING.value:
            strategy_manager.remove_instance(instance_id)
        
        # 删除实例
        await db.delete(instance)
        await db.commit()
        
        logger.info(f"🗑️ 删除策略实例: ID={instance_id}, Name={instance.name}")
        return {"success": True, "message": "实例已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除策略实例失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
