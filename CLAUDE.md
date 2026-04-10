# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```cmd
# With console output (for debugging)
venv\Scripts\python.exe main.py

# Without console window (normal use)
venv\Scripts\pythonw.exe main.py
```

**Always kill all running instances before starting a new one.** Use this exact sequence every time:

```bash
powershell -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | Stop-Process -Force"
venv/Scripts/python.exe main.py &
```

Use PowerShell's `Stop-Process` — `taskkill` via bash is unreliable and leaves ghost tray icons.
This ensures no stale processes are left holding the mic, hotkey listener, or tray icon.

Always use **backslashes** in CMD, **forward slashes** in bash/PowerShell.

## Setup

```cmd
install.bat          # Creates venv, installs requirements.txt
```

Requires a `.env` file with `OPENAI_API_KEY=sk-...` in the project root.

## Architecture

### Threading Model
This is the most critical thing to understand. Four threads run concurrently:

- **Main thread** — Qt `app.exec()` event loop. Only this thread may touch Qt widgets. All other threads send signals via `pyqtSignal` (see `_Bridge` in `main.py`).
- **keyboard OS thread** — Fires `on_hotkey_press` / `on_hotkey_release` via the `keyboard` library. These callbacks must return immediately — they emit signals or set threading events. Never block here.
- **RealtimeTranscriber thread** — Runs an asyncio event loop (`_run_loop`). Manages the OpenAI WebSocket, audio sender coroutine, and event receiver coroutine.
- **sounddevice callback thread** — Internal to PortAudio. Calls `_start_mic_prebuffer`'s callback every 20ms. Must be fast; uses `asyncio.run_coroutine_threadsafe` to enqueue audio.

### Cross-thread UI updates
Worker threads must never touch Qt widgets directly. Two mechanisms are used:

- **`_Bridge` (main.py)** — `QObject` with `pyqtSignal`s for `set_ui_sig`, `open_settings_sig`, `quit_sig`. Hotkey/transcriber threads emit these; slots on the main thread handle them.
- **`OverlayWindow._sig`** — The overlay has its own internal `pyqtSignal(str, str)` so `set_state()` is safe to call from any thread.
- **`_HotkeyCapture._update_sig`** — Same pattern for the hotkey capture dialog.

Old Tkinter pattern (`root.after(0, fn)`) is gone — do not use it.

### Recording State Machine (`app_state.py`)
`IDLE → RECORDING → TRANSCRIBING → IDLE` (or `→ ERROR → IDLE`).
State transitions happen in `main.py`'s `on_hotkey_press` / `on_hotkey_release`.

### Real-time Transcription Flow (`realtime_transcriber.py`)
1. **Hotkey pressed** → `start()` called → mic opens immediately and buffers audio into `_pre_buffer` (a `deque`) before the WebSocket is ready.
2. WebSocket connects to `wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview`.
3. Session configured with `input_audio_transcription.model = gpt-4o-transcribe` and server VAD.
4. `_flush_prebuffer()` sends all pre-captured audio, then `_send_audio()` continues streaming.
5. Server VAD detects speech pauses → emits `conversation.item.input_audio_transcription.delta` events → each delta is injected immediately.
6. **Hotkey released** → `stop()` called → mic stops, `stop_event` set, remaining audio committed via `input_audio_buffer.commit`.

**Two separate model names**: the WebSocket connection uses `REALTIME_MODEL = "gpt-4o-realtime-preview"`; the actual transcription quality uses `gpt-4o-transcribe` (or `gpt-4o-mini-transcribe`) in the session config. These are different.

### Text Injection (`text_injector.py`)
Two modes:
- **Batch** (`inject(text)`): saves clipboard, pastes full text, restores clipboard.
- **Streaming** (`start_stream()` → repeated `inject_delta(delta)` → `end_stream()`): saves clipboard once at start, pastes each delta without restore, restores only at end.

### Settings Dialog (`settings_dialog.py`)
`SettingsDialog` is a plain Python wrapper; `SettingsWindow` is the actual `FramelessWindow`.
- Opening is triggered via `bridge.open_settings_sig.emit()` → marshalled to main thread → `_settings_dialog.show()`.
- Uses **PyQt6-Frameless-Window** (`qframelesswindow.FramelessWindow`) for the custom title bar and Windows 11 Mica effect (`windowEffect.setMicaEffect`). Title bar is set to `transparent` so Mica shows through it.
- All Fluent-style visuals (combobox border-bottom, toggle switch) are done with custom QSS + `_Toggle(QAbstractButton)` with `QPropertyAnimation`. No qfluentwidgets dependency.
- **Background layering**: The scroll content widget uses `WA_StyledBackground = True` + `background: #202020` (solid, like the HTML mockup). The QSS rule `QScrollArea > QWidget > QWidget { background: #202020; }` reinforces this. Child widgets must NOT set `background: transparent` — doing so causes Qt to composite against the system white, producing white outlines around widgets.
- **`_Slider`** — `QSlider` subclass with custom `paintEvent` that draws a perfectly circular handle via `QPainter`. The QSS handle is set to `width: 0; height: 0` to hide the default handle; the painter draws a `_R = 7px` radius circle on top. This avoids the pill-shape distortion caused by Qt's `margin: -Npx 0` expanding the handle's bounding rect at high DPI.
- **`_KeyboardIcon`** — `QWidget` subclass using `QSvgRenderer` to render the keyboard SVG icon from the HTML mockup (keyboard outline + key dots + spacebar) inside a subtle `rgba(255,255,255,13)` rounded badge.
- **`_HotkeyCapture`** — modal hotkey picker. Uses pynput on a background thread; `_update_sig = pyqtSignal(str)` marshals display updates to the main thread. `exec()` creates a `QEventLoop` stored as `self._loop`; `closeEvent` calls `self._loop.quit()` to unblock it. `QTimer.singleShot(0, self.close)` is used from the pynput thread to safely trigger close on the Qt thread.

### Overlay (`overlay.py`)
Frameless translucent pill window (`Qt.Tool` + `WA_TranslucentBackground`).
- Always on top, click-through via `WS_EX_LAYERED | WS_EX_TRANSPARENT` (Windows ctypes).
- `set_state()` is thread-safe (emits `_sig` pyqtSignal).
- Positions: `bottom-right`, `bottom-left`, `top-right`, `top-left`.

### Tray Icon (`tray_icon.py`)
`QSystemTrayIcon` — runs on the main thread. No pystray.
- `set_state("IDLE"|"RECORDING"|"TRANSCRIBING"|"ERROR")` updates icon color and tooltip.
- `update_hotkey_tooltip()` called after settings save to reflect new hotkey combo.

### Hotkey Listener (`hotkey_listener.py`)
Uses the `keyboard` library with `suppress=True` on `add_hotkey()` so the hotkey combo is fully consumed and never leaks to other applications. pynput is only used inside `_HotkeyCapture` for the one-shot capture dialog.

## Configuration

`config.json` is auto-created with defaults on first run. Key tuning knobs:
- `transcription.vad_silence_ms` (default 300) — ms of silence before a speech segment is committed. Lower = more frequent text appearance but more fragmented.
- `transcription.vad_threshold` (default 0.5) — VAD sensitivity (0.0–1.0). Lower catches quieter voices.
- `audio.min_duration_seconds` (default 0.3) — ignores accidental short presses.

## Known Limitations
- UAC-elevated windows (Task Manager, etc.) cannot receive pasted text without running the app elevated.
- The `input_audio_buffer_commit_empty` error from the OpenAI API is silently ignored — it occurs on very short/silent hotkey presses and is harmless.
- Mica effect requires Windows 11. On Windows 10 the window falls back to a solid dark background.
