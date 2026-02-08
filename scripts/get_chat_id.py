import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load env to get token if available, or just ask user
load_dotenv()

async def get_chat_id():
    token = os.getenv("BOT_TOKEN")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        token = input("Enter your Bot Token: ").strip()

    print(f"\n1. Make sure the bot is added to the group.")
    print(f"2. Send a message to the group (e.g., 'Hello Bot').")
    input("Press Enter when done...")

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
    if not data.get("ok"):
        print(f"Error: {data}")
        return

    results = data.get("result", [])
    if not results:
        print("No updates found. Try sending a message again.")
        return

    print("\nRecent Chats Found:")
    found_any = False
    for update in results:
        message = update.get("message") or update.get("my_chat_member")
        if not message:
            continue
            
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        title = chat.get("title", "Private Chat")
        
        if chat_type in ["group", "supergroup"]:
            print(f"📂 Group: '{title}' | ID: {chat_id}")
            found_any = True
            
    if not found_any:
        print("No group messages found. Make sure you sent a message to the GROUP, not private chat.")

if __name__ == "__main__":
    asyncio.run(get_chat_id())
