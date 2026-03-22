"""
PrivacyGuard - Overlay UI
Fullscreen privacy overlay supporting all 4 modes:
  light_blur | strong_blur | blackout | freeze
"""

import tkinter as tk
import threading
import time
import cv2
import numpy as np

try:
    from PIL import Image, ImageTk, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


# Overlay colors for non-image modes
MODE_COLORS = {
    "light_blur":  ("#1a1a2e", 120),   # (hex color, alpha 0-255)
    "strong_blur": ("#0a0a14", 200),
    "blackout":    ("#000000", 255),
}

MODE_LABELS = {
    "light_blur":  "LIGHT BLUR",
    "strong_blur": "STRONG BLUR",
    "blackout":    "BLACKOUT",
    "freeze":      "SCREEN FROZEN",
}


class PrivacyOverlay:
    """
    Manages a fullscreen Tkinter window used as the privacy overlay.
    All overlay operations are marshalled to the Tk main thread.
    """

    def __init__(self):
        self._root = None
        self._canvas = None
        self._label = None
        self._visible = False
        self._tk_thread = threading.Thread(target=self._run_tk, daemon=True)
        self._tk_thread.start()
        time.sleep(0.3)  # Give Tk time to initialize

    # ------------------------------------------------------------------ #
    #  Public API (called from any thread)                                 #
    # ------------------------------------------------------------------ #

    def show(self, mode: str):
        if self._root:
            self._root.after(0, lambda: self._apply_mode(mode))

    def hide(self):
        if self._root:
            self._root.after(0, self._hide_overlay)

    # ------------------------------------------------------------------ #
    #  Tk Thread                                                           #
    # ------------------------------------------------------------------ #

    def _run_tk(self):
        self._root = tk.Tk()
        self._root.withdraw()  # Start hidden
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        # Don't use "-fullscreen" with overrideredirect; set geometry instead

        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        self._screen_size = (screen_w, screen_h)
        self._root.geometry(f"{screen_w}x{screen_h}+0+0")

        self._canvas = tk.Canvas(
            self._root,
            width=screen_w,
            height=screen_h,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill="both", expand=True)

        # Status label in corner
        self._label = tk.Label(
            self._root,
            text="",
            font=("Courier New", 13, "bold"),
            fg="#00ff88",
            bg="black",
            padx=10,
            pady=5,
        )

        self._root.mainloop()

    # ------------------------------------------------------------------ #
    #  Mode Rendering                                                      #
    # ------------------------------------------------------------------ #

    def _apply_mode(self, mode: str):
        self._root.deiconify()
        self._visible = True
        w, h = self._screen_size

        if mode == "freeze" and PIL_AVAILABLE and PYAUTOGUI_AVAILABLE:
            self._apply_freeze_mode(w, h)
        elif mode in ("light_blur", "strong_blur") and PIL_AVAILABLE and PYAUTOGUI_AVAILABLE:
            self._apply_blur_mode(mode, w, h)
        else:
            self._apply_solid_mode(mode, w, h)

        # Corner label
        label_text = f"🔐 PrivacyGuard — {MODE_LABELS.get(mode, mode)}"
        self._label.config(text=label_text)
        self._label.place(x=10, y=10)

    def _apply_solid_mode(self, mode: str, w: int, h: int):
        """Solid color overlay (works without PIL / pyautogui)."""
        color, _ = MODE_COLORS.get(mode, ("#000000", 255))
        self._canvas.delete("all")
        self._canvas.config(bg=color)
        self._canvas.create_rectangle(0, 0, w, h, fill=color, outline="")
        # Subtle grid lines for aesthetics
        for x in range(0, w, 60):
            self._canvas.create_line(x, 0, x, h, fill="#ffffff08", width=1)
        for y in range(0, h, 60):
            self._canvas.create_line(0, y, w, y, fill="#ffffff08", width=1)
        # Center icon
        cx, cy = w // 2, h // 2
        self._canvas.create_text(
            cx, cy - 30,
            text="🔒",
            font=("Segoe UI Emoji", 64),
            fill="#ffffff22",
        )
        self._canvas.create_text(
            cx, cy + 60,
            text="PRIVACY PROTECTED",
            font=("Courier New", 18, "bold"),
            fill="#ffffff30",
            letter_spacing=8,
        )

    def _apply_blur_mode(self, mode: str, w: int, h: int):
        """Screenshot + Gaussian blur overlay."""
        try:
            screenshot = pyautogui.screenshot()
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            radius = 21 if mode == "light_blur" else 51
            blurred = cv2.GaussianBlur(img, (radius, radius), 0)
            blurred_rgb = cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)

            pil_img = Image.fromarray(blurred_rgb)
            # Add tint overlay
            tint_color, alpha = MODE_COLORS.get(mode, ("#000000", 100))
            r = int(tint_color[1:3], 16)
            g = int(tint_color[3:5], 16)
            b = int(tint_color[5:7], 16)
            tint = Image.new("RGBA", pil_img.size, (r, g, b, alpha))
            pil_img = pil_img.convert("RGBA")
            pil_img = Image.alpha_composite(pil_img, tint).convert("RGB")

            self._tk_image = ImageTk.PhotoImage(pil_img)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
        except Exception:
            self._apply_solid_mode(mode, w, h)

    def _apply_freeze_mode(self, w: int, h: int):
        """Freeze: show screenshot as-is (looks frozen), overlay lock badge."""
        try:
            screenshot = pyautogui.screenshot()
            pil_img = screenshot.resize((w, h))
            self._tk_image = ImageTk.PhotoImage(pil_img)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
            # Semi-transparent dark strip at top
            self._canvas.create_rectangle(0, 0, w, 50, fill="#000000", stipple="gray50")
        except Exception:
            self._apply_solid_mode("blackout", w, h)

    def _hide_overlay(self):
        self._root.withdraw()
        self._visible = False
        self._canvas.delete("all")
