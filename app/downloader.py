import os
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME")
target_chat = os.getenv("TARGET_CHAT")  # bisa username atau ID
download_dir = os.getenv("DOWNLOAD_DIR")

os.makedirs(download_dir, exist_ok=True)

client = TelegramClient(session_name, api_id, api_hash)


async def download_history():
    print("Starting full history download...")

    async for message in client.iter_messages(target_chat, limit=None):
        if message.media:
            try:
                file_path = await message.download_media(download_dir)
                print(f"History downloaded: {file_path}")
            except Exception as e:
                print(f"Failed history download: {e}")

    print("All history processed.")


@client.on(events.NewMessage(chats=target_chat))
async def handler(event):
    if event.message.media:
        try:
            file_path = await event.message.download_media(download_dir)
            print(f"New media downloaded: {file_path}")
        except Exception as e:
            print(f"Failed new media download: {e}")


async def main():
    await client.start()
    print("Telethon downloader is running...")

    # Jalankan download history tanpa mengganggu listener
    asyncio.create_task(download_history())

    # Listener realtime
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
