import uuid
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.core.config import settings
from app.models.user import UserType

router = Router()

@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message):
    welcome_text = (
        "👋 <b>Welcome to Digital Support!</b>\n\n"
        "I am here to help you connecting with our support team.\n"
        "Please send your message directly here, and an agent will respond shortly.\n\n"
        "<i>You can send text, photos, documents, or voice messages.</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("list"), F.chat.id == settings.AGENT_GROUP_ID)
async def cmd_list(message: Message, session: AsyncSession):
    conv_service = ConversationService(session)
    conversations = await conv_service.list_open_conversations()
    
    if not conversations:
        await message.reply("No open conversations.")
        return
        
    text = "<b>Open Conversations:</b>\n"
    for c in conversations:
        locker_name = "Agent"
        if c.locker:
            locker_name = c.locker.username or c.locker.first_name or "Agent"
            
        locked_status = f"🔒 {locker_name}" if c.locked_by_agent else "🟢 Open"
        customer_name = c.customer.username or c.customer.first_name or str(c.customer.telegram_user_id)
        
        text += f"- {customer_name} (<code>{c.id}</code>) [{locked_status}]\n"
        
    await message.reply(text, parse_mode="HTML")

@router.message(Command("lock"), F.chat.id == settings.AGENT_GROUP_ID)
async def cmd_lock(message: Message, command: CommandObject, session: AsyncSession):
    conv_service = ConversationService(session)
    conv_id = None
    
    if command.args:
         try:
            conv_id = uuid.UUID(command.args.strip())
         except ValueError:
            await message.reply("Invalid UUID.")
            return
    elif message.message_thread_id:
        # Infer from topic
        conv = await conv_service.get_by_topic_id(message.message_thread_id)
        if conv:
            conv_id = conv.id
    
    if not conv_id:
        await message.reply("Usage: /lock <conversation_id> (or use inside a topic)")
        return

    user_service = UserService(session)
    agent = await user_service.get_or_create(
        message.from_user.id, 
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        UserType.AGENT
    )
    
    success = await conv_service.lock_conversation(conv_id, agent)
    if success:
        await message.reply("🔒 Conversation locked.")
    else:
        await message.reply("❌ Could not lock (invalid ID, closed, or already locked).")

@router.message(Command("unlock"), F.chat.id == settings.AGENT_GROUP_ID)
async def cmd_unlock(message: Message, command: CommandObject, session: AsyncSession):
    conv_service = ConversationService(session)
    conv_id = None
    
    if command.args:
         try:
            conv_id = uuid.UUID(command.args.strip())
         except ValueError:
            await message.reply("Invalid UUID.")
            return
    elif message.message_thread_id:
        # Infer from topic
        conv = await conv_service.get_by_topic_id(message.message_thread_id)
        if conv:
            conv_id = conv.id
            
    if not conv_id:
        await message.reply("Usage: /unlock <conversation_id> (or use inside a topic)")
        return

    user_service = UserService(session)
    agent = await user_service.get_or_create(
        message.from_user.id, 
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        UserType.AGENT
    )
    
    success = await conv_service.unlock_conversation(conv_id, agent)
    if success:
        await message.reply("🔓 Conversation unlocked.")
    else:
        await message.reply("❌ Could not unlock (only locker/admin can unlock).")

@router.message(Command("close"), F.chat.id == settings.AGENT_GROUP_ID)
async def cmd_close(message: Message, command: CommandObject, session: AsyncSession):
    conv_service = ConversationService(session)
    conv_id = None
    
    if command.args:
         try:
            conv_id = uuid.UUID(command.args.strip())
         except ValueError:
            await message.reply("Invalid UUID.")
            return
    elif message.message_thread_id:
        # Infer from topic
        conv = await conv_service.get_by_topic_id(message.message_thread_id)
        if conv:
            conv_id = conv.id

    if not conv_id:
        await message.reply("Usage: /close <conversation_id> (or use inside a topic)")
        return
        
    success = await conv_service.close_conversation(conv_id)
    if success:
        await message.reply("✅ Conversation closed.")
    else:
        await message.reply("❌ Could not close (invalid ID).")
