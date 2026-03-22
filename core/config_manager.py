"""
PrivacyGuard - Configuration Manager
Reads and writes config/settings.json
"""

import json
import os
from typing import Any

DEFAULT_CONFIG = {
    "system_enabled": True,
    "privacy_mode": "strong_blur",       # light_blur | strong_blur | blackout | freeze
    "trigger_delay_sec": 1.2,            # seconds unknown must be seen before triggering
    "cooldown_sec": 3.0,                 # seconds between consecutive triggers
    "frame_skip": 2,                     # process every Nth frame
    "detection_scale": 0.75,             # fast pass scale (1.0 = full resolution)
    "face_upsample_times": 1,            # increases small/edge face detect rate (CPU tradeoff)
    "face_detector_model": "hog",       # hog | cnn (cnn is slower, needs dlib CUDA for speed)
    "full_res_scan_interval_sec": 0.6,   # fallback full-res scan cadence when fast pass sees none
    "unknown_loss_grace_sec": 0.6,       # keep unknown timer alive through short detection dropouts
    "camera_index": 0,
    "face_match_tolerance": 0.55,        # lower = stricter (0.4–0.6 recommended)
    "hotkey_toggle": "ctrl+shift+p",
    "notifications_enabled": True,
    "log_enabled": True,
    "overlay_opacity": 180,              # 0–255 (for light_blur mode)
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")


class ConfigManager:
    def __init__(self):
        self._path = os.path.abspath(CONFIG_PATH)
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    saved = json.load(f)
                # Merge with defaults so new keys always exist
                merged = {**DEFAULT_CONFIG, **saved}
                return merged
            except Exception:
                pass
        # Write defaults on first run
        self._data = DEFAULT_CONFIG.copy()
        self._save()
        return DEFAULT_CONFIG.copy()

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, fallback: Any = None) -> Any:
        return self._data.get(key, fallback)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self._save()

    def all(self) -> dict:
        return dict(self._data)
