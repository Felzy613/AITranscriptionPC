import threading
import time
from typing import Callable

import keyboard as _kb


# Maps our modifier names → keyboard-library names
_MOD_MAP = {
    "ctrl":  "ctrl",
    "shift": "shift",
    "alt":   "alt",
    "win":   "windows",
}

# Keys whose keyboard-library name differs from what we store in config
_KEY_MAP = {
    "space": "space",
    "enter": "enter",
    "tab":   "tab",
    "esc":   "esc",
    **{f"f{i}": f"f{i}" for i in range(1, 13)},
}



class HotkeyListener:
    POLL_MS = 20   # how often to check key state after press (ms)

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        modifiers: list[str],
        key: str,
    ):
        self._on_press_cb   = on_press
        self._on_release_cb = on_release
        self._hotkey_held   = False
        self._lock          = threading.Lock()
        self._started       = False
        self._hooks: list   = []

        self._modifiers: list[str] = []
        self._key: str             = ""
        self._combo_str: str       = ""

        self._set_combo(modifiers, key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_combo(self, modifiers: list[str], key: str) -> None:
        self._modifiers = modifiers
        self._key       = key
        mod_parts       = [_MOD_MAP.get(m.lower(), m.lower()) for m in modifiers]
        key_part        = _KEY_MAP.get(key.lower(), key.lower())
        self._combo_str = "+".join(mod_parts + [key_part])

    def _combo_physically_held(self) -> bool:
        """True only when every key in the combo is still held.
        Uses keyboard library's internal state, which is updated before
        suppression, so it works correctly even with suppress=True."""
        try:
            return _kb.is_pressed(self._combo_str)
        except Exception:
            return False

    def _on_hotkey_down(self) -> None:
        with self._lock:
            if self._hotkey_held:
                return
            self._hotkey_held = True
        threading.Thread(target=self._on_press_cb,   daemon=True).start()
        threading.Thread(target=self._poll_for_release, daemon=True).start()

    def _poll_for_release(self) -> None:
        """Poll physical key state; fire release callback the moment combo breaks."""
        while True:
            time.sleep(self.POLL_MS / 1000)
            with self._lock:
                if not self._hotkey_held:
                    return   # already released via another path
            if not self._combo_physically_held():
                with self._lock:
                    if not self._hotkey_held:
                        return
                    self._hotkey_held = False
                threading.Thread(target=self._on_release_cb, daemon=True).start()
                return

    # ------------------------------------------------------------------
    # Hook management
    # ------------------------------------------------------------------

    def _install_hooks(self) -> None:
        # Press hook: suppress the combo so it doesn't reach other apps
        h = _kb.add_hotkey(self._combo_str, self._on_hotkey_down, suppress=True)
        self._hooks.append(h)

    def _remove_hooks(self) -> None:
        for h in self._hooks:
            try:
                _kb.remove_hotkey(h)
            except Exception:
                pass
        self._hooks.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_hotkey(self, modifiers: list[str], key: str) -> None:
        with self._lock:
            self._hotkey_held = False
        if self._started:
            self._remove_hooks()
        self._set_combo(modifiers, key)
        if self._started:
            self._install_hooks()

    def start(self) -> None:
        self._started = True
        self._install_hooks()

    def stop(self) -> None:
        self._started = False
        self._remove_hooks()
        with self._lock:
            self._hotkey_held = False
