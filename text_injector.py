import time
import threading

import pyautogui
import pyperclip


class TextInjector:
    PASTE_DELAY = 0.04       # seconds before Ctrl+V
    RESTORE_DELAY = 0.12     # seconds before restoring clipboard (batch mode only)
    STREAM_PASTE_DELAY = 0.03  # tighter delay for streaming deltas

    _paste_lock = threading.Lock()
    _saved_clipboard: str = ""

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
        """Save the user's clipboard once before streaming begins."""
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

    def inject_delta(self, delta: str) -> None:
        """Paste one delta fragment. Fast — no save/restore per call."""
        if not delta:
            return

        with self._paste_lock:
            try:
                pyperclip.copy(delta)
                time.sleep(self.STREAM_PASTE_DELAY)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pass

    def end_stream(self) -> None:
        """Restore the user's clipboard after streaming is fully done."""
        try:
            pyperclip.copy(self._saved_clipboard)
        except Exception:
            pass
