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
    """Generate SHA256 checksum for a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def mark_downloaded(message_id, checksum):
    """Record message_id and checksum to log files."""
    downloaded_ids.add(str(message_id))
    known_checksums.add(checksum)

    with open(download_log, "a") as f:
        f.write(f"{message_id}\n")

    with open(checksum_log, "a") as f:
        f.write(f"{checksum}\n")


async def safe_download(message):
    """Download media with checksum-based duplicate prevention and progress bar."""
    # Get file size for progress bar
    size = message.file.size if message.file else None

    # Create progress bar for this file
    pbar = tqdm(
        total=size,
        unit="B",
        unit_scale=True,
        desc=f"Downloading {message.id}",
        leave=False
    )

    # Custom progress callback
    def progress_callback(current, total):
        pbar.total = total
        pbar.n = current
        pbar.refresh()

    # Download file
    file_path = await message.download_media(
        download_dir,
        progress_callback=progress_callback
    )

    pbar.close()

    if not file_path:
        return None

    checksum = calculate_checksum(file_path)

    if checksum in known_checksums:
        os.remove(file_path)
        return None

    mark_downloaded(message.id, checksum)
    return file_path


async def download_history():
    """Download full history with progress bar and rate-limit safety."""
    print("Starting full history download...")

    # Count total messages for progress bar
    total_messages = await client.get_messages(target_chat, limit=0)
    total_count = total_messages.total

    pbar = tqdm(total=total_count, desc="History scanning", unit="msg")

    async for message in client.iter_messages(target_chat, limit=None):
        await asyncio.sleep(0.5)
        pbar.update(1)

        if str(message.id) in downloaded_ids:
            continue

        if message.media:
            try:
                file_path = await safe_download(message)
                if file_path:
                    print(f"History downloaded: {file_path}")

            except FloodWaitError as fw:
                print(f"FloodWait detected: waiting {fw.seconds} seconds...")
                await asyncio.sleep(fw.seconds)

                try:
                    file_path = await safe_download(message)
                    if file_path:
                        print(f"History downloaded after wait: {file_path}")
                except Exception as e:
                    print(f"Failed after FloodWait retry: {e}")

            except Exception as e:
                print(f"Failed history download: {e}")

    pbar.close()
    print("All history processed.")


@client.on(events.NewMessage(chats=target_chat))
async def handler(event):
    """Handle new incoming messages with duplicate prevention."""
    message = event.message

    if str(message.id) in downloaded_ids:
        return

    if message.media:
        try:
            file_path = await safe_download(message)
            if file_path:
                print(f"New media downloaded: {file_path}")

        except FloodWaitError as fw:
            print(f"FloodWait on new message: waiting {fw.seconds} seconds...")
            await asyncio.sleep(fw.seconds)

            try:
                file_path = await safe_download(message)
                if file_path:
                    print(f"New media downloaded after wait: {file_path}")
            except Exception as e:
                print(f"Failed new media retry: {e}")

        except Exception as e:
            print(f"Failed new media download: {e}")


async def main():
    """Start client, run history download, and listen for new messages."""
    await client.start()
    print("Telethon downloader is running...")

    asyncio.create_task(download_history())
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
