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
Five threads run concurrently:

- **Main thread** — Qt `app.exec()` event loop. Only this thread may touch Qt widgets. All other threads communicate via `pyqtSignal`.
- **HotkeyListener polling thread** — Spawned per keypress. Polls `keyboard.is_pressed()` every 20ms to detect release. Fires `on_hotkey_release` callback when combo breaks.
- **RealtimeTranscriber thread** — Runs an asyncio event loop (`_run_loop`). Manages the OpenAI WebSocket, `_send_audio` coroutine, and `_receive_events` coroutine.
- **sounddevice callback thread** — Internal to PortAudio. Calls the mic callback every 20ms. Uses `asyncio.run_coroutine_threadsafe` to enqueue audio chunks.
- **DeltaFlusher thread** — Spawned by `TextInjector.start_stream()`. Wakes every 80ms, batches buffered deltas into a single `pyperclip.copy` + Ctrl+V, then sleeps again. Stopped by `end_stream()`.

### Cross-thread UI updates
Worker threads must never touch Qt widgets directly. Mechanisms used:

- **`_Bridge` (main.py)** — `QObject` with `pyqtSignal`s for `set_ui_sig`, `open_settings_sig`, `quit_sig`.
- **`OverlayWindow._sig`** — Internal `pyqtSignal(str, str)` so `set_state()` is safe from any thread.
- **`_HotkeyCapture._update_sig` / `_close_sig`** — Signals marshal display updates and close events from the pynput thread to the Qt thread. Do NOT use `QTimer.singleShot` from non-Qt threads — it schedules on the calling thread's event loop which doesn't exist, so it silently never fires.

### Recording State Machine (`app_state.py`)
`IDLE → RECORDING → TRANSCRIBING → IDLE` (or `→ ERROR → IDLE`).

**Critical ordering in `on_hotkey_press`**: `active_transcriber` must be set before state changes to `RECORDING`. If state is set first, a fast hotkey release can pass the state check in `on_hotkey_release` but find `active_transcriber = None`, causing stop to be a no-op and leaving the session running forever.

### Real-time Transcription Flow (`realtime_transcriber.py`)
1. **Hotkey pressed** → `RealtimeTranscriber` created and stored in `active_transcriber`, then state set to `RECORDING`. Mic opens immediately, buffering into `_pre_buffer` before WebSocket is ready.
2. WebSocket connects to `wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview`.
3. Session configured with `input_audio_transcription.model = gpt-4o-transcribe` and server VAD.
4. `_flush_prebuffer()` sends all pre-captured audio; `_send_audio()` continues streaming live.
5. Server VAD emits `conversation.item.input_audio_transcription.delta` events → each delta is injected via `run_in_executor` (off the event loop) so `_send_audio` is never starved.
6. **Hotkey released** → duration since press is checked against `min_duration_seconds`. If too short, `cancel()` is called — this sets `_cancelled = True` then calls `stop()`, and `_session()` exits before the commit step. State returns to IDLE with no API call. For normal releases, `stop()` is called → mic stops, `_stop_event` set. Before committing, sends `session.update` with `turn_detection: None` to disable server VAD — this prevents the server from waiting out its silence window (e.g. 600ms) before processing the final audio. Then commits remaining audio via `input_audio_buffer.commit`.

**Race condition guard**: `_stop_requested` flag is set in `stop()`. If `stop()` is called before `_session()` has created `_stop_event`, the flag causes `_stop_event` to be set immediately when it's created.

**`cancel()` vs `stop()`**: `cancel()` is for accidental short presses — it sets `_cancelled` so `_session()` skips the VAD-disable + commit sequence entirely and just closes the WebSocket. `stop()` is the normal release path that commits audio.

**Two separate model names**: The WebSocket URL uses `REALTIME_MODEL = "gpt-4o-realtime-preview"`; transcription quality is set by `gpt-4o-transcribe` (or `gpt-4o-mini-transcribe`) inside the session config.

**Do not block the asyncio event loop from `_receive_events`**: The delta callback (`_on_delta`) calls `inject_delta` which uses `time.sleep`. Always call it via `await loop.run_in_executor(None, self._on_delta, delta)` — blocking the event loop starves `_send_audio`, creating apparent audio gaps that trigger premature VAD commits on the server.

### Text Injection (`text_injector.py`)
Streaming mode only (batch mode exists but is unused in the main flow):
- `start_stream()` — saves clipboard once, then starts the `DeltaFlusher` background thread.
- `inject_delta(delta)` — appends to an internal `_delta_buffer` list under `_buffer_lock`. Does not paste directly; the flusher handles that.
- `end_stream()` — signals the flusher to stop, joins it (up to 1s), then calls `_flush_once()` to drain any deltas that arrived after the last tick, then restores the original clipboard.
- `_flush_loop()` — runs on the DeltaFlusher thread. Sleeps `FLUSH_INTERVAL` (80ms), calls `_flush_once()`, repeats until `_flush_stop` is set.
- `_flush_once()` — grabs all buffered text in one lock, joins it, copies to clipboard, waits `STREAM_PASTE_DELAY` (30ms), sends Ctrl+V. Single paste per flush tick regardless of how many deltas arrived.

**Why batching**: Each Ctrl+V carries ~30ms of clipboard-settle delay. Batching many rapid deltas into one paste reduces that overhead and avoids flooding the target app with keystrokes.

### Settings Dialog (`settings_dialog.py`)
`SettingsDialog` is a plain Python wrapper; `SettingsWindow` is the actual `QWidget`.

- Uses a **native Windows title bar** (plain `QWidget`, no `qframelesswindow`). Dark mode is applied via `DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE=20, 1)` in `showEvent` via `QTimer.singleShot(0, ...)`.
- All Fluent-style visuals (combobox, toggle switch, slider) done with custom QSS + subclasses. No external widget library.
- **QSS scoping**: Rules set on a parent widget cascade to descendants, BUT if an intermediate widget has its own `setStyleSheet`, its children only see that intermediate stylesheet. Fix: use `setObjectName` + `WA_StyledBackground` on intermediate widgets and control their background via the root QSS rather than inline `setStyleSheet`.
- **`QFrame` border bleeding**: `QLabel` is a subclass of `QFrame`. A `QFrame { border: ... }` rule in a group's stylesheet applies to all `QLabel` children too. Fix: use `QFrame#group { ... }` and add explicit `QLabel { border: none; }` in the same stylesheet.
- **`_Slider`** — `QSlider` subclass. Ignores wheel events unless focused (prevents accidental value changes when scrolling). Custom `paintEvent` draws a circular handle via `QPainter`.
- **`_WheelGuard`** — `QObject` event filter. Installed on all `QComboBox` instances. Ignores wheel events unless the widget has focus, so scrolling over dropdowns scrolls the parent `QScrollArea` instead.
- **`_HotkeyCapture`** — Modal hotkey picker. Uses pynput on a background thread. Close is triggered via `_close_sig = pyqtSignal()` emitted from the pynput thread — this is the correct cross-thread pattern. Never call `QTimer.singleShot` from a pynput callback.
- **Dropdown arrow**: `QComboBox::down-arrow` requires `image: url(...)` — the CSS border triangle trick does not work in Qt QSS.

### Hotkey Listener (`hotkey_listener.py`)
Uses the `keyboard` library with `suppress=True` on `add_hotkey()` so the combo is consumed and never leaks to other apps.

**Release detection via polling**: `on_release_key` is NOT used. When `suppress=True`, the keyboard library's hook intercepts both press and release events, so `on_release_key` callbacks may never fire. Instead, when the hotkey fires, a polling thread is spawned that calls `keyboard.is_pressed(combo_str)` every 20ms. `keyboard.is_pressed()` reads the library's internal key-state table (updated before suppression decisions), so it correctly reflects the physical key state even with suppression active. Do NOT use `GetAsyncKeyState` — it reads OS-level state which is not updated for suppressed events.

### Overlay (`overlay.py`)
Frameless translucent pill window (`Qt.Tool` + `WA_TranslucentBackground`).
- Always on top, click-through via `WS_EX_LAYERED | WS_EX_TRANSPARENT` (Windows ctypes).
- `set_state()` is thread-safe (emits `_sig` pyqtSignal).
- Positions: `bottom-right`, `bottom-left`, `top-right`, `top-left`.
- **Animated gradient border**: When the overlay is visible (any non-IDLE state), `_border_timer` fires at ~60fps and advances `_border_angle` by `_BORDER_SPEED` degrees. `paintEvent` draws layered `QPen` strokes using `QConicalGradient` centered on the pill to produce a rotating rainbow glow. Four `_GLOW_LAYERS` are drawn back-to-front (wide diffuse → tight bright core) at decreasing opacity. Two separate `QTimer`s: `_blink_timer` for the dot, `_border_timer` for the border — both stopped in `_apply()` before re-evaluating state.

### Tray Icon (`tray_icon.py`)
`QSystemTrayIcon` — runs on the main thread. No pystray.
- `set_state("IDLE"|"RECORDING"|"TRANSCRIBING"|"ERROR")` updates icon and tooltip.
- `update_hotkey_tooltip()` called after settings save.

## Configuration

`config.json` is auto-created with defaults on first run. Key tuning knobs:
- `transcription.vad_silence_ms` (default 600) — ms of silence before a speech segment is auto-committed mid-recording. Only affects behaviour while the hotkey is held; on release, VAD is disabled before the final commit so this doesn't add latency.
- `transcription.vad_threshold` (default 0.5) — VAD sensitivity (0.0–1.0).
- `audio.min_duration_seconds` (default 0.3) — ignores accidental short presses.

## Known Limitations
- UAC-elevated windows (Task Manager, etc.) cannot receive pasted text without running the app elevated.
- The `input_audio_buffer_commit_empty` error from the OpenAI API is silently ignored — it occurs on very short/silent presses and is harmless.
- Native title bar dark mode requires Windows 10 build 17763+ (October 2018 Update).
