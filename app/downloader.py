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

# Load downloaded message IDs
if os.path.exists(download_log):
    with open(download_log, "r") as f:
        downloaded_ids = set(line.strip() for line in f.readlines())
else:
    downloaded_ids = set()

# Load known checksums
if os.path.exists(checksum_log):
    with open(checksum_log, "r") as f:
        known_checksums = set(line.strip() for line in f.readlines())
else:
    known_checksums = set()


def calculate_checksum(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def mark_downloaded(message_id, checksum):
    downloaded_ids.add(str(message_id))
    known_checksums.add(checksum)

    with open(download_log, "a") as f:
        f.write(f"{message_id}\n")

    with open(checksum_log, "a") as f:
        f.write(f"{checksum}\n")


# Parallel download limiter
MAX_PARALLEL = 3
semaphore = asyncio.Semaphore(MAX_PARALLEL)


async def fast_download(message):
    """High-speed downloader using low-level API with parallel control."""
    if not message.media or not message.file:
        return None

    file_name = message.file.name or f"{message.id}"
    file_path = os.path.join(download_dir, file_name)
    total_size = message.file.size

    pbar = tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        desc=f"Downloading {file_name}",
        leave=False
    )

    async def progress_callback(current, total):
        pbar.total = total
        pbar.n = current
        pbar.refresh()

    async with semaphore:
        try:
            await client.download_file(
                message.media.document,
                file_path,
                part_size_kb=1024,  # 1 MB chunks
                progress_callback=progress_callback
            )
        finally:
            pbar.close()

    checksum = calculate_checksum(file_path)

    if checksum in known_checksums:
        os.remove(file_path)
        return None

    mark_downloaded(message.id, checksum)
    return file_path


async def download_history():
    print("Starting full history download...")

    total_messages = await client.get_messages(target_chat, limit=0)
    total_count = total_messages.total

    pbar = tqdm(total=total_count, desc="History scanning", unit="msg")

    tasks = []

    async for message in client.iter_messages(target_chat, limit=None):
        pbar.update(1)

        if str(message.id) in downloaded_ids:
            continue

        if message.media:
            async def task_wrapper(msg=message):
                try:
                    file_path = await fast_download(msg)
                    if file_path:
                        print(f"Downloaded: {file_path}")
                except FloodWaitError as fw:
                    print(f"FloodWait: waiting {fw.seconds}s...")
                    await asyncio.sleep(fw.seconds)
                    await fast_download(msg)
                except Exception as e:
                    print(f"Error: {e}")

            tasks.append(asyncio.create_task(task_wrapper()))

    await asyncio.gather(*tasks)

    pbar.close()
    print("History download complete.")


@client.on(events.NewMessage(chats=target_chat))
async def handler(event):
    message = event.message

    if str(message.id) in downloaded_ids:
        return

    if message.media:
        async def new_msg_task():
            try:
                file_path = await fast_download(message)
                if file_path:
                    print(f"New media downloaded: {file_path}")
            except FloodWaitError as fw:
                print(f"FloodWait new msg: waiting {fw.seconds}s...")
                await asyncio.sleep(fw.seconds)
                await fast_download(message)
            except Exception as e:
                print(f"New message error: {e}")

        asyncio.create_task(new_msg_task())


async def main():
    await client.start()
    print("Telethon downloader is running...")

    asyncio.create_task(download_history())
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
