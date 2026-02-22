"""
交易机器人后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from core.event_bus import EventBus
from core.database import init_database
from core.plugin_loader import get_plugin_loader
from api import accounts, strategies, instances, system, orders, positions, notifications, websocket
from api import fund_manager, symbols  # 新增: 导入资金管理和交易对API
from core.websocket_manager import init_websocket_manager, get_websocket_manager

# 导入新的执行层组件
from core.trade_executor import trade_executor
from core.fund_monitor import fund_monitor
from core.risk_monitor import risk_monitor
from plugins.data_source.market_data import MarketDataSource
from core.strategy_manager import strategy_manager
from core.order_monitor import order_monitor
from core.websocket_event_bridge import websocket_event_bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 交易机器人系统启动中...")
    
    # 初始化数据库
    await init_database()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化事件总线
    event_bus = EventBus.get_instance()
    await event_bus.start()
    logger.info("✅ 事件总线启动完成")
    
    # 初始化WebSocket管理器
    ws_manager = init_websocket_manager(event_bus)
    await ws_manager.start()
    logger.info("✅ WebSocket管理器启动完成")
    
    # 启动策略管理器
    await strategy_manager.start()
    logger.info("✅ 策略管理器启动完成")
    
    # 启动交易执行协调器
    await trade_executor.start()
    logger.info("✅ 交易执行协调器启动完成")
    
    # 启动资金监控器
    await fund_monitor.start()
    logger.info("✅ 资金监控器启动完成")
    
    # 启动风控监控器
    await risk_monitor.start()
    logger.info("✅ 风控监控器启动完成")
    
    # 启动订单监控器
    await order_monitor.start()
    logger.info("✅ 订单监控器启动完成")
    
    # 加载并启动所有插件
    plugin_loader = get_plugin_loader()
    
    # 插件配置
    plugin_configs = {
        'data_source': {
            'exchange': 'binance',
            # 'proxy': {'host': '127.0.0.1', 'port': 7890}  # 可选：代理配置
        },
        'fund_manager': {},
        'risk_engine': {},
        'execution_engine': {},
        'notification_engine': {}
    }
    
    # 加载插件
    plugins = plugin_loader.load_all_plugins(event_bus, plugin_configs)
    logger.info(f"✅ 已加载{len(plugins)}个插件")
    
    # 启动插件
    await plugin_loader.start_all_plugins()
    logger.info("✅ 所有插件已启动")
    
    logger.info("🎉 系统启动完成，准备接收请求")
    
    yield
    
    # 停止所有监控器
    await fund_monitor.stop()
    await risk_monitor.stop()
    logger.info("✅ 所有监控器已停止")
    
    # 停止所有插件
    plugin_loader = get_plugin_loader()
    await plugin_loader.stop_all_plugins()
    logger.info("✅ 所有插件已停止")
    
    # 关闭事件总线
    await event_bus.stop()
    logger.info("👋 系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="交易机器人API",
    description="专业级量化交易机器人系统",
    version="1.0.1",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册幂等性中间件（防止重复下单）
from core.idempotency import IdempotencyMiddleware
from core.database import async_session_maker
app.add_middleware(IdempotencyMiddleware, db_session_factory=async_session_maker)
logger.info("✅ 幂等性中间件已注册")

# 注册路由
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["账户管理"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["策略管理"])
app.include_router(instances.router, prefix="/api/v1/instances", tags=["实例管理"])
app.include_router(orders.router, prefix="/api/v1", tags=["订单管理"])
app.include_router(positions.router, prefix="/api/v1", tags=["持仓管理"])
app.include_router(notifications.router, prefix="/api/v1", tags=["通知管理"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(websocket.router, tags=["WebSocket"])

# 新增: 注册资金管理和交易对API路由
app.include_router(fund_manager.router, prefix="/api/fund-manager", tags=["资金管理"])
app.include_router(symbols.router, prefix="/api/symbols", tags=["交易对管理"])


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "service": "trading-bot-backend",
        "version": "1.0.1",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    try:
        # 检查Redis连接
        event_bus = EventBus.get_instance()
        redis_healthy = event_bus.redis_client is not None
        
        # 检查WebSocket管理器
        try:
            ws_manager = get_websocket_manager()
            ws_healthy = ws_manager is not None
            active_connections = len(ws_manager.active_connections) if ws_healthy else 0
        except:
            ws_healthy = False
            active_connections = 0
        
        return {
            "status": "healthy",
            "redis": "connected" if redis_healthy else "disconnected",
            "websocket": "ready" if ws_healthy else "not_ready",
            "active_ws_connections": active_connections
        }
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
