"""会话工作区数据访问"""
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, title: str, workspace_type: str = "query") -> Conversation:
        conv = Conversation(user_id=user_id, title=title, workspace_type=workspace_type)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def get(self, conv_id: int, user_id: int) -> Conversation | None:
        stmt = select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int, page: int = 1, page_size: int = 20) -> tuple[list[Conversation], int]:
        base = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(base.offset(offset).limit(page_size))
        return list(result.scalars().all()), total

    async def update(self, conv: Conversation, **kwargs) -> Conversation:
        for k, v in kwargs.items():
            if v is not None:
                setattr(conv, k, v)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def delete(self, conv: Conversation) -> None:
        await self.db.delete(conv)

    async def add_message(self, conversation_id: int, role: str, content: str, message_type: str = "text") -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id, role=role, content=content, message_type=message_type
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, conversation_id: int) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_message_count(self, conversation_id: int) -> int:
        stmt = select(func.count()).where(ConversationMessage.conversation_id == conversation_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0