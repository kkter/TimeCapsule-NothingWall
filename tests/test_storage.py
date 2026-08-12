import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import time_capsule


class FakeBot:
    def __init__(self):
        self.messages = []

    def send_message(self, **kwargs):
        self.messages.append(kwargs)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.previous = (
            time_capsule.DATA_DIR,
            time_capsule.CAPSULES_FILE,
            time_capsule.BACKUP_DIR,
            time_capsule.BACKUP_RETENTION,
            time_capsule.bot,
        )
        time_capsule.DATA_DIR = Path(self.temporary.name) / "data"
        time_capsule.CAPSULES_FILE = time_capsule.DATA_DIR / "time_capsules.json"
        time_capsule.BACKUP_DIR = time_capsule.DATA_DIR / "backups"
        time_capsule.BACKUP_RETENTION = 5
        time_capsule.bot = FakeBot()

    def tearDown(self):
        (
            time_capsule.DATA_DIR,
            time_capsule.CAPSULES_FILE,
            time_capsule.BACKUP_DIR,
            time_capsule.BACKUP_RETENTION,
            time_capsule.bot,
        ) = self.previous
        self.temporary.cleanup()

    def test_concurrent_adds_are_not_lost_and_backups_are_private(self):
        threads = [
            threading.Thread(target=time_capsule.add_capsule, args=(f"message-{index}", index, 0))
            for index in range(20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        capsules = time_capsule.load_capsules()
        self.assertEqual(len(capsules), 20)
        self.assertEqual(len({item["id"] for item in capsules}), 20)
        self.assertEqual(os.stat(time_capsule.CAPSULES_FILE).st_mode & 0o777, 0o600)
        backups = list(time_capsule.BACKUP_DIR.glob("time_capsules_*.json"))
        self.assertLessEqual(len(backups), 5)
        self.assertTrue(all((os.stat(path).st_mode & 0o777) == 0o600 for path in backups))

    def test_public_projection_excludes_private_fields(self):
        time_capsule.save_capsules(
            [
                {
                    "id": "private-id",
                    "user_id": 123,
                    "message": "shared message",
                    "created_at": "2026-08-12T00:00:00+00:00",
                    "send_at": "2026-08-13T00:00:00+00:00",
                    "sent": True,
                    "shared": True,
                },
                {
                    "id": "hidden-id",
                    "user_id": 456,
                    "message": "private message",
                    "shared": False,
                },
            ]
        )
        self.assertEqual(
            time_capsule.get_public_capsules(),
            [{"message": "shared message", "created_at": "2026-08-12T00:00:00+00:00"}],
        )

    def test_http_allowlist_applies_to_get_and_head(self):
        time_capsule.save_capsules(
            [
                {
                    "user_id": 999,
                    "message": "public",
                    "created_at": "2026-08-12T00:00:00+00:00",
                    "shared": True,
                }
            ]
        )
        server = time_capsule.CapsuleHTTPServer(
            ("127.0.0.1", 0), time_capsule.PublicRequestHandler
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=5) as response:
                health = json.load(response)
            self.assertEqual(health["status"], "ok")

            with urllib.request.urlopen(
                f"{base_url}/time_capsules.json", timeout=5
            ) as response:
                public_capsules = json.load(response)
            self.assertEqual(
                public_capsules,
                [{"message": "public", "created_at": "2026-08-12T00:00:00+00:00"}],
            )

            for method in ("GET", "HEAD"):
                request = urllib.request.Request(
                    f"{base_url}/time_capsule.py", method=method
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(raised.exception.code, 404)
                raised.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_wall_renders_public_projection_as_text_not_html(self):
        html = (time_capsule.SCRIPT_DIR / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("capsule.shared === true", html)
        self.assertNotIn("bubble.innerHTML", html)
        self.assertIn("messageElement.textContent", html)
        self.assertIn("No shared capsules yet — showing demo messages.", html)
        self.assertIn("Demo capsule", html)

    def test_web_only_mode_does_not_require_a_telegram_token(self):
        with patch.dict(os.environ, {"BOT_ENABLED": "false"}, clear=True), patch.object(
            time_capsule, "start_web_server"
        ) as start_server:
            time_capsule.main()
        start_server.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
