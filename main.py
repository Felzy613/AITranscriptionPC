import sys
import threading
import os

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore    import QObject, pyqtSignal

from config_manager import ConfigManager
from app_state import AppState, RecordingState
from realtime_transcriber import RealtimeTranscriber
from text_injector import TextInjector
from hotkey_listener import HotkeyListener
from overlay import OverlayWindow
from tray_icon import TrayIcon
from settings_dialog import SettingsDialog
from secure_storage import SecureStorage
from api_key_setup import APIKeySetupDialog


# ---------------------------------------------------------------------------
# Thread-safe bridge: lets worker threads send signals to the main thread.
# ---------------------------------------------------------------------------

class _Bridge(QObject):
    set_ui_sig        = pyqtSignal(str, str)   # (state, error_msg)
    open_settings_sig = pyqtSignal()
    quit_sig          = pyqtSignal()


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # --- Load config ---
    config_mgr = ConfigManager()
    config = config_mgr.load()

    # --- Secure API Key Management ---
    secure_storage = SecureStorage()
    api_key = secure_storage.get_api_key() or config_mgr.get_api_key()

    # If no stored API key exists, show setup dialog.
    if not api_key:
        setup_dialog = APIKeySetupDialog(storage_description=secure_storage.storage_description())
        setup_dialog.api_key_set.connect(secure_storage.set_api_key)

        if setup_dialog.exec() != APIKeySetupDialog.DialogCode.Accepted:
            sys.exit(0)

        api_key = secure_storage.get_api_key()
        if not api_key:
            QMessageBox.critical(
                None,
                "Setup Required",
                "You must enter a valid OpenAI API key to use this application."
            )
            sys.exit(1)
    
    # Set API key as environment variable for the OpenAI client.
    os.environ["OPENAI_API_KEY"] = api_key

    # --- Shared state ---
    state = AppState()
    injector = TextInjector()

    active_transcriber: RealtimeTranscriber | None = None
    _transcriber_lock = threading.Lock()

    # --- UI objects ---
    overlay = OverlayWindow(
        position=config["ui"]["overlay_position"],
        opacity=config["ui"]["overlay_opacity"],
        enabled=config["ui"]["show_overlay"],
    )

    tray = TrayIcon(
        on_settings=lambda: bridge.open_settings_sig.emit(),
        on_quit=lambda: bridge.quit_sig.emit(),
        hotkey_modifiers=config["hotkey"]["modifiers"],
        hotkey_key=config["hotkey"]["key"],
    )

    # --- Bridge ---
    bridge = _Bridge()

    def _set_ui(ui_state: str, error_msg: str = "") -> None:
        """Thread-safe: can be called from any thread."""
        overlay.set_state(ui_state, error_msg)   # already uses pyqtSignal internally
        bridge.set_ui_sig.emit(ui_state, error_msg)

    bridge.set_ui_sig.connect(lambda s, _e: tray.set_state(s))

    # ------------------------------------------------------------------ #
    # Settings                                                             #
    # ------------------------------------------------------------------ #

    def _apply_config(new_config: dict) -> None:
        nonlocal config
        config = new_config
        config_mgr.save(config)
        listener.update_hotkey(
            config["hotkey"]["modifiers"],
            config["hotkey"]["key"],
        )
        overlay.set_enabled(config["ui"]["show_overlay"])
        overlay.update_position(config["ui"]["overlay_position"])
        overlay.update_opacity(config["ui"]["overlay_opacity"])
        tray.update_hotkey_tooltip(
            config["hotkey"]["modifiers"],
            config["hotkey"]["key"],
        )

    _settings_dialog = SettingsDialog(config, on_save=_apply_config)

    def _open_settings() -> None:
        _settings_dialog.show()

    bridge.open_settings_sig.connect(_open_settings)

    # ------------------------------------------------------------------ #
    # Quit                                                                 #
    # ------------------------------------------------------------------ #

    def _do_quit() -> None:
        listener.stop()
        tray.stop()
        app.quit()

    bridge.quit_sig.connect(_do_quit)

    # ------------------------------------------------------------------ #
    # Transcription callbacks (called from RealtimeTranscriber's thread)  #
    # ------------------------------------------------------------------ #

    def on_delta(delta: str) -> None:
        injector.inject_delta(delta)

    def on_complete(transcript: str) -> None:
        pass  # Deltas already injected; cleanup handled in on_session_done

    def on_error(msg: str) -> None:
        state.set_state(RecordingState.ERROR)
        state.last_error = msg
        _set_ui("ERROR", msg)
        injector.end_stream()

        import time
        time.sleep(3)
        state.set_state(RecordingState.IDLE)
        _set_ui("IDLE")

    def on_session_done() -> None:
        injector.end_stream()
        if state.get_state() != RecordingState.ERROR:
            state.set_state(RecordingState.IDLE)
            _set_ui("IDLE")

    # ------------------------------------------------------------------ #
    # Hotkey callbacks                                                     #
    # ------------------------------------------------------------------ #

    def on_hotkey_press() -> None:
        nonlocal active_transcriber

        if state.get_state() != RecordingState.IDLE:
            return

        t = RealtimeTranscriber(
            api_key=api_key,
            model=config["transcription"]["model"],
            language=config["transcription"]["language"],
            vad_threshold=config["transcription"].get("vad_threshold", 0.5),
            vad_silence_ms=config["transcription"].get("vad_silence_ms", 600),
            prompt=config["transcription"].get("prompt", ""),
        )

        with _transcriber_lock:
            active_transcriber = t

        state.set_state(RecordingState.RECORDING)
        _set_ui("RECORDING")
        injector.start_stream()

        def _start() -> None:
            t.start(
                on_delta=on_delta,
                on_complete=on_complete,
                on_error=on_error,
            )
            if t._thread:
                t._thread.join()
            on_session_done()

        threading.Thread(target=_start, daemon=True, name="TranscriberSession").start()

    def on_hotkey_release() -> None:
        nonlocal active_transcriber

        current_state = state.get_state()
        if current_state not in (RecordingState.RECORDING, RecordingState.TRANSCRIBING):
            return

        state.set_state(RecordingState.TRANSCRIBING)
        _set_ui("TRANSCRIBING")

        with _transcriber_lock:
            t = active_transcriber

        if t:
            t.stop()

    # ------------------------------------------------------------------ #
    # Start                                                                #
    # ------------------------------------------------------------------ #

    listener = HotkeyListener(
        on_press=on_hotkey_press,
        on_release=on_hotkey_release,
        modifiers=config["hotkey"]["modifiers"],
        key=config["hotkey"]["key"],
    )
    listener.start()
    tray.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
