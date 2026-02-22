"""
交易对管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from loguru import logger
import ccxt
import asyncio

router = APIRouter()


class SymbolInfo(BaseModel):
    """交易对信息"""
    symbol: str
    base_currency: str
    quote_currency: str
    contract_type: str  # "perpetual" | "future"
    is_active: bool


class ExchangeSymbolsResponse(BaseModel):
    """交易所交易对响应"""
    exchange: str
    total_count: int
    symbols: List[SymbolInfo]


# 缓存交易对数据(避免频繁请求交易所)
_symbols_cache = {}


@router.get("/exchanges/{exchange}/symbols", response_model=ExchangeSymbolsResponse)
async def get_exchange_symbols(
    exchange: str,
    contract_type: str = "perpetual",
    quote_currency: str = "USDT",
    force_refresh: bool = False
):
    """
    获取交易所的交易对列表
    
    参数:
    - exchange: 交易所名称 (binance, okx, bybit等)
    - contract_type: 合约类型 (perpetual=永续合约, future=交割合约)
    - quote_currency: 计价货币 (USDT, BUSD等)
    - force_refresh: 是否强制刷新缓存
    """
    try:
        cache_key = f"{exchange}_{contract_type}_{quote_currency}"
        
        # 检查缓存
        if not force_refresh and cache_key in _symbols_cache:
            logger.info(f"✅ 从缓存返回 {exchange} 交易对列表")
            return _symbols_cache[cache_key]
        
        # 创建交易所实例
        exchange_class = getattr(ccxt, exchange.lower(), None)
        if not exchange_class:
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        exchange_instance = exchange_class({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap' if contract_type == 'perpetual' else 'future'
            }
        })
        
        # 异步加载市场数据
        loop = asyncio.get_event_loop()
        markets = await loop.run_in_executor(None, exchange_instance.load_markets)
        
        # 过滤交易对
        symbols_list = []
        for symbol, market in markets.items():
            # 只保留指定计价货币的永续/交割合约
            if market.get('quote') == quote_currency:
                # 检查合约类型
                market_type = market.get('type', '')
                is_perpetual = market.get('swap', False) or 'perpetual' in market_type.lower()
                is_future = market.get('future', False) or 'future' in market_type.lower()
                
                if contract_type == 'perpetual' and is_perpetual:
                    symbols_list.append(SymbolInfo(
                        symbol=symbol,
                        base_currency=market.get('base', ''),
                        quote_currency=market.get('quote', ''),
                        contract_type='perpetual',
                        is_active=market.get('active', True)
                    ))
                elif contract_type == 'future' and is_future:
                    symbols_list.append(SymbolInfo(
                        symbol=symbol,
                        base_currency=market.get('base', ''),
                        quote_currency=market.get('quote', ''),
                        contract_type='future',
                        is_active=market.get('active', True)
                    ))
        
        # 按symbol排序
        symbols_list.sort(key=lambda x: x.symbol)
        
        # 构建响应
        response = ExchangeSymbolsResponse(
            exchange=exchange,
            total_count=len(symbols_list),
            symbols=symbols_list
        )
        
        # 缓存结果
        _symbols_cache[cache_key] = response
        
        logger.info(f"✅ 获取 {exchange} 交易对列表成功: {len(symbols_list)} 个")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取交易对列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取交易对列表失败: {str(e)}")


@router.post("/exchanges/{exchange}/symbols/refresh")
async def refresh_exchange_symbols(exchange: str):
    """刷新交易所交易对缓存"""
    try:
        # 清除该交易所的所有缓存
        keys_to_remove = [key for key in _symbols_cache.keys() if key.startswith(f"{exchange}_")]
        for key in keys_to_remove:
            del _symbols_cache[key]
        
        logger.info(f"✅ 已清除 {exchange} 的交易对缓存")
        
        return {"message": f"缓存已清除,下次请求将重新获取", "cleared_count": len(keys_to_remove)}
        
    except Exception as e:
        logger.error(f"❌ 刷新缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}")
