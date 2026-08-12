# Time Capsule Bot & Nothing Wall

A Telegram bot that returns a message to its author at a randomly selected future date. After a capsule opens, its author can choose whether to publish the message anonymously on the companion web wall.

[Live wall](https://capsule.520353.xyz) · [Telegram bot](https://t.me/MoonTimeCapsuleBot)

## What this project demonstrates

- A long-running Python service with Telegram command and callback handling
- Delayed delivery with locked, atomic JSON persistence and private rolling backups
- An anonymous, opt-in public publishing flow
- A lightweight responsive web experience served by the application
- Docker Compose deployment and local data persistence

## Privacy model

Capsules are private by default. The runtime record contains the Telegram user ID required to return a capsule to its author, so `data/time_capsules.json` is deliberately excluded from Git and Docker build contexts.

The public `/time_capsules.json` endpoint:

- includes only records whose `shared` flag is explicitly `true`;
- returns an allowlist of public fields (`message` and `created_at`);
- never returns Telegram user IDs or delivery metadata; and
- cannot be bypassed through static paths or alternate `HEAD` requests.

The sharing callback verifies that the Telegram account accepting publication owns the selected capsule. Capsule UUIDs avoid index drift during concurrent updates. Before every real storage change, the service writes a mode-`0600` rolling backup under ignored `data/backups/`; writes use a temporary file, `fsync` and atomic replacement.

> Important: if private data was committed before these controls were added, deleting it from the current branch does not remove it from earlier Git history. Repository-history cleanup should be performed separately after preserving a backup and coordinating a force-push.

## Quick start

### Requirements

- Python 3.12+
- A Telegram bot token
- Docker and Docker Compose (optional)

### Local development

```bash
git clone https://github.com/kkter/TimeCapsule-NothingWall.git
cd TimeCapsule-NothingWall
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your_bot_token"
export ADMIN_CHAT_ID="your_chat_id" # optional test mode
python time_capsule.py
```

The wall is available at `http://localhost:9000`.

### Docker Compose

Create a local `.env` file from the committed template, then replace the values:

```bash
cp .env.example .env
```

```bash
docker compose up -d --build
```

The wall binds to `127.0.0.1:5102` by default for use behind Nginx. Override `CAPSULE_BIND_ADDRESS` or `CAPSULE_PORT` only when needed.

## Bot commands

| Command | Purpose |
| --- | --- |
| Send a message | Create a private time capsule |
| `/status` | Show capsule counts for the current user |
| `/wall` | Open the public Nothing Wall |
| `/help` | Show usage help |

Non-admin capsules reopen after a randomly selected interval from 30 days to 3 years. Setting `ADMIN_CHAT_ID` enables a 1–3 minute test interval for that account.

## Architecture

```text
Telegram user
    │ messages and sharing choice
    ▼
Telegram Bot API ──► time_capsule.py ──► data/time_capsules.json
                           │                     (private, ignored)
                           │ allowlisted shared records only
                           ▼
                    /time_capsules.json ──► index.html
```

## Project structure

```text
.
├── time_capsule.py              # Telegram bot, scheduler and HTTP server
├── index.html                   # Public Nothing Wall UI
├── data/                        # Private runtime data (ignored)
├── auto_backup_timecapsule.sh   # Manual private backup helper
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── requirements.txt
```

## Local backup

Run:

```bash
./auto_backup_timecapsule.sh
```

This atomically copies the runtime file to ignored `data/manual-backups/`, applies mode `0600`, and retains the newest 30 by default. It does not run Git write commands or upload capsule data.

## Health check

`GET /healthz` validates that the private JSON store can be read and returns no message content or user identifiers. Docker Compose uses this endpoint for service health.

## Security notes

- Keep `.env`, all files under `data/`, and logs outside version control.
- Restrict filesystem and server access to private runtime data.
- Use HTTPS and a reverse proxy for public deployments.
- The JSON store is suitable for this small single-process deployment. A larger service should move to a transactional database and add encryption at rest, retention controls and user-directed deletion.

## Disclaimer

This is a personal project and demonstration service. Operators are responsible for protecting stored content and complying with applicable privacy requirements.
