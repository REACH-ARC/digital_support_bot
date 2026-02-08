from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.core.config import settings
from app.models.user import UserType
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

# Accept any content type
@router.message(F.chat.type == "private")
async def handle_customer_message(message: Message, session: AsyncSession, bot: Bot):
    user_service = UserService(session)
    conv_service = ConversationService(session)

    # 1. Get or Create User
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        user_type=UserType.CUSTOMER
    )

    # 2. Get or Create Conversation
    conversation = await conv_service.create_conversation(user.id)
    
    # 3. Determine Format & Content
    message_type = "text"
    content = message.text or ""
    
    if message.photo:
        message_type = "photo"
        # Best quality photo
        content = message.photo[-1].file_id 
        if message.caption:
            content += f"|{message.caption}" # Store caption too if needed custom parsing
    
    elif message.document:
        message_type = "document"
        content = message.document.file_id
    elif message.audio:
        message_type = "audio"
        content = message.audio.file_id
    elif message.voice:
        message_type = "voice"
        content = message.voice.file_id
    elif message.video:
        message_type = "video"
        content = message.video.file_id
    elif message.sticker:
        message_type = "sticker"
        content = message.sticker.file_id
    
    # Fallback/Safety
    if not content and not message.text:
        content = "[Unknown Media]"

    # 4. Save to DB
    await conv_service.add_message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=content,
        sender_id=user.id,
        telegram_message_id=message.message_id,
        message_type=message_type
    )

    # 5. Handle Forum Topic & Forwarding structure
    # Robust retry mechanism for topic creation and messaging
    await process_conversation_message(message, conversation, user, conv_service, bot, message_type, content)

async def process_conversation_message(message: Message, conversation, user, conv_service: ConversationService, bot: Bot, message_type: str, content: str):
    """
    Helper function to handle the complex logic of topic validation, creation, and message sending.
    Separated to keep the handler clean and allow recursion/retries if needed (though we use a loop).
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        current_topic_id = conversation.topic_id
        logger.info(f"Processing message id={message.message_id} (Attempt {attempt+1}/{max_retries}). Topic ID: {current_topic_id}")
        
        # A. Create Topic if Missing
        if not current_topic_id:
            try:
                name = f"{user.first_name} {user.last_name or ''}".strip() or f"User {user.telegram_user_id}"
                logger.info(f"Creating new topic for user {user.id} with name: {name}")
                
                topic = await bot.create_forum_topic(chat_id=settings.AGENT_GROUP_ID, name=name)
                current_topic_id = topic.message_thread_id
                
                # Update DB and Local Object
                await conv_service.set_topic_id(conversation.id, current_topic_id)
                conversation.topic_id = current_topic_id
                
                logger.info(f"Topic created successfully. ID: {current_topic_id}")
                
                # Send System Message
                try:
                    await bot.send_message(
                        chat_id=settings.AGENT_GROUP_ID,
                        message_thread_id=current_topic_id,
                        text=f"🆕 <b>New Conversation Started</b>\nUser: {user.full_name}\nID: <code>{conversation.id}</code>",
                        parse_mode="HTML"
                    )
                    # Helper delay to ensure Telegram registers the topic
                    await asyncio.sleep(1) 
                except Exception as sys_msg_error:
                    logger.warning(f"Failed to send system message: {sys_msg_error}")

            except Exception as create_error:
                logger.error(f"Failed to create topic: {create_error}")
                # If we can't create a topic, we must fallback to general chat for this attempt
                current_topic_id = None
        
        # B. Attempt to Send/Copy Message
        if current_topic_id:
            try:
                # 1. Validate topic by attempting to EDIT it (Sync input).
                # This serves two purposes:
                # a) Strong validation: fails if topic is deleted.
                # b) Feature: Syncs topic name if user updated their profile.
                user_name = f"{user.first_name} {user.last_name or ''}".strip() or f"User {user.telegram_user_id}"
                
                try:
                    await bot.edit_forum_topic(chat_id=settings.AGENT_GROUP_ID, message_thread_id=current_topic_id, name=user_name)
                except Exception as val_error:
                    val_err_str = str(val_error).lower()
                    
                    # "message is not modified" means topic exists and name is same -> SUCCESS
                    # "topic_not_modified" (underscore) is also common
                    if "not modified" in val_err_str or "not_modified" in val_err_str:
                         pass 
                    
                    # "thread not found" -> DEAD
                    elif any(x in val_err_str for x in ["thread", "topic", "not found", "deleted", "deactivated", "bad request"]):
                        logger.warning(f"Topic {current_topic_id} is dead (edit failed). Triggering recreation.")
                        raise val_error # Re-raise to trigger outer loop
                    
                    else:
                        logger.warning(f"Topic edit failed with non-critical error: {val_err_str}. Proceeding.")

                # 2. Try Copying
                await message.copy_to(
                    chat_id=settings.AGENT_GROUP_ID,
                    message_thread_id=current_topic_id
                )
                
                logger.info("Message copied successfully.")
                return # Success! Exit function.

            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"Failed to send to topic {current_topic_id} (Attempt {attempt+1}): {error_str}")
                
                # Aggressive Retry Logic:
                # If this is the first attempt, we assume ANY error (except verified content errors) 
                # might be due to a broken topic state. We should force a recreation.
                
                is_content_error = any(x in error_str for x in ["message is too long", "file is too big", "wrong file identifier", "file part exceeded"])
                
                # If it's NOT a content error, and we have retries left, assume the topic is botched.
                if not is_content_error and attempt < max_retries - 1:
                    logger.warning(f"Error does not look like content error. Assuming topic {current_topic_id} is dead/invalid. Clearing and retrying...")
                    
                    # Clear topic in DB
                    await conv_service.set_topic_id(conversation.id, None)
                    conversation.topic_id = None
                    continue # Loop will try to create new topic
                
                elif is_content_error:
                    logger.error("Message content error (too big/invalid). Cannot fix by recreating topic.")
                    # We might want to send a warning to user here? 
                    # For now, just logging and letting it fall to fallback (which might also fail if it's content)
                    pass
                else:
                    logger.error("Max retries reached or unrecoverable error.")

        # C. Fallback to General (if no topic or max retries reached)
        # Only execute this if we are breaking out of the loop or valid attempt failed without retry
        if attempt == max_retries - 1 or not current_topic_id:
             try:
                 logger.info("Falling back to General topic.")
                 fallback_text = (
                    f"📩 <b>New Message</b> (Type: {message_type})\n"
                    f"User: {message.from_user.full_name}\n"
                    f"ID: <code>{user.id}</code>\n"
                    f"Conversation ID: <code>{conversation.id}</code>\n"
                    f"<i>(Topic creation failed or topic lost)</i>"
                 )
                 info = await bot.send_message(settings.AGENT_GROUP_ID, text=fallback_text, parse_mode="HTML")
                 await message.copy_to(settings.AGENT_GROUP_ID, reply_to_message_id=info.message_id)
                 return
             except Exception as fallback_error:
                 logger.error(f"Critical: Failed to send fallback message: {fallback_error}")
                 return
