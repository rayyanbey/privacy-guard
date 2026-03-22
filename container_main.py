"""
PrivacyGuard container entrypoint.
Runs detection in background and exposes a small HTTP status server.
"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.config_manager import ConfigManager
from core.detection_engine import DetectionEngine
from core.privacy_controller import PrivacyController
from core.logger import Logger


def _make_handler(config: ConfigManager, privacy: PrivacyController, started_at: float):
    class StatusHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/health"):
                self.send_response(404)
                self.end_headers()
                return

            payload = {
                "status": "ok",
                "uptime_sec": round(time.time() - started_at, 1),
                "system_enabled": bool(config.get("system_enabled", True)),
                "privacy_active": bool(privacy.is_active()),
                "mode": config.get("privacy_mode", "strong_blur"),
            }
            body = json.dumps(payload).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _fmt, *_args):
            # Keep container logs clean; app logger already logs key events.
            return

    return StatusHandler


def main():
    port = int(os.getenv("PORT", "8080"))

    config = ConfigManager()
    logger = Logger()
    privacy_ctrl = PrivacyController(config, logger)
    detector = DetectionEngine(config, privacy_ctrl, logger)

    detection_thread = threading.Thread(target=detector.run, daemon=True)
    detection_thread.start()
    logger.info("Detection engine started in container background thread.")

    handler = _make_handler(config, privacy_ctrl, time.time())
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    logger.info(f"Container status server listening on port {port}.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        detector.stop()
        server.server_close()
        logger.info("Container shutdown complete.")


if __name__ == "__main__":
    main()
