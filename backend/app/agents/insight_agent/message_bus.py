"""
消息转换与持久化模块
负责消息序列化、通过消息队列（Celery/Redis）持久化、以及事件发布。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.core.celery_app import celery_app

# ---------- 枚举 ----------


class MessagePriority(str, Enum):
    """消息优先级"""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MessageStatus(str, Enum):
    """消息处理状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    """事件类型枚举"""

    # 查询流程
    QUERY_STARTED = "query.started"
    QUERY_COMPLETED = "query.completed"
    QUERY_FAILED = "query.failed"
    QUERY_CANCELLED = "query.cancelled"

    # 归因流程
    ATTRIBUTION_STARTED = "attribution.started"
    ATTRIBUTION_COMPLETED = "attribution.completed"
    ATTRIBUTION_FAILED = "attribution.failed"

    # 工作区
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_UPDATED = "workspace.updated"
    WORKSPACE_DELETED = "workspace.deleted"

    # 附件
    ATTACHMENT_READY = "attachment.ready"
    ATTACHMENT_EXPIRED = "attachment.expired"

    # 系统
    SYSTEM_NOTIFICATION = "system.notification"
    ERROR_OCCURRED = "error.occurred"


# ---------- Pydantic 模型 ----------


class MessagePayload(BaseModel):
    """消息载荷的通用结构"""

    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType
    source: str = "insight_agent"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING


class EventEnvelope(BaseModel):
    """事件信封——用于发布到事件总线的外部格式"""

    event_id: str
    event_type: str
    version: str = "1.0"
    published_at: str
    source: str
    subject: Optional[str] = None
    data: dict[str, Any]
    data_schema: Optional[str] = Field(default=None, alias="data-schema")


# ---------- 消息总线 ----------


class MessageBus:
    """
    消息转换与持久化总线

    职责：
        1. 构建标准化的消息载荷（MessagePayload）
        2. 通过 Celery 任务异步持久化消息
        3. 通过 Redis 发布/订阅模式推送事件
        4. 消息 ID 去重与状态跟踪
    """

    # Redis 键前缀
    _QUEUE_PREFIX = "starry:messages:queue"
    _EVENT_PREFIX = "starry:messages:event"
    _HISTORY_PREFIX = "starry:messages:history"

    def __init__(self, redis: Optional[Redis] = None) -> None:
        self._redis = redis

    # ---------- 消息构建 ----------

    def build_message(
        self,
        event_type: EventType,
        data: dict[str, Any],
        *,
        user_id: Optional[int] = None,
        conversation_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        source: str = "insight_agent",
    ) -> MessagePayload:
        """
        构建标准化的消息载荷。

        Args:
            event_type: 事件类型
            data: 事件数据
            user_id: 关联用户 ID（可选）
            conversation_id: 关联会话 ID（可选）
            priority: 消息优先级
            source: 消息来源标识

        Returns:
            标准化的 MessagePayload 实例
        """
        return MessagePayload(
            event_type=event_type,
            source=source,
            user_id=user_id,
            conversation_id=conversation_id,
            data=data,
            priority=priority,
        )

    # ---------- 消息持久化（Celery） ----------

    async def dispatch_task(self, message: MessagePayload, task_name: str = "") -> str:
        """
        通过 Celery 异步派发消息任务。

        将消息序列化为 JSON 后发送到 Celery broker，
        由对应 worker 消费处理。

        Args:
            message: 消息载荷
            task_name: Celery 任务名称（空字符串时使用默认路由）

        Returns:
            Celery 异步任务 ID（AsyncResult.id）
        """
        payload = message.model_dump(mode="json")
        task_kwargs: dict[str, Any] = {"payload": payload}

        task = celery_app.send_task(
            name=task_name or "process_insight_message",
            kwargs=task_kwargs,
            priority=self._celery_priority(message.priority),
        )
        return task.id

    # ---------- 事件发布（Redis Pub/Sub） ----------

    async def publish_event(self, message: MessagePayload) -> int:
        """
        通过 Redis 发布事件到事件总线。

        事件被发布到 `starry:events:<event_type>` 频道，
        订阅者可以实时接收通知。

        Args:
            message: 消息载荷

        Returns:
            接收到事件的订阅者数量

        Raises:
            RuntimeError: Redis 连接未初始化
        """
        if self._redis is None:
            raise RuntimeError("Redis 连接未初始化，请先调用 set_redis 注入 Redis 实例")

        envelope = self._build_envelope(message)
        channel = f"{self._EVENT_PREFIX}:{message.event_type.value}"
        serialized = envelope.model_dump_json(by_alias=True)
        count = await self._redis.publish(channel, serialized)
        return count

    async def store_message(self, message: MessagePayload) -> None:
        """
        将消息持久化到 Redis 列表（用作操作历史）。

        Args:
            message: 消息载荷

        Raises:
            RuntimeError: Redis 连接未初始化
        """
        if self._redis is None:
            raise RuntimeError("Redis 连接未初始化")

        payload = message.model_dump(mode="json")
        key = f"{self._HISTORY_PREFIX}:{message.event_type.value}"

        pipeline = self._redis.pipeline()
        pipeline.lpush(key, json.dumps(payload, ensure_ascii=False))
        pipeline.ltrim(key, 0, 999)  # 每个事件类型保留最近 1000 条
        await pipeline.execute()

    async def get_history(
        self,
        event_type: EventType,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        获取指定事件类型的历史消息。

        Args:
            event_type: 事件类型
            limit: 返回条数上限
            offset: 偏移量

        Returns:
            消息字典列表（按时间倒序）
        """
        if self._redis is None:
            return []

        key = f"{self._HISTORY_PREFIX}:{event_type.value}"
        raw_messages = await self._redis.lrange(key, offset, offset + limit - 1)
        results: list[dict[str, Any]] = []
        for raw in raw_messages:
            try:
                results.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue
        return results

    # ---------- 依赖注入 ----------

    def set_redis(self, redis: Redis) -> None:
        """注入 Redis 客户端实例"""
        self._redis = redis

    # ---------- 私有方法 ----------

    @staticmethod
    def _build_envelope(message: MessagePayload) -> EventEnvelope:
        """将内部消息载荷转换为外部事件信封格式"""
        return EventEnvelope(
            event_id=message.message_id,
            event_type=message.event_type.value,
            published_at=message.timestamp.isoformat(),
            source=message.source,
            subject=f"user_{message.user_id}" if message.user_id else None,
            data=message.data,
        )

    @staticmethod
    def _celery_priority(priority: MessagePriority) -> int:
        """将 MessagePriority 转换为 Celery 优先级数值（0 最高）"""
        mapping = {
            MessagePriority.HIGH: 0,
            MessagePriority.NORMAL: 5,
            MessagePriority.LOW: 9,
        }
        return mapping[priority]


# ---------- Convenience 函数 ----------


async def dispatch_event(
    event_type: EventType,
    data: dict[str, Any],
    *,
    user_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
    redis: Optional[Redis] = None,
    persist: bool = True,
) -> str:
    """
    便捷函数：一条调用同时构建、持久化并发布事件。

    Args:
        event_type: 事件类型
        data: 事件数据
        user_id: 关联用户 ID
        conversation_id: 关联会话 ID
        redis: Redis 客户端（用于发布事件）
        persist: 是否持久化到历史

    Returns:
        消息 ID
    """
    bus = MessageBus(redis=redis)
    message = bus.build_message(
        event_type=event_type,
        data=data,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    # 持久化到历史
    if persist and redis is not None:
        await bus.store_message(message)

    # 发布事件
    if redis is not None:
        await bus.publish_event(message)

    # 派发 Celery 任务
    await bus.dispatch_task(message)

    return message.message_id