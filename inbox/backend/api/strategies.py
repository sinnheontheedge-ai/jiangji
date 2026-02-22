"""
策略管理API - 修复版（统一使用数据库）
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import os

from core.database import get_db, Strategy


router = APIRouter()


class StrategyInfo(BaseModel):
    """策略信息"""
    strategy_id: int  # 修复: 使用整数ID
    name: str
    description: str
    is_active: bool
    
    class Config:
        from_attributes = True


class StrategyCreate(BaseModel):
    """创建策略请求"""
    name: str
    description: Optional[str] = None
    code: str
    parameters: Optional[dict] = None


class StrategyUpdate(BaseModel):
    """更新策略请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


@router.get("/", response_model=List[StrategyInfo])
async def list_strategies(db: AsyncSession = Depends(get_db)):
    """
    获取策略列表
    
    修复: 从数据库查询策略，而不是文件系统
    """
    try:
        result = await db.execute(select(Strategy))
        strategies = result.scalars().all()
        
        return [
            StrategyInfo(
                strategy_id=s.id,  # 修复: 使用数据库ID
                name=s.name,
                description=s.description or f"策略: {s.name}",
                is_active=s.is_active
            )
            for s in strategies
        ]
        
    except Exception as e:
        logger.error(f"❌ 获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=StrategyInfo)
async def create_strategy(strategy: StrategyCreate, db: AsyncSession = Depends(get_db)):
    """
    创建策略
    
    新增: 支持通过API创建策略
    """
    try:
        # 检查策略名称是否已存在
        result = await db.execute(
            select(Strategy).where(Strategy.name == strategy.name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"策略名称 '{strategy.name}' 已存在")
        
        # 创建策略
        new_strategy = Strategy(
            name=strategy.name,
            description=strategy.description or f"策略: {strategy.name}",
            code=strategy.code,
            parameters=strategy.parameters,
            is_active=True
        )
        
        db.add(new_strategy)
        await db.commit()
        await db.refresh(new_strategy)
        
        logger.info(f"✅ 创建策略成功: ID={new_strategy.id}, Name={new_strategy.name}")
        
        return StrategyInfo(
            strategy_id=new_strategy.id,
            name=new_strategy.name,
            description=new_strategy.description,
            is_active=new_strategy.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建策略失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=StrategyInfo)
async def upload_strategy(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    上传策略文件
    
    修复: 保存到数据库，而不是文件系统
    """
    try:
        # 验证文件类型
        if not file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="只支持.py文件")
        
        # 读取文件内容
        code_content = await file.read()
        code_str = code_content.decode('utf-8')
        
        # 提取策略名称（从文件名）
        strategy_name = file.filename.replace('.py', '')
        
        # 基本安全检查
        dangerous_keywords = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
        for keyword in dangerous_keywords:
            if keyword in code_str:
                raise HTTPException(
                    status_code=400, 
                    detail=f"代码包含危险关键字: {keyword}"
                )
        
        # 检查策略名称是否已存在
        result = await db.execute(
            select(Strategy).where(Strategy.name == strategy_name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 更新现有策略
            existing.code = code_str
            existing.description = f"上传的策略: {strategy_name}"
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
            
            logger.info(f"✅ 更新策略成功: ID={existing.id}, Name={existing.name}")
            
            return StrategyInfo(
                strategy_id=existing.id,
                name=existing.name,
                description=existing.description,
                is_active=existing.is_active
            )
        else:
            # 创建新策略
            new_strategy = Strategy(
                name=strategy_name,
                description=f"上传的策略: {strategy_name}",
                code=code_str,
                is_active=True
            )
            
            db.add(new_strategy)
            await db.commit()
            await db.refresh(new_strategy)
            
            logger.info(f"✅ 上传策略成功: ID={new_strategy.id}, Name={new_strategy.name}")
            
            return StrategyInfo(
                strategy_id=new_strategy.id,
                name=new_strategy.name,
                description=new_strategy.description,
                is_active=new_strategy.is_active
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 上传策略失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}", response_model=StrategyInfo)
async def get_strategy(strategy_id: int, db: AsyncSession = Depends(get_db)):
    """
    获取单个策略详情
    
    修复: 从数据库查询，strategy_id为整数
    """
    try:
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        return StrategyInfo(
            strategy_id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            is_active=strategy.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取策略详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{strategy_id}", response_model=StrategyInfo)
async def update_strategy(
    strategy_id: int, 
    strategy_update: StrategyUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    更新策略
    
    新增: 支持更新策略
    """
    try:
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 更新字段
        if strategy_update.name is not None:
            strategy.name = strategy_update.name
        if strategy_update.description is not None:
            strategy.description = strategy_update.description
        if strategy_update.code is not None:
            strategy.code = strategy_update.code
        if strategy_update.parameters is not None:
            strategy.parameters = strategy_update.parameters
        if strategy_update.is_active is not None:
            strategy.is_active = strategy_update.is_active
        
        await db.commit()
        await db.refresh(strategy)
        
        logger.info(f"✅ 更新策略成功: ID={strategy_id}, Name={strategy.name}")
        
        return StrategyInfo(
            strategy_id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            is_active=strategy.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新策略失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: AsyncSession = Depends(get_db)):
    """
    删除策略
    
    修复: 从数据库删除，strategy_id为整数
    """
    try:
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 删除策略
        await db.delete(strategy)
        await db.commit()
        
        logger.info(f"🗑️ 删除策略成功: ID={strategy_id}, Name={strategy.name}")
        
        return {"message": "策略已删除", "strategy_id": strategy_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除策略失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
