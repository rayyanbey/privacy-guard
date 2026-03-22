"""
PrivacyGuard - Main Entry Point
Run this file to start the application.
"""

import threading
from core.config_manager import ConfigManager
from core.detection_engine import DetectionEngine
from core.privacy_controller import PrivacyController
from core.logger import Logger
from ui.tk_app import TkApp


def main():
    print("=" * 50)
    print("  PrivacyGuard - Starting...")
    print("=" * 50)

    # Initialize core modules
    config = ConfigManager()
    logger = Logger()
    privacy_ctrl = PrivacyController(config, logger)
    detector = DetectionEngine(config, privacy_ctrl, logger)

    # Start detection in background thread
    detection_thread = threading.Thread(target=detector.run, daemon=True)
    detection_thread.start()
    logger.info("Detection engine started in background.")

    # Start Tkinter control panel (blocks main thread)
    app = TkApp(config, detector, privacy_ctrl, logger)
    app.run()


if __name__ == "__main__":
    main()
