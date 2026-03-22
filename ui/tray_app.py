"""
PrivacyGuard - System Tray Application
Provides the tray icon, menu, and hotkey listener.
"""

import threading
import pystray
from PIL import Image, ImageDraw
import keyboard

from core.config_manager import ConfigManager
from core.detection_engine import DetectionEngine
from core.privacy_controller import PrivacyController
from core.logger import Logger
from ui.overlay import PrivacyOverlay


MODES = ["light_blur", "strong_blur", "blackout", "freeze"]
MODE_LABELS = {
    "light_blur":  "🟡 Light Blur",
    "strong_blur": "🔵 Strong Blur",
    "blackout":    "⚫ Blackout",
    "freeze":      "🧊 Freeze Screen",
}


class TrayApp:
    def __init__(
        self,
        config: ConfigManager,
        detector: DetectionEngine,
        privacy_ctrl: PrivacyController,
        logger: Logger,
    ):
        self._config = config
        self._detector = detector
        self._privacy = privacy_ctrl
        self._logger = logger

        # Setup overlay and register with controller
        self._overlay = PrivacyOverlay()
        self._privacy.register_overlay(self._overlay)

        # Register hotkey
        hotkey = self._config.get("hotkey_toggle", "ctrl+shift+p")
        try:
            keyboard.add_hotkey(hotkey, self._toggle_system)
            self._logger.info(f"Hotkey registered: {hotkey}")
        except Exception as e:
            self._logger.warn(f"Hotkey registration failed: {e}")

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def run(self):
        icon_img = self._build_icon()
        self._tray = pystray.Icon(
            "PrivacyGuard",
            icon_img,
            "PrivacyGuard",
            menu=self._build_menu(),
        )
        self._logger.info("System tray started. Right-click icon for options.")
        self._tray.run()

    # ------------------------------------------------------------------ #
    #  Tray Menu                                                           #
    # ------------------------------------------------------------------ #

    def _build_menu(self):
        mode_items = [
            pystray.MenuItem(
                label,
                self._make_mode_setter(mode),
                checked=lambda item, m=mode: self._config.get("privacy_mode") == m,
                radio=True,
            )
            for mode, label in MODE_LABELS.items()
        ]

        return pystray.Menu(
            pystray.MenuItem("PrivacyGuard", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🟢 System: ON",
                self._toggle_system,
                checked=lambda item: self._config.get("system_enabled", True),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Privacy Mode", pystray.Menu(*mode_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔒 Lock Now", self._lock_now),
            pystray.MenuItem("🔓 Unlock", self._unlock_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📋 View Logs", self._show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit", self._exit_app),
        )

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def _toggle_system(self):
        current = self._config.get("system_enabled", True)
        new_val = not current
        self._config.set("system_enabled", new_val)
        state = "ENABLED" if new_val else "DISABLED"
        self._logger.info(f"System toggled: {state}")
        if not new_val:
            self._privacy.deactivate()
        # Rebuild menu to update checkbox
        if self._tray:
            self._tray.menu = self._build_menu()

    def _make_mode_setter(self, mode: str):
        def _set():
            self._privacy.set_mode(mode)
            self._logger.info(f"Mode set via tray: {mode}")
            if self._tray:
                self._tray.menu = self._build_menu()
        return _set

    def _lock_now(self):
        mode = self._config.get("privacy_mode", "strong_blur")
        self._privacy.activate()
        self._logger.event(f"Manual lock triggered. Mode: {mode}")

    def _unlock_now(self):
        self._privacy.deactivate()
        self._logger.event("Manual unlock triggered.")

    def _show_logs(self):
        lines = self._logger.read_recent(30)
        log_text = "\n".join(lines) if lines else "No log entries yet."
        # Show in a simple Tk window
        import tkinter as tk
        win = tk.Tk()
        win.title("PrivacyGuard - Recent Logs")
        win.geometry("800x400")
        win.configure(bg="#0d0d14")
        text = tk.Text(win, bg="#0d0d14", fg="#00ff88", font=("Courier New", 11),
                       wrap="word", bd=0, padx=10, pady=10)
        text.insert("end", log_text)
        text.config(state="disabled")
        text.pack(fill="both", expand=True)
        win.mainloop()

    def _exit_app(self):
        self._logger.info("Exiting PrivacyGuard...")
        self._detector.stop()
        self._privacy.deactivate()
        self._tray.stop()

    # ------------------------------------------------------------------ #
    #  Icon                                                                #
    # ------------------------------------------------------------------ #

    def _build_icon(self) -> Image.Image:
        """Draw a simple shield icon for the tray."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Shield shape (simplified as a rounded rectangle)
        draw.rounded_rectangle(
            [6, 4, size - 6, size - 10],
            radius=12,
            fill="#1e90ff",
        )
        draw.rounded_rectangle(
            [6, 4, size - 6, size - 10],
            radius=12,
            outline="#00ccff",
            width=2,
        )
        # Lock symbol
        draw.rectangle([22, 34, 42, 50], fill="#0a0a20")
        draw.arc([24, 24, 40, 38], start=0, end=180, fill="#0a0a20", width=4)
        return img
