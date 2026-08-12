"""Telegram time-capsule bot and anonymous public wall."""

from __future__ import annotations

import http.server
import json
import os
import posixpath
import random
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import telebot


VERSION = "2.5.0"
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", SCRIPT_DIR / "data"))
CAPSULES_FILE = Path(os.getenv("CAPSULES_FILE", DATA_DIR / "time_capsules.json"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", DATA_DIR / "backups"))
BACKUP_RETENTION = max(1, int(os.getenv("BACKUP_RETENTION", "20")))
WEB_PORT = int(os.getenv("WEB_PORT", "9000"))
CHECK_INTERVAL_SECONDS = max(5, int(os.getenv("CHECK_INTERVAL_SECONDS", "30")))
WALL_URL = os.getenv("WALL_URL", "https://capsule.520353.xyz")
PUBLIC_FILES = {
    "/index.html",
    "/favicon.ico",
    "/favicon-32x32.png",
    "/apple-touch-icon.png",
    "/robots.txt",
    "/sitemap.xml",
}
DATA_LOCK = threading.RLock()
bot: telebot.TeleBot | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _load_unlocked() -> list[dict]:
    if not CAPSULES_FILE.exists():
        return []
    with CAPSULES_FILE.open("r", encoding="utf-8") as handle:
        capsules = json.load(handle)
    if not isinstance(capsules, list) or not all(isinstance(item, dict) for item in capsules):
        raise ValueError("capsule store must contain a JSON array of objects")
    return capsules


def _backup_existing_unlocked() -> None:
    if not CAPSULES_FILE.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    suffix = utc_now().strftime("%Y%m%dT%H%M%S.%fZ")
    destination = BACKUP_DIR / f"time_capsules_{suffix}.json"
    shutil.copyfile(CAPSULES_FILE, destination)
    destination.chmod(0o600)
    backups = sorted(BACKUP_DIR.glob("time_capsules_*.json"), reverse=True)
    for old_backup in backups[BACKUP_RETENTION:]:
        old_backup.unlink(missing_ok=True)


def _save_unlocked(capsules: list[dict]) -> None:
    CAPSULES_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _backup_existing_unlocked()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{CAPSULES_FILE.name}.", dir=CAPSULES_FILE.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(capsules, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, CAPSULES_FILE)
        directory_descriptor = os.open(CAPSULES_FILE.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def load_capsules() -> list[dict]:
    with DATA_LOCK:
        return _load_unlocked()


def save_capsules(capsules: list[dict]) -> None:
    with DATA_LOCK:
        _save_unlocked(capsules)


def get_public_capsules() -> list[dict]:
    """Return only allowlisted anonymous fields from explicitly shared capsules."""
    return [
        {"message": capsule.get("message", ""), "created_at": capsule.get("created_at")}
        for capsule in load_capsules()
        if capsule.get("shared") is True
    ]


def _require_bot() -> telebot.TeleBot:
    if bot is None:
        raise RuntimeError("Telegram bot is not initialized")
    return bot


def add_capsule(message: str, user_id: int, admin_chat_id: int) -> dict:
    if user_id == admin_chat_id and admin_chat_id != 0:
        delay = timedelta(minutes=random.randint(1, 3))
        confirmation = "👑 Admin time capsule buried! It will open in a few minutes."
    else:
        delay = timedelta(days=random.randint(30, 1095))
        confirmation = "⏰ Time capsule buried and will open at an unknown time!"
    created_at = utc_now()
    capsule = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "message": message,
        "created_at": created_at.isoformat(),
        "send_at": (created_at + delay).isoformat(),
        "sent": False,
        "shared": False,
    }
    with DATA_LOCK:
        capsules = _load_unlocked()
        capsules.append(capsule)
        _save_unlocked(capsules)
    _require_bot().send_message(chat_id=user_id, text=confirmation)
    return capsule


def ask_for_sharing(user_id: int, capsule_id: str) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            "👊🏼 Share with the world", callback_data=f"share:{capsule_id}"
        )
    )
    markup.add(
        telebot.types.InlineKeyboardButton("💔 Keep private", callback_data="keep_private")
    )
    _require_bot().send_message(
        chat_id=user_id,
        text=(
            "💫 Would you like to share this Time Capsule with others?\n\n"
            f"It will appear anonymously on the public [Time Capsule Wall]({WALL_URL})."
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


def _claim_due_capsule() -> dict | None:
    now = utc_now()
    with DATA_LOCK:
        capsules = _load_unlocked()
        changed = False
        for capsule in capsules:
            if capsule.get("sent"):
                continue
            try:
                due = _parse_timestamp(str(capsule["send_at"])) <= now
            except (KeyError, TypeError, ValueError):
                continue
            if not due:
                continue
            claimed_at = capsule.get("delivery_claimed_at")
            if claimed_at:
                try:
                    if now - _parse_timestamp(str(claimed_at)) < timedelta(minutes=5):
                        continue
                except (TypeError, ValueError):
                    pass
            if not capsule.get("id"):
                capsule["id"] = str(uuid.uuid4())
            capsule["delivery_claimed_at"] = now.isoformat()
            changed = True
            candidate = dict(capsule)
            break
        else:
            candidate = None
        if changed:
            _save_unlocked(capsules)
        return candidate


def _finish_delivery(capsule_id: str, sent: bool) -> None:
    with DATA_LOCK:
        capsules = _load_unlocked()
        for capsule in capsules:
            if capsule.get("id") == capsule_id:
                capsule.pop("delivery_claimed_at", None)
                if sent:
                    capsule["sent"] = True
                    capsule["sent_at"] = utc_now().isoformat()
                _save_unlocked(capsules)
                return


def check_and_send_capsules() -> int:
    delivered = 0
    while candidate := _claim_due_capsule():
        capsule_id = str(candidate["id"])
        try:
            now = utc_now()
            created_at = _parse_timestamp(str(candidate["created_at"]))
            elapsed = now - created_at
            time_text = f"{elapsed.days} days ago" if elapsed.days else f"{elapsed.seconds // 3600} hours ago"
            _require_bot().send_message(
                chat_id=candidate["user_id"],
                text=(
                    "📮 Time capsule opened!\n\n"
                    f"This is a message from you {time_text}:\n\n「{candidate['message']}」"
                ),
            )
            _finish_delivery(capsule_id, True)
            delivered += 1
            try:
                ask_for_sharing(int(candidate["user_id"]), capsule_id)
            except Exception as exc:
                print(f"Share prompt could not be sent for capsule {capsule_id}: {exc}")
        except Exception:
            _finish_delivery(capsule_id, False)
            raise
    return delivered


def handle_callback(call) -> None:
    telegram_bot = _require_bot()
    if call.data.startswith("share:") or call.data.startswith("share_"):
        reference = call.data.split(":" if ":" in call.data else "_", 1)[1]
        with DATA_LOCK:
            capsules = _load_unlocked()
            capsule = None
            if reference.isdigit():
                index = int(reference)
                if 0 <= index < len(capsules):
                    capsule = capsules[index]
            else:
                capsule = next((item for item in capsules if item.get("id") == reference), None)
            if (
                capsule is None
                or capsule.get("user_id") != call.from_user.id
                or not capsule.get("sent")
            ):
                allowed = False
            else:
                capsule["shared"] = True
                _save_unlocked(capsules)
                allowed = True
        if not allowed:
            telegram_bot.answer_callback_query(
                call.id, "This capsule cannot be shared by this account.", show_alert=True
            )
            return
        telegram_bot.answer_callback_query(call.id, "Capsule shared anonymously.")
        telegram_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✨ Thank you for sharing your Time Capsule with the world!",
        )
    elif call.data == "keep_private":
        telegram_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔒 Your message remains private.",
        )


def handle_message(message, admin_chat_id: int) -> None:
    telegram_bot = _require_bot()
    user_id = message.from_user.id
    text = (message.text or "").strip()
    if text == "/status":
        capsules = [item for item in load_capsules() if item.get("user_id") == user_id]
        pending = sum(not item.get("sent") for item in capsules)
        opened = sum(bool(item.get("sent")) for item in capsules)
        shared = sum(bool(item.get("shared")) for item in capsules)
        telegram_bot.send_message(
            chat_id=user_id,
            text=f"💡 Your capsules:\n⏳ Waiting: {pending}\n✅ Opened: {opened}\n👊🏼 Shared: {shared}",
        )
    elif text == "/wall":
        telegram_bot.send_message(
            chat_id=user_id,
            text=f"💫 Nothing Wall\n\n[Read shared Time Capsules]({WALL_URL})",
            parse_mode="Markdown",
        )
    elif text in {"/help", "/start"}:
        telegram_bot.send_message(
            chat_id=user_id,
            text=(
                "🕰️ Welcome to Time Capsule Bot!\n\n"
                "Send a text message and it will return to you at an unknown time.\n\n"
                "⌛️ /status - Check your capsules\n"
                "💫 /wall - Read shared capsules\n"
                "❓ /help - Show this help"
            ),
        )
    elif text.startswith("/"):
        telegram_bot.send_message(chat_id=user_id, text="Unknown command. Use /help for options.")
    elif text:
        add_capsule(text, user_id, admin_chat_id)


class CapsuleHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class PublicRequestHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "TimeCapsuleHTTP/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def _send_json(self, payload: object, status: int = 200, head_only: bool = False) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(encoded)

    def _route(self, head_only: bool = False) -> None:
        request_path = unquote(urlsplit(self.path).path)
        request_path = "/" + posixpath.normpath(request_path).lstrip("/")
        if request_path == "/healthz":
            try:
                capsules = load_capsules()
                self._send_json({"status": "ok", "storage": "ready", "capsules": len(capsules)}, head_only=head_only)
            except (OSError, ValueError, json.JSONDecodeError):
                self._send_json({"status": "unhealthy", "storage": "unavailable"}, 503, head_only)
            return
        if request_path == "/time_capsules.json":
            try:
                self._send_json(get_public_capsules(), head_only=head_only)
            except (OSError, ValueError, json.JSONDecodeError):
                self._send_json({"error": "public capsules are temporarily unavailable"}, 503, head_only)
            return
        if request_path == "/":
            request_path = "/index.html"
        if request_path not in PUBLIC_FILES:
            self.send_error(404)
            return
        self.path = request_path
        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()

    def do_GET(self):
        self._route(False)

    def do_HEAD(self):
        self._route(True)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, HEAD, OPTIONS")
        self.end_headers()


def start_web_server() -> None:
    with CapsuleHTTPServer(("", WEB_PORT), PublicRequestHandler) as server:
        print(f"Web wall listening on port {WEB_PORT}")
        server.serve_forever()


def capsule_checker() -> None:
    while True:
        try:
            check_and_send_capsules()
        except Exception as exc:
            print(f"Capsule delivery check failed: {exc}")
        time.sleep(CHECK_INTERVAL_SECONDS)


def register_handlers(telegram_bot: telebot.TeleBot, admin_chat_id: int) -> None:
    telegram_bot.register_callback_query_handler(handle_callback, func=lambda _call: True)
    telegram_bot.register_message_handler(
        lambda message: handle_message(message, admin_chat_id),
        content_types=["text"],
        func=lambda _message: True,
    )


def main() -> None:
    global bot
    bot_enabled = os.getenv("BOT_ENABLED", "1").lower() in {"1", "true", "yes"}
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not bot_enabled:
        print(f"Time Capsule Wall v{VERSION} started in web-only mode")
        start_web_server()
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required when BOT_ENABLED=true")
    try:
        admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", "0"))
    except ValueError as exc:
        raise SystemExit("ADMIN_CHAT_ID must be an integer") from exc

    bot = telebot.TeleBot(token, threaded=True)
    register_handlers(bot, admin_chat_id)
    threading.Thread(target=start_web_server, daemon=True, name="public-wall").start()
    threading.Thread(target=capsule_checker, daemon=True, name="capsule-checker").start()
    print(f"Time Capsule Bot v{VERSION} started; private data is stored in {DATA_DIR}")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=False)


if __name__ == "__main__":
    main()
