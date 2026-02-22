"""
自动补足余额模块
"""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import FundConfig, Account
from .binance_client import get_binance_client

logger = logging.getLogger(__name__)


class AutoReplenishManager:
    """自动补足余额管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def on_position_closed(self, account_id: int):
        """
        持仓平仓后检查并执行自动补足
        
        Args:
            account_id: 账户ID
        """
        try:
            # 获取账户和资金配置
            account = await self.db.get(Account, account_id)
            if not account:
                logger.error(f"❌ 账户不存在: {account_id}")
                return
            
            fund_config = await self.db.execute(
                select(FundConfig).where(FundConfig.account_id == account_id)
            )
            fund_config = fund_config.scalar_one_or_none()
            
            if not fund_config:
                logger.warning(f"⚠️ 账户 {account_id} 没有资金管理配置")
                return
            
            # 检查是否启用自动补足
            if not fund_config.enable_replenish:
                logger.debug(f"ℹ️ 账户 {account_id} 未启用自动补足余额")
                return
            
            # 获取账户余额
            client = await get_binance_client(
                account_id=account_id,
                api_key=account.api_key,
                api_secret=account.api_secret,
                testnet=account.testnet,
                proxy=account.proxy_config
            )
            
            balance_info = await client.get_account_balance()
            account_balance = balance_info.get('total_wallet_balance', 0.0)
            
            logger.info(f"📊 账户 {account_id} 当前余额: ${account_balance:.2f}, 初始投入: ${fund_config.initial_capital:.2f}")
            
            # 判断是亏损还是盈利
            if account_balance < fund_config.initial_capital:
                # 亏损，需要补足
                await self._handle_deficit(account_id, account_balance, fund_config, client)
            elif account_balance > fund_config.initial_capital and fund_config.total_replenished_amount > 0:
                # 盈利，且之前有补足过，需要覆盖
                await self._handle_profit(account_id, account_balance, fund_config, client)
            else:
                logger.info(f"ℹ️ 账户 {account_id} 余额正常，无需补足或覆盖")
        
        except Exception as e:
            logger.error(f"❌ 自动补足余额检查失败: {e}", exc_info=True)
    
    async def _handle_deficit(self, account_id: int, account_balance: float, fund_config: FundConfig, client):
        """
        处理亏损情况：补足余额
        
        Args:
            account_id: 账户ID
            account_balance: 当前账户余额
            fund_config: 资金管理配置
            client: 币安客户端
        """
        # 计算缺少的金额
        deficit = fund_config.initial_capital - account_balance
        
        logger.info(f"💰 账户 {account_id} 亏损 ${deficit:.2f}，需要补足")
        
        # 检查是否达到最小补足金额
        if deficit < fund_config.replenish_min_amount:
            logger.info(f"ℹ️ 缺少金额 ${deficit:.2f} < 最小补足金额 ${fund_config.replenish_min_amount:.2f}，跳过补足")
            return
        
        # 检查告警
        if fund_config.replenish_enable_alert:
            alert_threshold = fund_config.initial_capital * fund_config.replenish_alert_threshold
            if account_balance < alert_threshold:
                logger.warning(f"⚠️ 账户 {account_id} 余额 ${account_balance:.2f} < 告警阈值 ${alert_threshold:.2f}")
                # TODO: 发送告警通知
        
        # 执行补足（从现货账户转入合约账户）
        try:
            await self._transfer_from_spot_to_futures(client, deficit)
            
            # 更新累计补足金额
            fund_config.total_replenished_amount += deficit
            await self.db.commit()
            
            logger.info(f"✅ 补足成功: ${deficit:.2f}, 累计已补足: ${fund_config.total_replenished_amount:.2f}")
        
        except Exception as e:
            logger.error(f"❌ 补足失败: {e}", exc_info=True)
            await self.db.rollback()
    
    async def _handle_profit(self, account_id: int, account_balance: float, fund_config: FundConfig, client):
        """
        处理盈利情况：覆盖之前的补足金额
        
        Args:
            account_id: 账户ID
            account_balance: 当前账户余额
            fund_config: 资金管理配置
            client: 币安客户端
        """
        # 计算盈利金额
        profit = account_balance - fund_config.initial_capital
        
        # 计算可以覆盖的金额（取盈利和已补足金额的最小值）
        recoverable = min(profit, fund_config.total_replenished_amount)
        
        logger.info(f"💰 账户 {account_id} 盈利 ${profit:.2f}，可覆盖 ${recoverable:.2f}（已补足 ${fund_config.total_replenished_amount:.2f}）")
        
        if recoverable <= 0:
            logger.info(f"ℹ️ 无需覆盖")
            return
        
        # 执行覆盖（从合约账户转回现货账户）
        try:
            await self._transfer_from_futures_to_spot(client, recoverable)
            
            # 更新累计补足金额
            fund_config.total_replenished_amount -= recoverable
            await self.db.commit()
            
            logger.info(f"✅ 覆盖成功: ${recoverable:.2f}, 剩余已补足: ${fund_config.total_replenished_amount:.2f}")
            
            # 如果全部覆盖完毕
            if fund_config.total_replenished_amount == 0:
                logger.info(f"🎉 账户 {account_id} 已补足金额已全部覆盖完毕")
        
        except Exception as e:
            logger.error(f"❌ 覆盖失败: {e}", exc_info=True)
            await self.db.rollback()
    
    async def _transfer_from_spot_to_futures(self, client, amount: float):
        """
        从现货账户转入合约账户
        
        Args:
            client: 币安客户端
            amount: 转账金额
        """
        logger.info(f"🔄 执行转账: 现货 → 合约, 金额: ${amount:.2f}")
        
        # 调用币安API执行转账
        result = await client.transfer_between_accounts(
            asset='USDT',
            amount=amount,
            from_account='SPOT',
            to_account='FUTURES'
        )
        
        logger.info(f"✅ 转账成功: {result}")
    
    async def _transfer_from_futures_to_spot(self, client, amount: float):
        """
        从合约账户转回现货账户
        
        Args:
            client: 币安客户端
            amount: 转账金额
        """
        logger.info(f"🔄 执行转账: 合约 → 现货, 金额: ${amount:.2f}")
        
        # 调用币安API执行转账
        result = await client.transfer_between_accounts(
            asset='USDT',
            amount=amount,
            from_account='FUTURES',
            to_account='SPOT'
        )
        
        logger.info(f"✅ 转账成功: {result}")
