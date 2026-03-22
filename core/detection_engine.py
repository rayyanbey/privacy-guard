"""
PrivacyGuard - Detection Engine
Background camera loop with face recognition.
Owner vs stranger logic with timer & cooldown.
"""

import cv2
import face_recognition
import pickle
import os
import time
import threading
import numpy as np
from core.config_manager import ConfigManager
from core.privacy_controller import PrivacyController
from core.logger import Logger

ENCODING_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "owner_encoding.pkl")


class DetectionEngine:
    def __init__(self, config: ConfigManager, privacy_ctrl: PrivacyController, logger: Logger):
        self._config = config
        self._privacy = privacy_ctrl
        self._logger = logger
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

        # State
        self._unknown_start_time = None
        self._unknown_last_seen_time = None
        self._last_trigger_time = 0.0
        self._last_full_res_scan = 0.0
        self._latest_debug_frame = None
        self._owner_encoding = self._load_owner_encoding()


    def run(self):
        """Main detection loop. Runs in a background thread."""
        self._running = True
        warned_owner_missing = False

        cap = self._open_camera()
        if cap is None:
            return

        self._logger.info("Camera opened. Detection loop active.")
        frame_count = 0

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self._logger.error("Camera read failed. Retrying...")
                    time.sleep(1)
                    cap = self._open_camera()
                    if cap is None:
                        break
                    continue

                if not self._config.get("system_enabled", True) or self._paused:
                    info_frame = frame.copy()
                    cv2.putText(
                        info_frame,
                        "Detection paused/off",
                        (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (170, 170, 170),
                        2,
                    )
                    self._set_latest_debug_frame(info_frame)
                    time.sleep(0.1)
                    continue

                if self._owner_encoding is None:
                    if not warned_owner_missing:
                        self._logger.error("Owner encoding not found. Run setup_owner.py first.")
                        warned_owner_missing = True
                    info_frame = frame.copy()
                    cv2.putText(
                        info_frame,
                        "Owner not registered",
                        (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 165, 255),
                        2,
                    )
                    self._set_latest_debug_frame(info_frame)
                    time.sleep(0.1)
                    continue

                frame_count += 1
                skip = self._config.get("frame_skip", 3)
                if frame_count % skip != 0:
                    self._set_latest_debug_frame(frame)
                    continue

                self._process_frame(frame)

        except Exception as e:
            self._logger.error(f"Detection engine crashed: {e}")
        finally:
            cap.release()
            self._logger.info("Camera released.")

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def get_latest_debug_frame(self):
        """Return latest annotated frame for camera monitor UI."""
        with self._lock:
            if self._latest_debug_frame is None:
                return None
            return self._latest_debug_frame.copy()

    def get_camera_index(self) -> int:
        return int(self._config.get("camera_index", 0))

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _load_owner_encoding(self):
        path = os.path.abspath(ENCODING_PATH)
        if not os.path.exists(path):
            self._logger.warn(f"Owner encoding not found at {path}")
            return None
        try:
            with open(path, "rb") as f:
                enc = pickle.load(f)
            self._logger.info("Owner encoding loaded successfully.")
            return enc
        except Exception as e:
            self._logger.error(f"Failed to load owner encoding: {e}")
            return None

    def _open_camera(self):
        idx = self._config.get("camera_index", 0)
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            self._logger.error(f"Cannot open camera index {idx}. Check config or connections.")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return cap

    def _process_frame(self, frame: np.ndarray):
        debug_frame = frame.copy()

        # Fast pass on a downscaled frame.
        detection_scale = float(self._config.get("detection_scale", 0.75))
        detection_scale = min(1.0, max(0.35, detection_scale))
        upsample_times = int(self._config.get("face_upsample_times", 1))
        upsample_times = max(0, min(3, upsample_times))
        detector_model = str(self._config.get("face_detector_model", "hog")).lower()
        if detector_model not in {"hog", "cnn"}:
            detector_model = "hog"

        small = cv2.resize(frame, (0, 0), fx=detection_scale, fy=detection_scale)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(
            rgb,
            number_of_times_to_upsample=upsample_times,
            model=detector_model,
        )
        active_rgb = rgb
        location_scale = 1.0 / detection_scale

        # Fallback scan: if fast pass misses faces, occasionally try full resolution.
        if not locations:
            now = time.time()
            fallback_interval = float(self._config.get("full_res_scan_interval_sec", 0.6))
            fallback_interval = max(0.1, fallback_interval)
            if now - self._last_full_res_scan >= fallback_interval:
                self._last_full_res_scan = now
                full_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locations = face_recognition.face_locations(
                    full_rgb,
                    number_of_times_to_upsample=max(upsample_times, 1),
                    model="hog",
                )
                if locations:
                    active_rgb = full_rgb
                    location_scale = 1.0
                    self._logger.info(f"[DEBUG] Full-res fallback found {len(locations)} face(s).")

        if not locations:
            cv2.putText(debug_frame, "No faces detected", (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (170, 170, 170), 2)
            self._set_latest_debug_frame(debug_frame)

        if not locations:
            # No faces at all
            self._reset_timer()
            if self._privacy.is_active():
                self._privacy.deactivate()
                self._logger.event("Privacy deactivated — no faces detected.")
            return

        encodings = face_recognition.face_encodings(active_rgb, locations)
        tolerance = self._config.get("face_match_tolerance", 0.55)

        owner_present = False
        unknown_present = False
        face_labels = ["UNENCODED"] * len(locations)

        for idx, enc in enumerate(encodings):
            match = face_recognition.compare_faces(
                [self._owner_encoding], enc, tolerance=tolerance
            )
            if match[0]:
                owner_present = True
                if idx < len(face_labels):
                    face_labels[idx] = "OWNER"
                self._logger.info(f"[DEBUG] Face {idx+1}/{len(encodings)}: OWNER MATCH")
            else:
                unknown_present = True
                if idx < len(face_labels):
                    face_labels[idx] = "UNKNOWN"
                self._logger.info(f"[DEBUG] Face {idx+1}/{len(encodings)}: UNKNOWN")

        # If a face is detected but cannot be encoded (common with side/partial faces),
        # treat that as unknown risk unless owner is confidently the only visible face.
        unencoded_faces = max(0, len(locations) - len(encodings))
        if unencoded_faces > 0 and (not owner_present or len(locations) > 1):
            unknown_present = True
            self._logger.info(
                f"[DEBUG] {unencoded_faces} unencoded face(s) treated as UNKNOWN risk."
            )

        self._draw_face_boxes(debug_frame, locations, face_labels, location_scale)
        self._set_latest_debug_frame(debug_frame)

        self._logger.info(f"[DEBUG] Frame result: {len(encodings)} faces | owner={owner_present}, unknown={unknown_present}")

        if owner_present and not unknown_present:
            # Only owner → safe
            self._reset_timer()
            if self._privacy.is_active():
                self._privacy.deactivate()
                self._logger.event("Privacy deactivated — only owner detected.")
            return

        if unknown_present:
            self._handle_unknown_detected()
        else:
            self._reset_timer()

    def _handle_unknown_detected(self):
        now = time.time()
        delay = self._config.get("trigger_delay_sec", 1.2)
        cooldown = self._config.get("cooldown_sec", 5.0)
        self._unknown_last_seen_time = now

        if self._unknown_start_time is None:
            self._unknown_start_time = now
            self._logger.info("Unknown face detected — starting timer...")
            return

        elapsed = now - self._unknown_start_time
        if elapsed >= delay:
            # Check cooldown
            if now - self._last_trigger_time < cooldown:
                return  # Too soon since last trigger
            if not self._privacy.is_active():
                self._privacy.activate()
                self._last_trigger_time = now
                self._logger.event("PRIVACY TRIGGERED — unknown face for "
                                   f"{elapsed:.1f}s exceeded {delay}s threshold.")

    def _reset_timer(self):
        # Keep timer alive for a short period to avoid restarting on brief detection flicker.
        now = time.time()
        grace = float(self._config.get("unknown_loss_grace_sec", 0.6))
        grace = max(0.0, grace)
        if (
            self._unknown_start_time is not None
            and self._unknown_last_seen_time is not None
            and (now - self._unknown_last_seen_time) < grace
        ):
            return

        self._unknown_start_time = None
        self._unknown_last_seen_time = None

    def _set_latest_debug_frame(self, frame: np.ndarray):
        with self._lock:
            self._latest_debug_frame = frame

    def _draw_face_boxes(self, frame: np.ndarray, locations, labels, scale: float):
        h, w = frame.shape[:2]
        for i, (top, right, bottom, left) in enumerate(locations):
            t = max(0, min(h - 1, int(top * scale)))
            r = max(0, min(w - 1, int(right * scale)))
            b = max(0, min(h - 1, int(bottom * scale)))
            l = max(0, min(w - 1, int(left * scale)))
            label = labels[i] if i < len(labels) else "UNKNOWN"

            if label == "OWNER":
                color = (0, 200, 0)
            elif label == "UNENCODED":
                color = (0, 165, 255)
            else:
                color = (0, 0, 255)

            cv2.rectangle(frame, (l, t), (r, b), color, 2)
            text_y = t - 8 if t > 20 else t + 22
            cv2.putText(frame, label, (l, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
