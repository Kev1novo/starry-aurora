"""
测试数据填充脚本
创建示例用户、数据源和触点数据，方便开发调试

用法: python scripts/seed_data.py
"""
import asyncio


async def seed():
    from app.core.database import async_session_factory
    from app.core.security import hash_password
    from app.models.user import User

    db_gen = async_session_factory()
    db = await db_gen.__anext__()

    try:
        # 创建 admin 用户
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin)

        # 创建 analyst 用户
        analyst = User(
            username="analyst",
            email="analyst@example.com",
            hashed_password=hash_password("analyst123"),
            role="analyst",
            is_active=True,
        )
        db.add(analyst)

        await db.commit()
        print(f"Created users: admin, analyst")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(seed())