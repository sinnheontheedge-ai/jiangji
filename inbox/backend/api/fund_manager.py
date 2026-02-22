"""
资金管理API - 绑定到具体账户
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from plugins.fund_engine.compounding import CompoundingEngine, CompoundingMode
from plugins.fund_engine.profit_extract import (
    ProfitExtractionEngine, 
    InitialCapitalProtection, 
    ProfitMultipleEndpoint,
    ExtractionMode
)
from plugins.fund_engine.auto_replenish import AutoReplenishEngine
from core.database import get_db, Account, FundConfig


router = APIRouter()


# ==================== 请求/响应模型 ====================

class CompoundingConfigModel(BaseModel):
    """复利配置"""
    mode: str  # "stage" | "perpetual"
    compound_ratio: float
    initial_base: float
    position_percent: float
    concurrent_positions: int


class ProfitExtractionConfigModel(BaseModel):
    """盈利提取配置"""
    mode: str  # "wallet_threshold" | "multiple_mode"
    initial_margin: float
    threshold: Optional[float] = None
    multiple: Optional[float] = None
    max_extract_ratio: Optional[float] = None


class CapitalProtectionConfigModel(BaseModel):
    """初始金额保护配置"""
    enabled: bool
    initial_amount: Optional[float] = None
    protect_multiple: Optional[float] = None
    max_protect_count: Optional[int] = None
    transfer_step: Optional[float] = None


class ProfitEndpointConfigModel(BaseModel):
    """盈利倍数终点配置"""
    enabled: bool
    initial_amount: Optional[float] = None
    endpoint_multiple: Optional[float] = None
    transfer_step: Optional[float] = None


class AutoReplenishConfigModel(BaseModel):
    """自动补足余额配置"""
    enabled: bool
    initial_capital: Optional[float] = None
    check_interval: Optional[int] = 60
    min_transfer_amount: Optional[float] = 10
    enable_alert: Optional[bool] = True
    alert_threshold: Optional[float] = 0.8
    max_replenish_per_day: Optional[int] = 10


class FundManagerConfigRequest(BaseModel):
    """资金管理配置请求"""
    account_id: int
    compounding: CompoundingConfigModel
    profit_extraction: ProfitExtractionConfigModel
    capital_protection: Optional[CapitalProtectionConfigModel] = None
    profit_endpoint: Optional[ProfitEndpointConfigModel] = None
    auto_replenish: Optional[AutoReplenishConfigModel] = None


class MarginCalculationRequest(BaseModel):
    """保证金计算请求"""
    account_id: int
    available_balance: float
    is_single_position: bool = True


# ==================== 内存中的引擎实例 ====================
# 键为 account_id
_compounding_engines: Dict[int, CompoundingEngine] = {}
_profit_extraction_engines: Dict[int, ProfitExtractionEngine] = {}
_capital_protections: Dict[int, InitialCapitalProtection] = {}
_profit_endpoints: Dict[int, ProfitMultipleEndpoint] = {}
_auto_replenish_engines: Dict[int, AutoReplenishEngine] = {}


# ==================== API路由 ====================

@router.post("/config")
async def create_config(config: FundManagerConfigRequest, db: AsyncSession = Depends(get_db)):
    """创建资金管理配置"""
    return await _update_config_impl(config, db)

async def _update_config_impl(config: FundManagerConfigRequest, db: AsyncSession):
    """更新资金管理配置的实现"""
    try:
        # 检查账户是否存在
        result = await db.execute(select(Account).where(Account.id == config.account_id))
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        # 查找或创建资金管理配置
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == config.account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            fund_config = FundConfig(account_id=config.account_id)
            db.add(fund_config)
        
        # 更新复利配置
        fund_config.compounding_mode = config.compounding.mode
        fund_config.compound_ratio = config.compounding.compound_ratio
        fund_config.initial_base = config.compounding.initial_base
        fund_config.current_base = config.compounding.initial_base
        fund_config.position_percent = config.compounding.position_percent
        fund_config.concurrent_positions = config.compounding.concurrent_positions
        
        # 更新盈利提取配置
        fund_config.extraction_mode = config.profit_extraction.mode
        fund_config.initial_margin = config.profit_extraction.initial_margin
        fund_config.threshold = config.profit_extraction.threshold
        fund_config.multiple = config.profit_extraction.multiple
        fund_config.max_extract_ratio = config.profit_extraction.max_extract_ratio
        
        # 更新初始金额保护配置
        if config.capital_protection:
            fund_config.protection_enabled = config.capital_protection.enabled
            if config.capital_protection.enabled:
                fund_config.protection_initial_amount = config.capital_protection.initial_amount
                fund_config.protection_multiple = config.capital_protection.protect_multiple
                fund_config.protection_max_count = config.capital_protection.max_protect_count
                fund_config.protection_transfer_step = config.capital_protection.transfer_step
        
        # 更新盈利倍数终点配置
        if config.profit_endpoint:
            fund_config.endpoint_enabled = config.profit_endpoint.enabled
            if config.profit_endpoint.enabled:
                fund_config.endpoint_initial_amount = config.profit_endpoint.initial_amount
                fund_config.endpoint_multiple = config.profit_endpoint.endpoint_multiple
                fund_config.endpoint_transfer_step = config.profit_endpoint.transfer_step
        
        # 更新自动补足余额配置
        if config.auto_replenish:
            fund_config.replenish_enabled = config.auto_replenish.enabled
            if config.auto_replenish.enabled:
                fund_config.replenish_initial_capital = config.auto_replenish.initial_capital
                fund_config.replenish_check_interval = config.auto_replenish.check_interval
                fund_config.replenish_min_amount = config.auto_replenish.min_transfer_amount
                fund_config.replenish_enable_alert = config.auto_replenish.enable_alert
                fund_config.replenish_alert_threshold = config.auto_replenish.alert_threshold
                fund_config.replenish_max_per_day = config.auto_replenish.max_replenish_per_day
        
        await db.flush()
        
        # 初始化内存中的引擎
        _init_engines_for_account(config.account_id, fund_config)
        
        logger.info(f"✅ 账户 {config.account_id} 的资金管理配置已更新")
        
        return {"message": "配置更新成功", "account_id": config.account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新资金管理配置失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config")
async def update_config(config: FundManagerConfigRequest, db: AsyncSession = Depends(get_db)):
    """更新资金管理配置"""
    return await _update_config_impl(config, db)


@router.get("/config/{account_id}")
async def get_config(account_id: int, db: AsyncSession = Depends(get_db)):
    """获取指定账户的资金管理配置"""
    try:
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            raise HTTPException(status_code=404, detail="该账户尚未配置资金管理")
        
        response = {
            "account_id": account_id,
            "compounding": {
                "mode": fund_config.compounding_mode,
                "compound_ratio": fund_config.compound_ratio,
                "initial_base": fund_config.initial_base,
                "current_base": fund_config.current_base,
                "position_percent": fund_config.position_percent,
                "concurrent_positions": fund_config.concurrent_positions
            },
            "profit_extraction": {
                "mode": fund_config.extraction_mode,
                "initial_margin": fund_config.initial_margin,
                "threshold": fund_config.threshold,
                "multiple": fund_config.multiple,
                "max_extract_ratio": fund_config.max_extract_ratio
            }
        }
        
        if fund_config.protection_enabled:
            response["capital_protection"] = {
                "enabled": True,
                "initial_amount": fund_config.protection_initial_amount,
                "protect_multiple": fund_config.protection_multiple,
                "max_protect_count": fund_config.protection_max_count,
                "transfer_step": fund_config.protection_transfer_step,
                "protect_count": fund_config.protection_count
            }
        
        if fund_config.endpoint_enabled:
            response["profit_endpoint"] = {
                "enabled": True,
                "initial_amount": fund_config.endpoint_initial_amount,
                "endpoint_multiple": fund_config.endpoint_multiple,
                "transfer_step": fund_config.endpoint_transfer_step,
                "triggered": fund_config.endpoint_triggered
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取资金管理配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/calculate-margin")
async def calculate_margin(request: MarginCalculationRequest, db: AsyncSession = Depends(get_db)):
    """计算保证金"""
    try:
        # 获取配置
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == request.account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            raise HTTPException(status_code=404, detail="该账户尚未配置资金管理")
        
        # 初始化引擎(如果尚未初始化)
        if request.account_id not in _compounding_engines:
            _init_engines_for_account(request.account_id, fund_config)
        
        engine = _compounding_engines[request.account_id]
        margin = engine.calculate_margin(
            available_balance=request.available_balance,
            is_single_position=request.is_single_position
        )
        
        return {
            "margin": margin,
            "mode": engine.mode.value,
            "current_base": engine.current_base if engine.mode == CompoundingMode.STAGE else None,
            "next_threshold": engine.get_next_compound_threshold() if engine.mode == CompoundingMode.STAGE else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 计算保证金失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.get("/status/{account_id}")
async def get_status(account_id: int, db: AsyncSession = Depends(get_db)):
    """获取指定账户的资金管理状态"""
    try:
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            raise HTTPException(status_code=404, detail="该账户尚未配置资金管理")
        
        # 初始化引擎(如果尚未初始化)
        if account_id not in _compounding_engines:
            _init_engines_for_account(account_id, fund_config)
        
        compounding_engine = _compounding_engines[account_id]
        profit_engine = _profit_extraction_engines[account_id]
        
        status = {
            "account_id": account_id,
            "compounding_status": compounding_engine.get_status(),
            "profit_extraction_status": profit_engine.get_status()
        }
        
        if account_id in _capital_protections:
            protection = _capital_protections[account_id]
            status["capital_protection_status"] = {
                "initial_amount": protection.initial_amount,
                "protect_multiple": protection.protect_multiple,
                "max_protect_count": protection.max_protect_count,
                "protect_count": protection.protect_count,
                "threshold": protection.threshold
            }
        
        if account_id in _profit_endpoints:
            endpoint = _profit_endpoints[account_id]
            status["profit_endpoint_status"] = {
                "initial_amount": endpoint.initial_amount,
                "endpoint_multiple": endpoint.endpoint_multiple,
                "threshold": endpoint.threshold,
                "triggered": endpoint.triggered
            }
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取资金管理状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/reset/{account_id}")
async def reset_fund_manager(account_id: int, db: AsyncSession = Depends(get_db)):
    """重置指定账户的资金管理状态"""
    try:
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            raise HTTPException(status_code=404, detail="该账户尚未配置资金管理")
        
        # 重置数据库中的状态
        fund_config.current_base = fund_config.initial_base
        fund_config.protection_count = 0
        fund_config.endpoint_triggered = False
        
        await db.flush()
        
        # 重新初始化引擎
        _init_engines_for_account(account_id, fund_config)
        
        logger.info(f"✅ 账户 {account_id} 的资金管理状态已重置")
        
        return {"message": "状态重置成功", "account_id": account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 重置资金管理状态失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.delete("/config/{account_id}")
async def delete_config(account_id: int, db: AsyncSession = Depends(get_db)):
    """删除指定账户的资金管理配置"""
    try:
        result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
        fund_config = result.scalar_one_or_none()
        
        if not fund_config:
            raise HTTPException(status_code=404, detail="该账户尚未配置资金管理")
        
        await db.delete(fund_config)
        await db.flush()
        
        # 清理内存中的引擎
        _compounding_engines.pop(account_id, None)
        _profit_extraction_engines.pop(account_id, None)
        _capital_protections.pop(account_id, None)
        _profit_endpoints.pop(account_id, None)
        
        logger.info(f"✅ 账户 {account_id} 的资金管理配置已删除")
        
        return {"message": "配置删除成功", "account_id": account_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除资金管理配置失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ==================== 辅助函数 ====================

def _init_engines_for_account(account_id: int, fund_config: FundConfig):
    """为指定账户初始化引擎"""
    # 初始化复利引擎
    _compounding_engines[account_id] = CompoundingEngine({
        "mode": fund_config.compounding_mode,
        "compound_ratio": fund_config.compound_ratio,
        "initial_base": fund_config.initial_base,
        "position_percent": fund_config.position_percent,
        "concurrent_positions": fund_config.concurrent_positions
    })
    
    # 设置当前复利起点
    _compounding_engines[account_id].current_base = fund_config.current_base
    
    # 初始化盈利提取引擎
    extraction_config = {
        "mode": fund_config.extraction_mode,
        "initial_margin": fund_config.initial_margin
    }
    if fund_config.threshold:
        extraction_config["threshold"] = fund_config.threshold
    if fund_config.multiple:
        extraction_config["multiple"] = fund_config.multiple
    if fund_config.max_extract_ratio:
        extraction_config["max_extract_ratio"] = fund_config.max_extract_ratio
    
    _profit_extraction_engines[account_id] = ProfitExtractionEngine(extraction_config)
    
    # 初始化初始金额保护(如果启用)
    if fund_config.protection_enabled:
        _capital_protections[account_id] = InitialCapitalProtection({
            "initial_amount": fund_config.protection_initial_amount,
            "protect_multiple": fund_config.protection_multiple,
            "max_protect_count": fund_config.protection_max_count,
            "transfer_step": fund_config.protection_transfer_step
        })
        _capital_protections[account_id].protect_count = fund_config.protection_count
    
    # 初始化盈利倍数终点(如果启用)
    if fund_config.endpoint_enabled:
        _profit_endpoints[account_id] = ProfitMultipleEndpoint({
            "initial_amount": fund_config.endpoint_initial_amount,
            "endpoint_multiple": fund_config.endpoint_multiple,
            "transfer_step": fund_config.endpoint_transfer_step
        })
        _profit_endpoints[account_id].triggered = fund_config.endpoint_triggered
    
    # 初始化自动补足余额引擎(如果启用)
    if fund_config.replenish_enabled:
        _auto_replenish_engines[account_id] = AutoReplenishEngine({
            "initial_capital": fund_config.replenish_initial_capital,
            "check_interval": fund_config.replenish_check_interval,
            "min_transfer_amount": fund_config.replenish_min_amount,
            "enable_alert": fund_config.replenish_enable_alert,
            "alert_threshold": fund_config.replenish_alert_threshold,
            "max_replenish_per_day": fund_config.replenish_max_per_day
        })
