"""
数据源服务层
封装数据源的创建、测试连接、更新、删除等业务逻辑，以及密码加解密。
"""

import time
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import decrypt_password, encrypt_password
from app.models.datasource import DataSource
from app.repositories.datasource_repo import DataSourceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)


class DataSourceService:
    """
    数据源服务

    处理数据源的完整生命周期管理，包括 CRUD、连接测试和密码加密存储。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.repo = DataSourceRepository(db)

    async def create(self, uid: int, data: DataSourceCreate) -> DataSource:
        """
        创建数据源

        校验名称唯一性，对密码进行加密存储后写入数据库。

        Args:
            uid: 当前用户 ID
            data: 创建数据源请求体

        Returns:
            新创建的数据源实例

        Raises:
            ValidationException: 名称已存在
        """
        existing = await self.repo.get_by_name(data.name)
        if existing is not None:
            raise ValidationException(
                detail=f"数据源名称 '{data.name}' 已被占用",
                code="DATASOURCE_NAME_EXISTS",
            )

        create_data: Dict[str, Any] = data.model_dump()
        create_data["password"] = encrypt_password(data.password)
        create_data["user_id"] = uid

        datasource = await self.repo.create(create_data)
        return datasource

    async def test_connection(
        self, data: TestConnectionRequest
    ) -> TestConnectionResponse:
        """
        测试数据库连接

        根据请求参数尝试建立数据库连接并执行 SELECT 1，记录连接延迟。

        Args:
            data: 测试连接请求体

        Returns:
            连接测试结果，包含成功状态、消息和延迟时间
        """
        start_time = time.perf_counter()
        try:
            if data.port == 5432:
                # PostgreSQL — 使用 asyncpg
                import asyncpg

                conn = await asyncpg.connect(
                    host=data.host,
                    port=data.port,
                    user=data.username,
                    password=data.password,
                    database=data.database_name,
                    timeout=10,
                )
                await conn.fetchval("SELECT 1")
                await conn.close()
            elif data.port == 9000 or "clickhouse" in str(data).lower():
                # ClickHouse — 使用 aiohttp 请求
                import aiohttp

                url = (
                    f"http://{data.host}:{data.port}"
                    f"/?query=SELECT+1&user={data.username}&password={data.password}"
                    f"&database={data.database_name}"
                )
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            return TestConnectionResponse(
                                success=False,
                                message=f"ClickHouse 连接失败: {text[:200]}",
                            )
            else:
                # MySQL / 其它 — 使用 aiomysql
                import aiomysql

                pool = await aiomysql.create_pool(
                    host=data.host,
                    port=data.port,
                    user=data.username,
                    password=data.password,
                    db=data.database_name,
                    minsize=1,
                    maxsize=1,
                    connect_timeout=10,
                )
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()
                pool.close()
                await pool.wait_closed()

            elapsed = (time.perf_counter() - start_time) * 1000
            return TestConnectionResponse(
                success=True,
                message="连接成功",
                latency_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            return TestConnectionResponse(
                success=False,
                message=f"连接失败: {str(e)[:200]}",
                latency_ms=round(elapsed, 2),
            )

    async def get_datasource(self, uid: int, ds_id: int) -> DataSource:
        """
        获取指定数据源详情（校验所属用户）

        Args:
            uid: 当前用户 ID
            ds_id: 数据源 ID

        Returns:
            数据源实例

        Raises:
            NotFoundException: 数据源不存在或不属于当前用户
        """
        datasource = await self.repo.get(ds_id)
        if datasource is None or datasource.user_id != uid:
            raise NotFoundException(detail=f"数据源 {ds_id} 不存在")
        return datasource

    async def list_datasources(
        self, uid: int, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[DataSourceResponse]:
        """
        获取当前用户的数据源列表（分页）

        Args:
            uid: 当前用户 ID
            page: 页码，从 1 开始
            page_size: 每页条数

        Returns:
            分页的数据源响应
        """
        skip = (page - 1) * page_size
        items = await self.repo.list_by_user(uid, skip=skip, limit=page_size)
        total = await self.repo.count_by_user(uid)
        return PaginatedResponse(
            items=[DataSourceResponse.model_validate(ds) for ds in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(self, uid: int, ds_id: int, data: DataSourceUpdate) -> DataSource:
        """
        更新数据源信息

        若更新名称则校验唯一性; 若包含新密码则重新加密

        Args:
            uid: 当前用户 ID
            ds_id: 数据源 ID
            data: 更新数据

        Returns:
            更新后的数据源实例

        Raises:
            NotFoundException: 数据源不存在或不属于当前用户
            ValidationException: 新名称已被占用
        """
        datasource = await self.repo.get(ds_id)
        if datasource is None or datasource.user_id != uid:
            raise NotFoundException(detail=f"数据源 {ds_id} 不存在")

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != datasource.name:
            existing = await self.repo.get_by_name(update_data["name"])
            if existing is not None:
                raise ValidationException(
                    detail=f"数据源名称 '{update_data['name']}' 已被占用",
                    code="DATASOURCE_NAME_EXISTS",
                )

        if "password" in update_data:
            update_data["password"] = encrypt_password(update_data["password"])

        datasource = await self.repo.update(ds_id, update_data)
        return datasource  # type: ignore[return-value]

    async def delete(self, uid: int, ds_id: int) -> None:
        """
        删除数据源

        Args:
            uid: 当前用户 ID
            ds_id: 数据源 ID

        Raises:
            NotFoundException: 数据源不存在或不属于当前用户
        """
        datasource = await self.repo.get(ds_id)
        if datasource is None or datasource.user_id != uid:
            raise NotFoundException(detail=f"数据源 {ds_id} 不存在")
        await self.repo.delete(ds_id)