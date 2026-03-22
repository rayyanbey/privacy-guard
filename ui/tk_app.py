"""
PrivacyGuard - Tkinter Control Panel UI
Main desktop UI for controlling detection, privacy mode, and settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from core.config_manager import ConfigManager
from core.detection_engine import DetectionEngine
from core.privacy_controller import PrivacyController
from core.logger import Logger
from ui.camera_monitor import CameraMonitorWindow
from ui.overlay import PrivacyOverlay


MODES = ["light_blur", "strong_blur", "blackout", "freeze"]


class TkApp:
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

        # Register overlay so privacy activation still works in desktop UI mode.
        self._overlay = PrivacyOverlay()
        self._privacy.register_overlay(self._overlay)
        self._camera_monitor = None

        self._root = tk.Tk()
        self._root.title("PrivacyGuard Control Panel")
        self._root.geometry("920x620")
        self._root.minsize(860, 560)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_styles()
        self._build_ui()
        self._refresh_from_config()
        self._schedule_status_refresh()

    def run(self):
        self._logger.info("Tkinter UI started.")
        self._root.mainloop()

    def _build_styles(self):
        self._root.configure(bg="#0f1115")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except RuntimeError:
            # Skip theme if main loop not started yet
            pass
        style.configure("TFrame", background="#0f1115")
        style.configure("Card.TFrame", background="#171a21")
        style.configure("TLabel", background="#0f1115", foreground="#d9dee8")
        style.configure("Card.TLabel", background="#171a21", foreground="#d9dee8")
        style.configure("Header.TLabel", background="#0f1115", foreground="#8cc8ff", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background="#0f1115", foreground="#9fa8b8")
        style.configure("TButton", padding=8)
        style.configure("Accent.TButton", padding=8, foreground="#ffffff", background="#1f6feb")
        style.map("Accent.TButton", background=[("active", "#2a7fff")])

    def _build_ui(self):
        root = ttk.Frame(self._root, padding=14)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="PrivacyGuard", style="Header.TLabel").pack(side="left")
        self._status_var = tk.StringVar(value="Status: initializing")
        ttk.Label(header, textvariable=self._status_var, style="Sub.TLabel").pack(side="right")

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, pady=(12, 0))

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self._build_controls_card(left)
        self._build_settings_card(left)
        self._build_logs_card(right)

    def _build_controls_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="x")

        ttk.Label(card, text="Quick Controls", style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10)
        )

        self._system_var = tk.BooleanVar(value=True)
        self._system_btn = ttk.Button(card, text="System: ON", style="Accent.TButton", command=self._toggle_system)
        self._system_btn.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        ttk.Label(card, text="Mode", style="Card.TLabel").grid(row=1, column=1, sticky="w")
        self._mode_var = tk.StringVar(value="strong_blur")
        self._mode_combo = ttk.Combobox(card, textvariable=self._mode_var, values=MODES, state="readonly", width=16)
        self._mode_combo.grid(row=1, column=2, sticky="w", padx=(8, 8), pady=(0, 8))
        self._mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        ttk.Button(card, text="Lock Now", command=self._lock_now).grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(card, text="Unlock", command=self._unlock_now).grid(row=2, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(card, text="Refresh Logs", command=self._refresh_logs).grid(row=2, column=2, sticky="ew")
        ttk.Button(card, text="Camera Monitor", command=self._open_camera_monitor).grid(row=2, column=3, sticky="ew", padx=(8, 0))

        for idx in range(4):
            card.columnconfigure(idx, weight=1)

    def _build_settings_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(card, text="Settings", style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        self._trigger_var = tk.StringVar()
        self._cooldown_var = tk.StringVar()
        self._frame_skip_var = tk.StringVar()
        self._camera_var = tk.StringVar()
        self._tolerance_var = tk.StringVar()
        self._detection_scale_var = tk.StringVar()
        self._upsample_var = tk.StringVar()
        self._full_res_interval_var = tk.StringVar()
        self._unknown_grace_var = tk.StringVar()
        self._detector_model_var = tk.StringVar(value="hog")
        self._hotkey_var = tk.StringVar()
        self._notify_var = tk.BooleanVar(value=True)

        self._add_setting_row(card, 1, "Trigger Delay (sec)", self._trigger_var)
        self._add_setting_row(card, 2, "Cooldown (sec)", self._cooldown_var)
        self._add_setting_row(card, 3, "Frame Skip", self._frame_skip_var)
        self._add_setting_row(card, 4, "Camera Index", self._camera_var)
        self._add_setting_row(card, 5, "Face Tolerance", self._tolerance_var)
        self._add_setting_row(card, 6, "Hotkey", self._hotkey_var)

        ttk.Separator(card, orient="horizontal").grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 8))
        ttk.Label(card, text="Detection Sensitivity", style="Card.TLabel", font=("Segoe UI", 11, "bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        self._add_setting_row(card, 9, "Detection Scale (0.35-1.0)", self._detection_scale_var)
        self._add_setting_row(card, 10, "Upsample Times (0-3)", self._upsample_var)
        self._add_setting_row(card, 11, "Fallback Full-Res Interval (sec)", self._full_res_interval_var)
        self._add_setting_row(card, 12, "Unknown Loss Grace (sec)", self._unknown_grace_var)
        ttk.Label(card, text="Detector Model", style="Card.TLabel").grid(row=13, column=0, sticky="w", pady=4, padx=(0, 10))
        ttk.Combobox(
            card,
            textvariable=self._detector_model_var,
            values=["hog", "cnn"],
            state="readonly",
            width=16,
        ).grid(row=13, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(card, text="Desktop notifications enabled", variable=self._notify_var).grid(
            row=14, column=0, columnspan=2, sticky="w", pady=(8, 8)
        )

        ttk.Button(card, text="Save Settings", style="Accent.TButton", command=self._save_settings).grid(
            row=15, column=0, sticky="w", pady=(6, 0)
        )

        ttk.Button(card, text="Reload", command=self._refresh_from_config).grid(row=15, column=1, sticky="e", pady=(6, 0))

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

    def _build_logs_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Recent Logs", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self._log_text = tk.Text(
            card,
            bg="#0a0d12",
            fg="#7ee787",
            font=("Consolas", 10),
            wrap="word",
            relief="flat",
            padx=8,
            pady=8,
        )
        self._log_text.pack(fill="both", expand=True, pady=(8, 0))
        self._log_text.configure(state="disabled")

    def _add_setting_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)

    def _toggle_system(self):
        new_state = not self._config.get("system_enabled", True)
        self._config.set("system_enabled", new_state)
        if not new_state:
            self._privacy.deactivate()
        self._system_var.set(new_state)
        self._system_btn.configure(text=f"System: {'ON' if new_state else 'OFF'}")
        self._logger.info(f"System toggled via Tk UI: {'ENABLED' if new_state else 'DISABLED'}")

    def _on_mode_changed(self, _event=None):
        mode = self._mode_var.get()
        self._privacy.set_mode(mode)

    def _lock_now(self):
        self._privacy.activate()

    def _unlock_now(self):
        self._privacy.deactivate()

    def _open_camera_monitor(self):
        if self._camera_monitor is not None and not self._camera_monitor.is_closed():
            self._camera_monitor.focus()
            return
        self._camera_monitor = CameraMonitorWindow(self._root, self._detector, self._logger)
        self._logger.info("Camera monitor window opened.")

    def _save_settings(self):
        try:
            trigger_delay = max(0.1, float(self._trigger_var.get().strip()))
            cooldown = max(0.0, float(self._cooldown_var.get().strip()))
            frame_skip = max(1, int(self._frame_skip_var.get().strip()))
            camera_index = int(self._camera_var.get().strip())
            tolerance = float(self._tolerance_var.get().strip())
            tolerance = min(0.8, max(0.3, tolerance))
            detection_scale = float(self._detection_scale_var.get().strip())
            detection_scale = min(1.0, max(0.35, detection_scale))
            upsample_times = int(self._upsample_var.get().strip())
            upsample_times = min(3, max(0, upsample_times))
            full_res_interval = max(0.1, float(self._full_res_interval_var.get().strip()))
            unknown_grace = max(0.0, float(self._unknown_grace_var.get().strip()))
            detector_model = self._detector_model_var.get().strip().lower() or "hog"
            if detector_model not in {"hog", "cnn"}:
                detector_model = "hog"
            hotkey = self._hotkey_var.get().strip() or "ctrl+shift+p"

            self._config.set("trigger_delay_sec", trigger_delay)
            self._config.set("cooldown_sec", cooldown)
            self._config.set("frame_skip", frame_skip)
            self._config.set("camera_index", camera_index)
            self._config.set("face_match_tolerance", tolerance)
            self._config.set("detection_scale", detection_scale)
            self._config.set("face_upsample_times", upsample_times)
            self._config.set("full_res_scan_interval_sec", full_res_interval)
            self._config.set("unknown_loss_grace_sec", unknown_grace)
            self._config.set("face_detector_model", detector_model)
            self._config.set("hotkey_toggle", hotkey)
            self._config.set("notifications_enabled", bool(self._notify_var.get()))
            self._config.set("privacy_mode", self._mode_var.get())

            self._logger.info("Settings updated via Tk UI.")
            messagebox.showinfo("PrivacyGuard", "Settings saved.")
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid numeric values for numeric fields.")

    def _refresh_from_config(self):
        self._system_var.set(self._config.get("system_enabled", True))
        self._mode_var.set(self._config.get("privacy_mode", "strong_blur"))
        self._trigger_var.set(str(self._config.get("trigger_delay_sec", 2.0)))
        self._cooldown_var.set(str(self._config.get("cooldown_sec", 5.0)))
        self._frame_skip_var.set(str(self._config.get("frame_skip", 3)))
        self._camera_var.set(str(self._config.get("camera_index", 0)))
        self._tolerance_var.set(str(self._config.get("face_match_tolerance", 0.55)))
        self._detection_scale_var.set(str(self._config.get("detection_scale", 0.75)))
        self._upsample_var.set(str(self._config.get("face_upsample_times", 1)))
        self._full_res_interval_var.set(str(self._config.get("full_res_scan_interval_sec", 0.6)))
        self._unknown_grace_var.set(str(self._config.get("unknown_loss_grace_sec", 0.6)))
        self._detector_model_var.set(str(self._config.get("face_detector_model", "hog")))
        self._hotkey_var.set(str(self._config.get("hotkey_toggle", "ctrl+shift+p")))
        self._notify_var.set(bool(self._config.get("notifications_enabled", True)))

        self._system_btn.configure(text=f"System: {'ON' if self._system_var.get() else 'OFF'}")
        self._refresh_logs()

    def _refresh_logs(self):
        lines = self._logger.read_recent(200)
        text = "\n".join(lines) if lines else "No logs yet."
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.insert("end", text)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _schedule_status_refresh(self):
        mode = self._config.get("privacy_mode", "strong_blur")
        system_enabled = self._config.get("system_enabled", True)
        privacy_state = "ACTIVE" if self._privacy.is_active() else "INACTIVE"
        self._status_var.set(
            f"System={'ON' if system_enabled else 'OFF'} | Privacy={privacy_state} | Mode={mode}"
        )
        self._refresh_logs()
        self._root.after(2000, self._schedule_status_refresh)

    def _on_close(self):
        self._logger.info("Shutting down from Tk UI...")
        if self._camera_monitor is not None and not self._camera_monitor.is_closed():
            self._camera_monitor.close()
        self._detector.stop()
        self._privacy.deactivate()
        self._root.destroy()
