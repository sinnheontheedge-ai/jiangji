"""
账户管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

from core.database import get_db, Account
from core.binance_client import get_binance_client


router = APIRouter()


class AccountCreate(BaseModel):
    """创建账户请求"""
    name: str
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool = False
    proxy_config: Optional[dict] = None  # 添加代理配置字段


class AccountUpdate(BaseModel):
    """更新账户请求"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: Optional[bool] = None
    is_active: Optional[bool] = None
    proxy_config: Optional[dict] = None  # 添加代理配置字段


class AccountResponse(BaseModel):
    """账户响应"""
    account_id: int
    name: str
    exchange: str
    api_key: str  # ✅ 修复: 添加api_key字段,前端需要显示
    balance: float
    status: str
    testnet: bool
    created_at: str  # ✅ 修复: 添加创建时间
    
    class Config:
        from_attributes = True


@router.post("/", response_model=AccountResponse)
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db)):
    """创建账户"""
    try:
        # 创建账户
        new_account = Account(
            name=account.name,
            exchange=account.exchange,
            api_key=account.api_key,
            api_secret=account.api_secret,
            testnet=account.testnet,
            proxy_config=account.proxy_config,  # 添加代理配置
            initial_balance=0.0,
            current_balance=0.0,
            is_active=True
        )
        
        db.add(new_account)
        await db.commit()  # 修复: 使用commit确保数据持久化
        await db.refresh(new_account)
        
        logger.info(f"✅ 账户创建成功: {new_account.name} (ID: {new_account.id})")
        
        # 创建后立即查询币安余额
        try:
            client = await get_binance_client(
                account_id=new_account.id,
                api_key=new_account.api_key,
                api_secret=new_account.api_secret,
                testnet=new_account.testnet,
                proxy=new_account.proxy_config  # 添加代理配置
            )
            balance_info = await client.get_account_balance()
            new_account.current_balance = balance_info['total_balance']
            new_account.initial_balance = balance_info['total_balance']
            await db.flush()
            logger.info(f"✅ 自动获取账户余额: {balance_info['total_balance']} USDT")
        except Exception as e:
            logger.warning(f"⚠️ 获取账户余额失败（账户已创建）: {e}")
        
        return AccountResponse(
            account_id=new_account.id,
            name=new_account.name,
            exchange=new_account.exchange,
            api_key=new_account.api_key,  # ✅ 修复: 返回api_key
            balance=new_account.current_balance,
            status="active" if new_account.is_active else "inactive",
            testnet=new_account.testnet,
            created_at=new_account.created_at.isoformat() if new_account.created_at else ""  # ✅ 修复: 返回创建时间
        )
        
    except Exception as e:
        logger.error(f"❌ 创建账户失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建账户失败: {str(e)}")


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(db: AsyncSession = Depends(get_db)):
    """获取所有账户"""
    try:
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        
        return [
            AccountResponse(
                account_id=acc.id,
                name=acc.name,
                exchange=acc.exchange,
                api_key=acc.api_key,  # ✅ 修复: 返回api_key
                balance=acc.current_balance,
                status="active" if acc.is_active else "inactive",
                testnet=acc.testnet,
                created_at=acc.created_at.isoformat() if acc.created_at else ""  # ✅ 修复: 返回创建时间
            )
            for acc in accounts
        ]
        
    except Exception as e:
        logger.error(f"❌ 获取账户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取账户列表失败: {str(e)}")


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个账户"""
    try:
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        return AccountResponse(
            account_id=account.id,
            name=account.name,
            exchange=account.exchange,
            api_key=account.api_key,  # ✅ 修复: 返回api_key
            balance=account.current_balance,
            status="active" if account.is_active else "inactive",
            testnet=account.testnet,
            created_at=account.created_at.isoformat() if account.created_at else ""  # ✅ 修复: 返回创建时间
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取账户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取账户失败: {str(e)}")


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新账户"""
    try:
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        # 更新字段
        if account_update.name is not None:
            account.name = account_update.name
        if account_update.api_key is not None:
            account.api_key = account_update.api_key
        if account_update.api_secret is not None:
            account.api_secret = account_update.api_secret
        if account_update.testnet is not None:
            account.testnet = account_update.testnet
        if account_update.is_active is not None:
            account.is_active = account_update.is_active
        if account_update.proxy_config is not None:
            account.proxy_config = account_update.proxy_config  # 添加代理配置更新
        
        await db.commit()  # 修复: 使用commit确保数据持久化
        await db.refresh(account)
        
        logger.info(f"✅ 账户更新成功: {account.name} (ID: {account.id})")
        
        return AccountResponse(
            account_id=account.id,
            name=account.name,
            exchange=account.exchange,
            api_key=account.api_key,  # ✅ 修复: 返回api_key
            balance=account.current_balance,
            status="active" if account.is_active else "inactive",
            testnet=account.testnet,
            created_at=account.created_at.isoformat() if account.created_at else ""  # ✅ 修复: 返回创建时间
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新账户失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新账户失败: {str(e)}")


@router.get("/{account_id}/balance")
async def get_account_balance(account_id: int, db: AsyncSession = Depends(get_db)):
    """
    获取账户在币安的实时余额
    
    Returns:
        {
            'total_balance': 总资产(USDT),
            'available_balance': 可用余额(USDT),
            'margin_balance': 保证金余额(USDT),
            'unrealized_pnl': 未实现盈亏(USDT),
            'positions': [持仓列表]
        }
    """
    try:
        # 查询账户
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        # 获取币安客户端
        client = await get_binance_client(
            account_id=account.id,
            api_key=account.api_key,
            api_secret=account.api_secret,
            testnet=account.testnet,
            proxy=account.proxy_config  # 添加代理配置
        )
        
        # 查询余额
        balance_info = await client.get_account_balance()
        
        # 更新数据库中的余额
        account.current_balance = balance_info['total_balance']
        await db.flush()
        
        logger.info(
            f"✅ 获取账户余额成功: {account.name} "
            f"总资产={balance_info['total_balance']} USDT"
        )
        
        return balance_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取账户余额失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取账户余额失败: {str(e)}")


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """删除账户"""
    try:
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        await db.delete(account)
        await db.flush()
        
        logger.info(f"✅ 账户删除成功: {account.name} (ID: {account.id})")
        
        return {"message": "账户删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除账户失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除账户失败: {str(e)}")
