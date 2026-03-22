"""
PrivacyGuard - Camera Monitor UI
Shows live camera preview with owner/unknown highlights.
"""

import tkinter as tk
from PIL import Image, ImageTk
import cv2


class CameraMonitorWindow:
    def __init__(self, root: tk.Tk, detector, logger):
        self._root = root
        self._detector = detector
        self._logger = logger

        self._win = tk.Toplevel(root)
        self._win.title("PrivacyGuard - Camera Monitor")
        self._win.geometry("760x560")
        self._win.minsize(520, 400)
        self._win.configure(bg="#11151b")
        self._win.protocol("WM_DELETE_WINDOW", self.close)

        self._title = tk.Label(
            self._win,
            text="Live Camera Angle (OWNER / UNKNOWN)",
            bg="#11151b",
            fg="#d9dee8",
            font=("Segoe UI", 11, "bold"),
        )
        self._title.pack(anchor="w", padx=10, pady=(10, 6))

        self._image_label = tk.Label(self._win, bg="#0a0d12")
        self._image_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._hint = tk.Label(
            self._win,
            text="Green=OWNER  Red=UNKNOWN  Orange=UNENCODED",
            bg="#11151b",
            fg="#9fa8b8",
            font=("Segoe UI", 9),
        )
        self._hint.pack(anchor="w", padx=10, pady=(0, 10))

        self._photo_ref = None
        self._closed = False
        self._loop_id = None
        self._no_frame_ticks = 0
        self._fallback_cap = None
        self._using_fallback = False

        self._update_frame()

    def is_closed(self) -> bool:
        return self._closed or not self._win.winfo_exists()

    def focus(self):
        if self.is_closed():
            return
        self._win.deiconify()
        self._win.lift()
        self._win.focus_force()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._loop_id is not None:
            try:
                self._win.after_cancel(self._loop_id)
            except Exception:
                pass
            self._loop_id = None
        if self._fallback_cap is not None:
            try:
                self._fallback_cap.release()
            except Exception:
                pass
            self._fallback_cap = None
        try:
            self._win.destroy()
        except Exception:
            pass

    def _update_frame(self):
        if self.is_closed():
            return
        try:
            frame = self._detector.get_latest_debug_frame()
            if frame is None:
                self._no_frame_ticks += 1
                if self._no_frame_ticks >= 20:
                    fallback = self._read_fallback_frame()
                    if fallback is not None:
                        self._using_fallback = True
                        if self._title.winfo_exists():
                            self._title.configure(text="Live Camera Angle (Fallback Preview)")
                        self._show_frame(fallback)
                        self._loop_id = self._win.after(66, self._update_frame)
                        return

                if self._image_label.winfo_exists():
                    self._image_label.configure(text="Waiting for camera frames...", fg="#b9c2d0")
                self._loop_id = self._win.after(100, self._update_frame)
                return

            self._no_frame_ticks = 0
            if self._using_fallback:
                self._using_fallback = False
                if self._title.winfo_exists():
                    self._title.configure(text="Live Camera Angle (OWNER / UNKNOWN)")

            self._show_frame(frame)
            self._loop_id = self._win.after(66, self._update_frame)
        except tk.TclError as e:
            # Window/widget may be destroyed while callback is mid-flight.
            self._logger.warn(f"Camera monitor UI closed during update: {e}")
            self.close()

    def _show_frame(self, frame):
        if self.is_closed() or not self._image_label.winfo_exists():
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        box_w = max(200, self._image_label.winfo_width())
        box_h = max(150, self._image_label.winfo_height())
        image.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(image=image, master=self._win)
        self._photo_ref = photo
        self._image_label.configure(image=photo, text="")

    def _read_fallback_frame(self):
        if self._fallback_cap is None:
            index = 0
            try:
                index = self._detector.get_camera_index()
            except Exception:
                index = 0
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                return None
            self._fallback_cap = cap

        ret, frame = self._fallback_cap.read()
        if not ret:
            return None

        cv2.putText(
            frame,
            "Fallback monitor feed",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 165, 255),
            2,
        )
        return frame
