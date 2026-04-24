import time
import threading

import pyautogui
import pyperclip


class TextInjector:
    PASTE_DELAY = 0.04          # seconds before Ctrl+V (batch mode)
    RESTORE_DELAY = 0.12        # seconds before restoring clipboard (batch mode)
    STREAM_PASTE_DELAY = 0.03   # delay before Ctrl+V inside the flusher
    FLUSH_INTERVAL = 0.08       # flush accumulated deltas every 80 ms

    def __init__(self):
        self._paste_lock = threading.Lock()
        self._saved_clipboard: str = ""

        self._delta_buffer: list[str] = []
        self._buffer_lock = threading.Lock()
        self._flush_stop = threading.Event()
        self._flush_thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    # Batch mode (original behaviour)                                      #
    # ------------------------------------------------------------------ #

    def inject(self, text: str) -> None:
        """Inject a complete text block — saves and restores clipboard."""
        if not text:
            return

        with self._paste_lock:
            try:
                original = pyperclip.paste()
            except Exception:
                original = ""

            try:
                pyperclip.copy(text)
                time.sleep(self.PASTE_DELAY)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(self.RESTORE_DELAY)
            finally:
                try:
                    pyperclip.copy(original)
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    # Streaming mode                                                       #
    # ------------------------------------------------------------------ #

    def start_stream(self) -> None:
        """Save the user's clipboard and start the background flush thread."""
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        self._flush_stop.clear()
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="DeltaFlusher"
        )
        self._flush_thread.start()

    def inject_delta(self, delta: str) -> None:
        """Buffer one delta fragment — the flusher pastes them in batches."""
        if not delta:
            return
        with self._buffer_lock:
            self._delta_buffer.append(delta)

    def end_stream(self) -> None:
        """Stop the flusher, drain any remaining buffer, restore clipboard."""
        self._flush_stop.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=1.0)
            self._flush_thread = None

        # Paste any deltas that arrived after the last flush tick
        self._flush_once()

        try:
            pyperclip.copy(self._saved_clipboard)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Internal flusher                                                     #
    # ------------------------------------------------------------------ #

    def _flush_loop(self) -> None:
        """Background thread: sleep FLUSH_INTERVAL, then paste buffered text."""
        while not self._flush_stop.is_set():
            time.sleep(self.FLUSH_INTERVAL)
            self._flush_once()

    def _flush_once(self) -> None:
        """Grab everything in the buffer and paste it as a single Ctrl+V."""
        with self._buffer_lock:
            if not self._delta_buffer:
                return
            text = "".join(self._delta_buffer)
            self._delta_buffer.clear()

        with self._paste_lock:
            try:
                pyperclip.copy(text)
                time.sleep(self.STREAM_PASTE_DELAY)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pass
