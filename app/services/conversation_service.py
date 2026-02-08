import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.conversation import Conversation, Message
from app.models.user import User

class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_conversation(self, customer_id: uuid.UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.customer_id == customer_id)
            .where(Conversation.status == "open")
            .options(selectinload(Conversation.customer))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.customer), selectinload(Conversation.locker))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_topic_id(self, topic_id: int) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(Conversation.topic_id == topic_id)
            .where(Conversation.status == "open") # Only active ones usually
            .options(selectinload(Conversation.customer), selectinload(Conversation.locker))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_conversation(self, customer_id: uuid.UUID) -> Conversation:
        active = await self.get_active_conversation(customer_id)
        if active:
            return active
        
        conversation = Conversation(customer_id=customer_id, status="open")
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def set_topic_id(self, conversation_id: uuid.UUID, topic_id: int):
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(topic_id=topic_id)
        )
        await self.session.commit()

    async def add_message(
        self, 
        conversation_id: uuid.UUID, 
        sender_type: str, 
        content: str, 
        sender_id: uuid.UUID | None = None,
        telegram_message_id: int | None = None,
        message_type: str = "text"
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            sender_id=sender_id,
            telegram_message_id=telegram_message_id,
            message_type=message_type
        )
        self.session.add(message)
        
        # Update last_message_at
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=datetime.utcnow())
        )
        
        await self.session.commit()
        return message

    async def lock_conversation(self, conversation_id: uuid.UUID, agent: User) -> bool:
        conv = await self.get_by_id(conversation_id)
        if not conv or conv.status != "open":
            return False
        
        if conv.locked_by_agent and conv.locked_by_agent != agent.id:
            return False 
        
        conv.locked_by_agent = agent.id
        await self.session.commit()
        return True

    async def unlock_conversation(self, conversation_id: uuid.UUID, agent: User) -> bool:
        conv = await self.get_by_id(conversation_id)
        if not conv:
            return False
        
        if conv.locked_by_agent == agent.id:
            conv.locked_by_agent = None
            await self.session.commit()
            return True
        return False

    async def close_conversation(self, conversation_id: uuid.UUID) -> bool:
        conv = await self.get_by_id(conversation_id)
        if not conv:
            return False
        
        conv.status = "closed"
        conv.locked_by_agent = None
        await self.session.commit()
        return True

    async def list_open_conversations(self) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.status == "open")
            .order_by(Conversation.created_at)
            .options(selectinload(Conversation.customer), selectinload(Conversation.locker))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
