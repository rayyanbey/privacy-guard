"""
PrivacyGuard - Privacy Controller
Activates/deactivates privacy overlays and sends notifications.
"""

import threading
from core.config_manager import ConfigManager
from core.logger import Logger


class PrivacyController:
    def __init__(self, config: ConfigManager, logger: Logger):
        self._config = config
        self._logger = logger
        self._active = False
        self._overlay = None          # Will be set by UI layer
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def register_overlay(self, overlay):
        """Called by the overlay UI module to register itself."""
        self._overlay = overlay

    def activate(self):
        with self._lock:
            if self._active:
                return
            self._active = True

        mode = self._config.get("privacy_mode", "strong_blur")
        self._logger.event(f"Activating privacy mode: {mode}")
        self._send_notification(mode)

        if self._overlay:
            self._overlay.show(mode)

    def deactivate(self):
        with self._lock:
            if not self._active:
                return
            self._active = False

        self._logger.event("Privacy mode deactivated.")
        if self._overlay:
            self._overlay.hide()

    def is_active(self) -> bool:
        return self._active

    def set_mode(self, mode: str):
        valid = {"light_blur", "strong_blur", "blackout", "freeze"}
        if mode not in valid:
            self._logger.warn(f"Invalid mode '{mode}'. Ignoring.")
            return
        self._config.set("privacy_mode", mode)
        self._logger.info(f"Privacy mode changed to: {mode}")
        # If currently active, reapply
        if self._active and self._overlay:
            self._overlay.show(mode)

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _send_notification(self, mode: str):
        if not self._config.get("notifications_enabled", True):
            return
        try:
            from plyer import notification
            mode_labels = {
                "light_blur":   "Light Blur",
                "strong_blur":  "Strong Blur",
                "blackout":     "Blackout",
                "freeze":       "Screen Freeze",
            }
            notification.notify(
                title="🔐 PrivacyGuard Activated",
                message=f"Mode: {mode_labels.get(mode, mode)} — Someone is watching your screen.",
                app_name="PrivacyGuard",
                timeout=4,
            )
        except Exception as e:
            self._logger.warn(f"Notification failed: {e}")
