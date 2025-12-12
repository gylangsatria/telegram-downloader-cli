import os
import asyncio
import hashlib
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME")
target_chat = os.getenv("TARGET_CHAT")
download_dir = os.getenv("DOWNLOAD_DIR")

os.makedirs(download_dir, exist_ok=True)

client = TelegramClient(session_name, api_id, api_hash)

download_log = "downloaded.log"
checksum_log = "checksums.log"

if os.path.exists(download_log):
    with open(download_log, "r") as f:
        downloaded_ids = set(line.strip() for line in f.readlines())
else:
    downloaded_ids = set()

if os.path.exists(checksum_log):
    with open(checksum_log, "r") as f:
        known_checksums = set(line.strip() for line in f.readlines())
else:
    known_checksums = set()


def calculate_checksum(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def mark_downloaded(message_id, checksum):
    downloaded_ids.add(str(message_id))
    known_checksums.add(checksum)

    with open(download_log, "a") as f:
        f.write(f"{message_id}\n")

    with open(checksum_log, "a") as f:
        f.write(f"{checksum}\n")


async def fast_download_media(message, output_dir):
    if not message.media:
        return None

    filename = message.file.name or f"{message.id}"
    file_path = os.path.join(output_dir, filename)

    size = message.file.size if message.file else None
    pbar = tqdm(total=size, unit="B", unit_scale=True, desc=f"{message.id}", leave=False)

    chunk_size = 5 * 1024 * 1024

    try:
        with open(file_path, "wb") as f:
            async for chunk in client.iter_download(message.media, chunk_size=chunk_size):
                f.write(chunk)
                pbar.update(len(chunk))
    except Exception:
        pbar.close()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    pbar.close()
    return file_path


async def safe_download(message, sem):
    async with sem:
        try:
            file_path = await fast_download_media(message, download_dir)
            if not file_path:
                return

            checksum = calculate_checksum(file_path)

            if checksum in known_checksums:
                os.remove(file_path)
                return

            mark_downloaded(message.id, checksum)
            print(f"Downloaded: {file_path}")

        except FloodWaitError as fw:
            print(f"FloodWait {fw.seconds} detik")
            await asyncio.sleep(fw.seconds)
            await safe_download(message, sem)

        except Exception as e:
            print(f"Gagal download: {e}")


async def download_history():
    print("Mulai scan riwayat")

    total_messages = await client.get_messages(target_chat, limit=0)
    total_count = total_messages.total

    pbar = tqdm(total=total_count, desc="Scanning", unit="msg")

    sem = asyncio.Semaphore(3)
    tasks = []

    async for message in client.iter_messages(target_chat, limit=None):
        pbar.update(1)

        if str(message.id) in downloaded_ids:
            continue

        if message.media:
            tasks.append(asyncio.create_task(safe_download(message, sem)))

    pbar.close()

    print("Menunggu semua download selesai")
    await asyncio.gather(*tasks)
    print("Semua riwayat selesai")


@client.on(events.NewMessage(chats=target_chat))
async def handler(event):
    message = event.message
    if str(message.id) in downloaded_ids:
        return

    if message.media:
        sem = asyncio.Semaphore(3)
        await safe_download(message, sem)


async def main():
    await client.start()
    print("Downloader aktif")

    asyncio.create_task(download_history())
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
