from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

client = TelegramClient("/session/downloader", api_id, api_hash)
client.start()
print("Login success")
client.disconnect()
