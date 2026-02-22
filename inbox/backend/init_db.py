"""
数据库初始化脚本
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from core.database import Base, DATABASE_URL

async def init_database():
    """初始化数据库"""
    print("🔧 开始初始化数据库...")
    
    # 创建异步引擎
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    try:
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ 数据库初始化成功！")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise
    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
