# Telegram Downloader CLI (Telethon-Based & Docker Ready)

An automatic downloader for retrieving media from Telegram groups using a Telethon‑based user session. Designed to capture both historical and real‑time messages, supporting large file downloads, persistent sessions, and seamless integration with automated processing pipelines.

---

## Features

- Full history download: Iterates through all past messages in the target group and downloads any media found.
- Real‑time listener: Automatically downloads new media as soon as it appears.
- Large file support: Uses Telethon (user session), allowing downloads beyond the 2 GB limit of the Bot API.
- Dockerized workflow: Runs inside a container with mounted volumes for session persistence and file storage.
- Session persistence: Uses Telethon `.session` files to avoid repeated logins.

---

## Current Limitations

- The downloader cannot start automatically because Telethon requires an interactive login for the first session.
- Docker containers cannot accept interactive input, causing the login process to fail.
- A valid `.session` file must be generated manually on the host machine and copied into the container.
- Additional adjustments are required to ensure stable runtime behavior.

---

## Requirements

- Python 3.10+ (for generating the session file)
- Docker and Docker Compose
- A Telegram account (user session, not bot token)
- API ID and API Hash from https://my.telegram.org

---

## Setup Instructions

### 1. Generate Telethon session on host

Create a file named `login.py`:

```python
from telethon import TelegramClient

api_id = 123456
api_hash = "your_api_hash"

client = TelegramClient("downloader", api_id, api_hash)
client.start()
print("Login success")


```python
from telethon import TelegramClient

api_id = 123456
api_hash = "your_api_hash"

client = TelegramClient("downloader", api_id, api_hash)
client.start()
print("Login success")
```

2. Configure environment variables

Create .env:
```code
API_ID=123456
API_HASH=your_api_hash
SESSION_NAME=/session/downloader
TARGET_CHAT=your_group_media example : t.me/sfbsdsz just add >> sfbsdsz
DOWNLOAD_DIR=/downloads

```

4. Build and run the container

Build and run the container
```code
docker compose up --build -d
```
Login
```code
docker compose run telethon-login
```
After login, a file named downloader.session will be created.

Watch Log 
```code
docker logs -f telegram-downloader-cli
```

### Project Status

This project is still under development. The container builds correctly, but the downloader logic and session handling require further refinement before it becomes fully operational.

### Roadmap

- Add automatic session string support ✅
- Improve error handling and reconnection logic ✅
- Add file type filtering ❌
- Add upload pipeline integration ❌
- Add rate‑limit safe history scanning ❌
- Add optional logging to file ❌
