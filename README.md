# PrivacyGuard

A real-time, face-recognition-powered screen privacy system.
Runs silently in your system tray and blurs/blacks out your screen the moment a stranger looks at it.

---

## Project Structure

```
privacyguard/
├── main.py                  # Entry point — run this
├── setup_owner.py           # One-time owner face registration
├── requirements.txt
│
├── core/
│   ├── config_manager.py    # Read/write config/settings.json
│   ├── detection_engine.py  # Camera loop + face recognition
│   ├── privacy_controller.py# Activate/deactivate privacy modes
│   └── logger.py            # Timestamped log to file + console
│
├── ui/
│   ├── overlay.py           # Fullscreen Tkinter overlay (4 modes)
│   └── tray_app.py          # System tray icon + menu + hotkeys
│
├── config/
│   ├── settings.json        # Auto-created on first run
│   └── owner_encoding.pkl   # Created by setup_owner.py
│
└── logs/
    └── privacy_log.txt      # Auto-created
```

---

## Quick Start

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

> **Note on `face_recognition`:** This requires `dlib`. On Windows, install via:
> ```bash
> pip install cmake
> pip install dlib
> pip install face_recognition
> ```

### Step 2: Register your face (once)

```bash
python setup_owner.py
```

- Choose to capture from webcam or use an existing photo.
- Sit in good lighting, face the camera straight on.
- Your face encoding is saved to `config/owner_encoding.pkl`.

### Step 3: Run PrivacyGuard

```bash
python main.py
```

- A shield icon appears in your system tray.
- Detection runs silently in the background.
- Privacy activates automatically when a stranger is detected.

---

## Docker (Background + Specific Port)

PrivacyGuard now includes container support via:

- `Dockerfile`
- `docker-compose.yml`
- `container_main.py` (runs detection + health/status HTTP server)

### Run on default port `8080` in background

```bash
docker compose up -d --build
```

### Run on a specific port (example `8095`) in background

PowerShell:

```powershell
$env:PORT=8095
docker compose up -d --build
```

### Check status endpoint

```bash
curl http://localhost:8095/health
```

Sample response:

```json
{
    "status": "ok",
    "uptime_sec": 12.4,
    "system_enabled": true,
    "privacy_active": false,
    "mode": "strong_blur"
}
```

### Stop container

```bash
docker compose down
```

### Notes

- Container mode does not launch Tk desktop windows (`TkApp` / full-screen overlay UI).
- It is intended for headless/background runtime and health monitoring.
- Webcam access inside containers depends on host Docker/camera permissions.

---

## Configuration (`config/settings.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `system_enabled` | `true` | Master on/off switch |
| `privacy_mode` | `"strong_blur"` | `light_blur` / `strong_blur` / `blackout` / `freeze` |
| `trigger_delay_sec` | `1.2` | Seconds before triggering after unknown detected |
| `cooldown_sec` | `3.0` | Minimum seconds between triggers |
| `frame_skip` | `2` | Process every Nth frame (reduce CPU usage) |
| `detection_scale` | `0.75` | Fast scan resolution scale (`1.0` = full-res, higher accuracy, more CPU) |
| `face_upsample_times` | `1` | Extra upsampling for small/edge faces (higher = slower) |
| `face_detector_model` | `"hog"` | `hog` (fast CPU) or `cnn` (higher accuracy, much slower without GPU) |
| `full_res_scan_interval_sec` | `0.6` | How often to run full-res fallback scan when fast scan finds no faces |
| `unknown_loss_grace_sec` | `0.6` | Keeps unknown timer alive through brief face-detection flicker |
| `camera_index` | `0` | Webcam index (0 = default) |
| `face_match_tolerance` | `0.55` | Lower = stricter (0.4–0.6) |
| `hotkey_toggle` | `"ctrl+shift+p"` | Global hotkey to toggle system |
| `notifications_enabled` | `true` | Desktop notification on trigger |
| `log_enabled` | `true` | Write events to log file |

---

## Privacy Modes

| Mode | Effect |
|------|--------|
| `light_blur` | Semi-transparent blurred overlay |
| `strong_blur` | Heavy Gaussian blur |
| `blackout` | Fully black screen |
| `freeze` | Screenshot frozen on screen |

---

## Hotkeys & Tray Menu

- **`Ctrl+Shift+P`** — Toggle system ON/OFF
- **Right-click tray icon** for:
  - Toggle ON/OFF
  - Change privacy mode
  - Manual lock/unlock
  - View recent logs
  - Exit

---

## Detection Logic

```
Camera Frame
    ↓
Any faces?  → No  → Deactivate (if active)
    ↓ Yes
Owner present + no unknown? → Safe → Deactivate
    ↓
Unknown detected?
    ↓
Timer started → 2 seconds elapsed?
    ↓ Yes
Cooldown passed?
    ↓ Yes
→ ACTIVATE PRIVACY MODE + Send Notification + Log Event

Note: If a face is detected but cannot be encoded (common with side/partial faces),
PrivacyGuard now treats that as an unknown-risk signal.
```

---

## Troubleshooting

**`No face detected during setup`**
- Improve lighting (face the light source, not away from it)
- Remove glasses/hat if possible
- Sit 30–60 cm from the camera

**`Camera won't open`**
- Another app may be using the camera
- Try changing `camera_index` to `1` in `settings.json`

**`dlib install fails on Windows`**
- Install Visual Studio Build Tools first
- Or download a pre-built dlib wheel from: https://github.com/z-mahmud22/Dlib_Windows_Python3.x

**High CPU usage**
- Increase `frame_skip` to `5` or `6`
- Reduce camera resolution (edit `detection_engine.py` → `cap.set` lines)

---

## Log Format

```
[2025-03-21 14:32:01] [EVENT] Unknown face detected — starting timer...
[2025-03-21 14:32:03] [EVENT] PRIVACY TRIGGERED — unknown face for 2.1s exceeded 2.0s threshold.
[2025-03-21 14:32:09] [EVENT] Privacy deactivated — only owner detected.
```

---

## Function Reference

### `main.py`

- `main()`
    - Initializes `ConfigManager`, `Logger`, `PrivacyController`, and `DetectionEngine`.
    - Starts detection on a background thread.
    - Starts Tk UI (`TkApp`) on the main thread.

### `setup_owner.py`

- `capture_from_camera()`
    - Opens webcam preview and captures a photo when SPACE is pressed.
- `encode_face(image_path)`
    - Creates a face embedding for the owner from an image file.
- `main()`
    - Runs one-time owner registration flow and writes `config/owner_encoding.pkl`.

### `core/config_manager.py`

- `ConfigManager.__init__()`
    - Loads config file and ensures defaults exist.
- `ConfigManager._load()`
    - Reads JSON and merges missing keys with defaults.
- `ConfigManager._save()`
    - Persists current config to disk.
- `ConfigManager.get(key, fallback)`
    - Reads a config value.
- `ConfigManager.set(key, value)`
    - Updates a config value and saves.
- `ConfigManager.all()`
    - Returns full config dict copy.

### `core/logger.py`

- `Logger._write(level, message)`
    - Writes timestamped log lines to console and file.
- `Logger.info()/warn()/error()/event()`
    - Convenience level methods.
- `Logger.read_recent(n)`
    - Reads last `n` log lines.

### `core/privacy_controller.py`

- `register_overlay(overlay)`
    - Connects UI overlay implementation.
- `activate()`
    - Enables privacy mode and sends desktop notification.
- `deactivate()`
    - Disables overlay and clears active state.
- `is_active()`
    - Returns current privacy state.
- `set_mode(mode)`
    - Changes privacy mode and reapplies if active.
- `_send_notification(mode)`
    - Sends notification through `plyer` (if enabled).

### `core/detection_engine.py`

- `run()`
    - Main camera loop. Publishes monitor frames and runs face detection/recognition logic.
- `stop()/pause()/resume()`
    - Controls engine loop state.
- `get_latest_debug_frame()`
    - Returns most recent annotated frame for camera monitor window.
- `get_camera_index()`
    - Returns configured camera index for fallback preview.
- `_load_owner_encoding()`
    - Loads owner embedding from disk.
- `_open_camera()`
    - Opens webcam and sets capture resolution.
- `_process_frame(frame)`
    - Detects faces, labels owner/unknown/unencoded, draws boxes, updates timer state.
- `_handle_unknown_detected()`
    - Unknown timer + delay/cooldown trigger logic.
- `_reset_timer()`
    - Resets unknown timer with grace period for brief flicker.
- `_set_latest_debug_frame(frame)`
    - Thread-safe update of monitor frame buffer.
- `_draw_face_boxes(frame, locations, labels, scale)`
    - Draws colored face rectangles and labels.

### `ui/tk_app.py`

- `TkApp.__init__()`
    - Creates main control panel and registers overlay.
- `run()`
    - Starts Tk event loop.
- `_build_styles()`
    - Applies widget styles/colors.
- `_build_ui()`
    - Builds top-level layout and cards.
- `_build_controls_card()/ _build_settings_card()/ _build_logs_card()`
    - Build UI sections.
- `_add_setting_row(parent, row, label, variable)`
    - Reusable entry row helper.
- `_toggle_system()`
    - ON/OFF master toggle.
- `_on_mode_changed()`
    - Applies selected privacy mode.
- `_lock_now()/ _unlock_now()`
    - Manual privacy activation controls.
- `_open_camera_monitor()`
    - Opens/focuses separate camera monitor window.
- `_save_settings()`
    - Validates and saves all settings from UI fields.
- `_refresh_from_config()`
    - Reloads UI fields from config.
- `_refresh_logs()`
    - Refreshes log viewer text area.
- `_schedule_status_refresh()`
    - Updates status line and logs periodically.
- `_on_close()`
    - Clean shutdown for detector, overlay, monitor, and window.

### `ui/camera_monitor.py`

- `CameraMonitorWindow.__init__()`
    - Creates separate monitor window and starts refresh loop.
- `is_closed()/focus()/close()`
    - Monitor lifecycle helpers.
- `_update_frame()`
    - Pulls latest annotated frame; falls back to direct camera feed when needed.
- `_show_frame(frame)`
    - Resizes and renders frame into Tk label.
- `_read_fallback_frame()`
    - Reads direct camera frame for fallback preview mode.

### `ui/overlay.py`

- `PrivacyOverlay.__init__()`
    - Starts dedicated Tk thread for full-screen overlay rendering.
- `show(mode)/hide()`
    - Public overlay controls.
- `_run_tk()`
    - Creates fullscreen canvas window.
- `_apply_mode(mode)`
    - Dispatches to blur/freeze/solid renderer.
- `_apply_solid_mode(mode, w, h)`
    - Draws dark screen protection layer.
- `_apply_blur_mode(mode, w, h)`
    - Screenshot + blur + tint overlay.
- `_apply_freeze_mode(w, h)`
    - Screenshot freeze effect.
- `_hide_overlay()`
    - Withdraws overlay window.

### `ui/tray_app.py`

- `TrayApp.__init__()`
    - Creates tray app and registers global hotkey.
- `run()`
    - Starts tray icon event loop.
- `_build_menu()`
    - Builds dynamic tray menu with mode selectors.
- `_toggle_system()`
    - Toggles system enabled state.
- `_make_mode_setter(mode)`
    - Returns callback that sets privacy mode.
- `_lock_now()/ _unlock_now()`
    - Manual lock controls from tray.
- `_show_logs()`
    - Opens small logs window.
- `_exit_app()`
    - Graceful shutdown from tray menu.
- `_build_icon()`
    - Draws tray icon image.

---

## GUI Button Guide

### Main Control Panel (`TkApp`)

- `System: ON/OFF`
    - Enables or disables detection globally.
- `Mode` dropdown
    - Chooses overlay mode (`light_blur`, `strong_blur`, `blackout`, `freeze`).
- `Lock Now`
    - Immediately applies privacy overlay.
- `Unlock`
    - Removes privacy overlay.
- `Refresh Logs`
    - Reloads visible log panel.
- `Camera Monitor`
    - Opens separate live camera monitor with face highlights.
- `Save Settings`
    - Validates and writes current settings to `config/settings.json`.
- `Reload`
    - Re-reads settings from file and refreshes UI fields.
- `Desktop notifications enabled` (checkbox)
    - Toggles desktop pop-up notifications on trigger.

### Camera Monitor Window

- Window close (`X`)
    - Stops monitor refresh loop and releases fallback camera (if opened).

### Tray Menu (`TrayApp`)

- `System: ON`
    - Toggles monitoring system.
- `Privacy Mode` submenu
    - Picks privacy mode directly from tray.
- `Lock Now`
    - Manual lock.
- `Unlock`
    - Manual unlock.
- `View Logs`
    - Opens recent logs window.
- `Exit`
    - Stops detector and exits app.
