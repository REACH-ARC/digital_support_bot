import uuid
from aiogram import Router, F, Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.core.config import settings
from app.models.user import UserType
import logging
import re

router = Router()
logger = logging.getLogger(__name__)

ID_PATTERN = re.compile(r"Conversation ID: ([a-f0-9\-]+)")

@router.message(F.chat.id == settings.AGENT_GROUP_ID, F.reply_to_message)
async def handle_agent_reply(message: Message, session: AsyncSession, bot: Bot):
    logger.info(f"Agent reply received: {message.message_id}")
    # Agents reply to the "Info Block" OR the "Media Message" (which is a reply to info block)
    # So we need to check both the replied message and its parent if possible (but API doesn't give parent of reply).
    # Strategy:
    # 1. Check if direct reply has ID (Info Block case).
    # 2. If not, check if it's a media message we forwarded? Hard to track without DB lookup of message_id.
    #    Actually, in `customer.py`, we reply to the info block with the media.
    #    So if Agent replies to Media, they are replying to a message from Bot.
    #    But that Media message doesn't contain the Text ID.
    #    WORKAROUND: Agents MUST reply to the TEXT Info Block to ensure we get the ID.
    #    OR we parse the caption of the media if we added one? No.
    #    BETTER: We CAN lookup the `messages` table for the `telegram_message_id` of the *replied message*.
    #    If the agent replies to a Photo we sent, that Photo's ID in Agent Group is NOT in our DB (we stored user's ID).
    #    
    #    Let's stick to: "Agent, please reply to the INFO BLOCK". 
    #    But that's annoying.
    #    
    #    Let's try to extract ID from text. If fails, assume it's a detailed log or ignore?
    
    # Check if replying inside a Topic
    topic_id = message.message_thread_id
    conversation_id = None
    
    conv_service = ConversationService(session)
    user_service = UserService(session)

    # Strategy 1: Topic ID Lookup (Preferred)
    if topic_id:
        conv = await conv_service.get_by_topic_id(topic_id)
        if conv:
            conversation_id = conv.id
    
    # Strategy 2: Regex Fallback (if they reply to an old message in General topic)
    if not conversation_id:
        reply = message.reply_to_message
        if reply and reply.from_user.is_bot:
            text_to_check = reply.text or reply.caption or ""
            match = ID_PATTERN.search(text_to_check)
            if match:
                try:
                    conversation_id = uuid.UUID(match.group(1))
                except ValueError:
                    pass

    if not conversation_id:
        # If we still don't have it, we can't do anything.
        # But in a Topic, we might just be chatting among agents?
        # If the bot is not involved, maybe ignore?
        # But if the agent WANTS to reply to customer, they must be in the right topic.
        if topic_id:
             logger.warning(f"Agent replied in topic {topic_id} but no active conversation found.")
             # await message.reply("⚠️ No active conversation found for this topic.") 
        return

    # 2. Get Agent (moved up in original code, but we do it here)
    agent = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        user_type=UserType.AGENT
    )

    # 3. Get Conversation (Already have 'conv' if strategy 1 worked, else fetch it)
    if not 'conv' in locals() or not conv:
        conv = await conv_service.get_by_id(conversation_id)
    
    if not conv:
        await message.reply("❌ Conversation not found.")
        return
    
    # Check Lock
    if conv.locked_by_agent:
        if conv.locked_by_agent != agent.id:
            await message.reply(f"🔒 Locked by another agent.")
            return
    else:
        # Auto-lock on first reply
        await conv_service.lock_conversation(conv.id, agent)
        await message.reply(f"🔒 Conversation auto-locked to you.")

    # 3. Send to Customer (Copy Message to support Media)
    try:
        await message.copy_to(chat_id=conv.customer.telegram_user_id)
    except Exception as e:
        logger.error(f"Failed to send to user {conv.customer.telegram_user_id}: {e}")
        await message.reply("❌ Failed to send message to user (blocked?).")
        return

    # 4. Save Agent Message
    message_type = "text"
    content = message.text or ""
    if message.photo:
        message_type = "photo"
        content = message.photo[-1].file_id
    elif message.document:
        message_type = "document"
        content = message.document.file_id
    elif message.sticker:
        message_type = "sticker"
        content = message.sticker.file_id
    # etc...
    
    await conv_service.add_message(
        conversation_id=conv.id,
        sender_type="agent",
        content=content,
        sender_id=agent.id,
        telegram_message_id=message.message_id,
        message_type=message_type
    )
