"""
资金监控器 - 使用WebSocket实时监控余额并触发资金管理功能
"""
import asyncio
from typing import Dict, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.event_bus import EventBus
from core.database import get_db, Account, Instance
from core.binance_websocket import BinanceWebSocket
from plugins.fund_engine.profit_extract import ProfitExtractionEngine
from plugins.fund_engine.auto_replenish import AutoReplenishEngine


class FundMonitor:
    """
    资金监控器（WebSocket实时版本）
    
    职责：
    1. 订阅币安用户数据流
    2. 实时接收余额更新
    3. 触发盈利提取
    4. 触发自动补足余额
    5. 触发初始金额保护
    6. 触发盈利倍数终点
    
    特点：
    - 使用WebSocket实时推送，延迟 < 100ms
    - 不再使用轮询，完全事件驱动
    """
    
    def __init__(self):
        """初始化资金监控器"""
        self.event_bus = EventBus.get_instance()
        self.running = False
        
        # 为每个实例存储资金管理引擎
        self.profit_extractors: Dict[int, ProfitExtractionEngine] = {}
        self.auto_replenishers: Dict[int, AutoReplenishEngine] = {}
        
        # 为每个账户存储WebSocket客户端
        self.ws_clients: Dict[int, BinanceWebSocket] = {}
        
        # 为每个账户存储币安REST客户端
        self.binance_clients: Dict[int, any] = {}
        
        # 账户ID到实例ID列表的映射
        self.account_to_instances: Dict[int, list] = {}
        
        logger.info("✅ 资金监控器初始化完成（WebSocket实时版本）")
    
    async def start(self):
        """启动资金监控器"""
        self.running = True
        logger.info("✅ 资金监控器已启动（WebSocket实时推送）")
    
    async def stop(self):
        """停止资金监控器"""
        self.running = False
        
        # 关闭所有WebSocket连接
        for account_id, ws_client in self.ws_clients.items():
            await ws_client.disconnect()
            logger.info(f"🛑 关闭账户 {account_id} 的WebSocket连接")
        
        self.ws_clients.clear()
        logger.info("🛑 资金监控器已停止")
    
    async def load_manager_for_instance(self, instance_id: int, db: AsyncSession):
        """
        为指定实例加载资金管理引擎并订阅WebSocket
        
        Args:
            instance_id: 实例ID
            db: 数据库会话
        """
        try:
            # 查询实例
            result = await db.execute(select(Instance).where(Instance.id == instance_id))
            instance = result.scalar_one_or_none()
            if not instance:
                logger.error(f"❌ 实例 {instance_id} 不存在")
                return
            
            account_id = instance.account_id
            
            # 查询账户
            result = await db.execute(select(Account).where(Account.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                logger.error(f"❌ 账户 {account_id} 不存在")
                return
            
            # 初始化币安REST客户端
            if account_id not in self.binance_clients:
                from core.binance_client import BinanceClient
                self.binance_clients[account_id] = BinanceClient(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet,
                    proxy=account.proxy_config  # 添加代理配置
                )
                logger.info(f"✅ 为账户 {account_id} 初始化币安REST客户端")
            
            # P0修复: 资金管理配置应该从 FundConfig 表读取，而不是 Instance 表
            # 查询账户的资金管理配置
            from core.database import FundConfig
            fund_config_result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
            fund_config = fund_config_result.scalar_one_or_none()
            
            if fund_config:
                # 初始化盈利提取引擎（如果启用）
                if fund_config.extraction_mode:
                    extract_config = {
                        "mode": fund_config.extraction_mode,
                        "threshold": fund_config.threshold,
                        "multiple": fund_config.multiple,
                        "initial_capital": fund_config.initial_capital
                    }
                    self.profit_extractors[instance_id] = ProfitExtractionEngine(extract_config)
                    logger.info(f"✅ 为实例 {instance_id} 初始化盈利提取引擎")
                
                # 初始化自动补足引擎（如果启用）
                if fund_config.enable_replenish:
                    replenish_config = {
                        "initial_capital": fund_config.initial_capital,
                        "min_transfer_amount": fund_config.replenish_min_amount,
                        "enable_alert": fund_config.replenish_enable_alert,
                        "alert_threshold": fund_config.replenish_alert_threshold,
                        "max_replenish_per_day": fund_config.replenish_max_per_day
                    }
                    self.auto_replenishers[instance_id] = AutoReplenishEngine(replenish_config)
                    logger.info(f"✅ 为实例 {instance_id} 初始化自动补足引擎")
            
            # 初始化WebSocket客户端（每个账户一个）
            if account_id not in self.ws_clients:
                ws_client = BinanceWebSocket(
                    api_key=account.api_key,
                    api_secret=account.api_secret,
                    testnet=account.testnet
                )
                
                # 连接WebSocket
                await ws_client.connect()
                
                # 设置余额更新回调
                ws_client.set_account_update_callback(
                    lambda data: self._on_account_update(account_id, data)
                )
                
                # 订阅用户数据流
                await ws_client.subscribe_user_data_stream()
                
                self.ws_clients[account_id] = ws_client
                logger.info(f"✅ 为账户 {account_id} 初始化WebSocket客户端并订阅用户数据流")
            
            # 记录账户到实例的映射
            if account_id not in self.account_to_instances:
                self.account_to_instances[account_id] = []
            if instance_id not in self.account_to_instances[account_id]:
                self.account_to_instances[account_id].append(instance_id)
            
            logger.info(f"✅ 为实例 {instance_id} 加载资金监控器完成（WebSocket实时推送）")
            
        except Exception as e:
            logger.error(f"❌ 为实例 {instance_id} 加载资金管理引擎失败: {e}")
            raise
    
    async def _on_account_update(self, account_id: int, data: dict):
        """
        处理余额更新（WebSocket回调）
        
        Args:
            account_id: 账户ID
            data: 余额更新数据
                {
                    "asset": "USDT",
                    "wallet_balance": 10000.0,
                    "cross_wallet_balance": 9500.0,
                    "balance_change": 100.0,
                    "timestamp": 1638747660000
                }
        """
        try:
            asset = data.get("asset")
            wallet_balance = data.get("wallet_balance")
            cross_wallet_balance = data.get("cross_wallet_balance")
            balance_change = data.get("balance_change")
            
            # 只处理USDT余额
            if asset != "USDT":
                return
            
            logger.info(f"💰 收到余额更新: 账户={account_id}, 钱包={wallet_balance}, 合约={cross_wallet_balance}, 变化={balance_change}")
            
            # 查找该账户下的所有实例
            instance_ids = self.account_to_instances.get(account_id, [])
            
            # 获取数据库会话
            async for db in get_db():
                try:
                    # 检查每个实例的资金管理规则
                    for instance_id in instance_ids:
                        await self._check_fund_management(
                            instance_id=instance_id,
                            account_id=account_id,
                            wallet_balance=wallet_balance,
                            cross_wallet_balance=cross_wallet_balance,
                            db=db
                        )
                
                finally:
                    await db.close()
                break
            
        except Exception as e:
            logger.error(f"❌ 处理余额更新失败: {e}")
    
    async def _check_fund_management(self, instance_id: int, account_id: int,
                                    wallet_balance: float, cross_wallet_balance: float,
                                    db: AsyncSession):
        """
        检查资金管理规则（账户级别）
        
        Args:
            instance_id: 实例ID
            account_id: 账户ID
            wallet_balance: 钱包余额
            cross_wallet_balance: 合约余额
            db: 数据库会话
        """
        try:
            # 查询资金管理配置（账户级别）
            from core.database import FundConfig
            result = await db.execute(select(FundConfig).where(FundConfig.account_id == account_id))
            fund_config = result.scalar_one_or_none()
            if not fund_config:
                return
            
            # 获取币安客户端
            if account_id not in self.binance_clients:
                return
            
            client = self.binance_clients[account_id]
            
            # 1. 检查盈利提取
            if fund_config.extraction_mode and instance_id in self.profit_extractors:
                await self._check_profit_extract(
                    fund_config=fund_config,
                    wallet_balance=wallet_balance,
                    client=client,
                    db=db
                )
            
            # 2. 检查自动补足
            if fund_config.enable_replenish and instance_id in self.auto_replenishers:
                await self._check_auto_replenish(
                    fund_config=fund_config,
                    cross_wallet_balance=cross_wallet_balance,
                    client=client,
                    db=db
                )
            
            # 3. 检查初始金额保护
            if fund_config.enable_initial_protect:
                await self._check_initial_protect(
                    fund_config=fund_config,
                    wallet_balance=wallet_balance,
                    client=client,
                    db=db
                )
            
            # 4. 检查盈利倍数终点
            if fund_config.enable_endpoint:
                await self._check_profit_endpoint(
                    fund_config=fund_config,
                    wallet_balance=wallet_balance,
                    client=client,
                    db=db
                )
            
        except Exception as e:
            logger.error(f"❌ 检查账户 {account_id} 资金管理失败: {e}")
    
    async def _check_profit_extract(self, fund_config, wallet_balance: float,
                                   client: any, db: AsyncSession):
        """检查盈利提取"""
        try:
            # 根据提取模式计算
            if fund_config.extraction_mode == "wallet_threshold":
                # 钱包阈值模式
                if wallet_balance >= fund_config.threshold:
                    extract_amount = wallet_balance - fund_config.initial_capital
                    
                    if extract_amount > 0:
                        logger.info(f"💰 盈利提取触发(阈值模式): 账户={fund_config.account_id}, 金额={extract_amount}")
                        
                        # 执行划转
                        try:
                            transfer_result = await client.transfer_between_accounts(
                                asset="USDT",
                                amount=extract_amount,
                                from_account="FUTURES",
                                to_account="SPOT"
                            )
                            
                            logger.info(f"✅ 盈利提取成功: {transfer_result}")
                            
                            # 如果是阶段复利模式，重置复利起点
                            if fund_config.compounding_mode == "stage":
                                fund_config.current_base = fund_config.initial_capital
                                await db.commit()
                                logger.info(f"📈 阶段复利重置: current_base → {fund_config.initial_capital}")
                            
                            # 发布事件
                            await self.event_bus.publish(
                                f"fund:profit_extracted:{fund_config.account_id}",
                                {
                                    "account_id": fund_config.account_id,
                                    "amount": extract_amount,
                                    "mode": "wallet_threshold"
                                }
                            )
                            
                        except Exception as e:
                            logger.error(f"❌ 盈利提取失败: {e}")
            
            elif fund_config.extraction_mode == "multiple_mode":
                # 倍数模式
                threshold = fund_config.initial_capital * fund_config.multiple
                if wallet_balance >= threshold:
                    extract_amount = wallet_balance - fund_config.initial_capital
                    
                    if extract_amount > 0:
                        logger.info(f"💰 盈利提取触发(倍数模式): 账户={fund_config.account_id}, 金额={extract_amount}")
                        
                        # 执行划转
                        try:
                            transfer_result = await client.transfer_between_accounts(
                                asset="USDT",
                                amount=extract_amount,
                                from_account="FUTURES",
                                to_account="SPOT"
                            )
                            
                            logger.info(f"✅ 盈利提取成功: {transfer_result}")
                            
                            # 如果是阶段复利模式，重置复利起点
                            if fund_config.compounding_mode == "stage":
                                fund_config.current_base = fund_config.initial_capital
                                await db.commit()
                                logger.info(f"📈 阶段复利重置: current_base → {fund_config.initial_capital}")
                            
                            # 发布事件
                            await self.event_bus.publish(
                                f"fund:profit_extracted:{fund_config.account_id}",
                                {
                                    "account_id": fund_config.account_id,
                                    "amount": extract_amount,
                                    "mode": "multiple_mode"
                                }
                            )
                            
                        except Exception as e:
                            logger.error(f"❌ 盈利提取失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 盈利提取检查失败: {e}")
    
    async def _check_auto_replenish(self, fund_config, cross_wallet_balance: float,
                                   client: any, db: AsyncSession):
        """检查自动补足"""
        try:
            # 计算阈值
            threshold = fund_config.initial_capital * fund_config.replenish_alert_threshold
            
            # 如果余额低于阈值
            if cross_wallet_balance < threshold:
                # 计算补足金额
                replenish_amount = fund_config.initial_capital - cross_wallet_balance
                
                # 检查最小转账金额
                if replenish_amount < fund_config.replenish_min_amount:
                    return
                
                logger.info(f"💰 自动补足触发: 账户={fund_config.account_id}, 金额={replenish_amount}")
                
                # 执行划转
                try:
                    transfer_result = await client.transfer_between_accounts(
                        asset="USDT",
                        amount=replenish_amount,
                        from_account="SPOT",  # 从现货账户
                        to_account="FUTURES"  # 转到合约账户
                    )
                    
                    logger.info(f"✅ 自动补足成功: {transfer_result}")
                    
                    # 发布事件
                    await self.event_bus.publish(
                        f"fund:auto_replenished:{fund_config.account_id}",
                        {
                            "account_id": fund_config.account_id,
                            "amount": replenish_amount
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"❌ 自动补足失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 自动补足检查失败: {e}")
    
    async def _check_initial_protect(self, fund_config, wallet_balance: float,
                                    client: any, db: AsyncSession):
        """检查初始金额保护（重新实现）"""
        try:
            # 检查是否达到最大保护次数
            if fund_config.protect_count >= fund_config.max_protect_count:
                # 已达到最大次数，自动禁用保护
                if fund_config.enable_initial_protect:
                    fund_config.enable_initial_protect = False
                    await db.commit()
                    logger.info(f"🛡️ 初始金额保护已达到最大次数({fund_config.max_protect_count})，自动禁用")
                return
            
            # 计算保护阈值
            if fund_config.protect_count == 0:
                # 第1次触发点 = 初始投入金额 × 保护倍数
                protect_threshold = fund_config.initial_capital * fund_config.protect_multiplier
            else:
                # 第N次触发点 = 上次保护后的余额 + 初始投入金额
                protect_threshold = fund_config.last_protect_balance + fund_config.initial_capital
            
            # 如果余额达到保护阈值
            if wallet_balance >= protect_threshold:
                # 每次转移固定金额 = 初始投入金额
                extract_amount = fund_config.initial_capital
                
                logger.info(f"🛡️ 初始金额保护触发: 账户={fund_config.account_id}, 提取={extract_amount}, 第{fund_config.protect_count + 1}次")
                
                # 执行划转
                try:
                    transfer_result = await client.transfer_between_accounts(
                        asset="USDT",
                        amount=extract_amount,
                        from_account="FUTURES",
                        to_account="SPOT"  # 转到现货账户
                    )
                    
                    logger.info(f"✅ 初始金额保护提取成功: {transfer_result}")
                    
                    # 更新触发次数和余额
                    fund_config.protect_count += 1
                    fund_config.last_protect_balance = wallet_balance - extract_amount
                    
                    # 检查是否达到最大次数
                    if fund_config.protect_count >= fund_config.max_protect_count:
                        fund_config.enable_initial_protect = False
                        logger.info(f"🛡️ 初始金额保护已达到最大次数({fund_config.max_protect_count})，自动禁用")
                    
                    await db.commit()
                    
                    # 发布事件
                    await self.event_bus.publish(
                        f"fund:initial_protected:{fund_config.account_id}",
                        {
                            "account_id": fund_config.account_id,
                            "amount": extract_amount,
                            "protect_multiplier": fund_config.protect_multiplier,
                            "count": fund_config.protect_count,
                            "last_balance": fund_config.last_protect_balance
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"❌ 初始金额保护提取失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 初始金额保护检查失败: {e}")
    
    async def _check_profit_endpoint(self, fund_config, wallet_balance: float,
                                    client: any, db: AsyncSession):
        """检查盈利倍数终点（重新实现）"""
        try:
            # 计算终点阈值 = 初始投入金额 × 终点倍数
            endpoint_threshold = fund_config.initial_capital * fund_config.endpoint_multiplier
            
            # 如果余额达到终点阈值
            if wallet_balance >= endpoint_threshold:
                # 计算提取金额 = 当前余额 - 初始投入金额
                extract_amount = wallet_balance - fund_config.initial_capital
                
                if extract_amount > 0:
                    logger.info(f"🏁 盈利倍数终点触发: 账户={fund_config.account_id}, 提取={extract_amount}")
                    
                    # 执行划转
                    try:
                        transfer_result = await client.transfer_between_accounts(
                            asset="USDT",
                            amount=extract_amount,
                            from_account="FUTURES",
                            to_account="SPOT"  # 转到现货账户
                        )
                        
                        logger.info(f"✅ 盈利倍数终点提取成功: {transfer_result}")
                        
                        # 更新触发次数（循环执行，不停止实例）
                        fund_config.endpoint_count += 1
                        await db.commit()
                        
                        logger.info(f"✅ 盈利倍数终点提取成功（第{fund_config.endpoint_count}次），继续交易")
                        
                        # 发布事件
                        await self.event_bus.publish(
                            f"fund:profit_endpoint_reached:{fund_config.account_id}",
                            {
                                "account_id": fund_config.account_id,
                                "amount": extract_amount,
                                "endpoint_multiplier": fund_config.endpoint_multiplier,
                                "count": fund_config.endpoint_count
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ 盈利倍数终点提取失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 盈利倍数终点检查失败: {e}")


# 全局资金监控器实例
fund_monitor = FundMonitor()
