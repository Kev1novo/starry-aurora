"""会话工作区业务服务"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation_repo import ConversationRepository


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.repo = ConversationRepository(db)

    async def create_conversation(self, user_id: int, title: str, workspace_type: str = "query"):
        conv = await self.repo.create(user_id, title, workspace_type)
        return conv

    async def get_conversation(self, conv_id: int, user_id: int):
        conv = await self.repo.get(conv_id, user_id)
        if not conv:
            return None
        msg_count = await self.repo.get_message_count(conv_id)
        return conv, msg_count

    async def get_conversation_detail(self, conv_id: int, user_id: int):
        conv = await self.repo.get(conv_id, user_id)
        if not conv:
            return None
        messages = await self.repo.get_messages(conv_id)
        return conv, messages

    async def list_conversations(self, user_id: int, page: int = 1, page_size: int = 20):
        items, total = await self.repo.list_by_user(user_id, page, page_size)
        return items, total

    async def update_conversation(self, conv_id: int, user_id: int, **kwargs):
        conv = await self.repo.get(conv_id, user_id)
        if not conv:
            return None
        return await self.repo.update(conv, **kwargs)

    async def delete_conversation(self, conv_id: int, user_id: int):
        conv = await self.repo.get(conv_id, user_id)
        if not conv:
            return False
        await self.repo.delete(conv)
        return True

    async def add_message(self, conversation_id: int, user_id: int, role: str, content: str, message_type: str = "text"):
        conv = await self.repo.get(conversation_id, user_id)
        if not conv:
            return None
        msg = await self.repo.add_message(conversation_id, role, content, message_type)
        return msg

    async def get_messages(self, conversation_id: int, user_id: int):
        conv = await self.repo.get(conversation_id, user_id)
        if not conv:
            return None
        return await self.repo.get_messages(conversation_id)