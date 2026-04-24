"""
API key storage helpers.

On Windows, API keys are protected with DPAPI so only the current user account
can decrypt them. On other platforms, the data falls back to plain JSON storage
for local development compatibility.
"""

from __future__ import annotations

import ctypes
import json
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class SecureStorage:
    """Stores sensitive app data locally."""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".aitpc"
        self.config_dir.mkdir(exist_ok=True)

        windll = getattr(ctypes, "windll", None)
        if windll is not None and hasattr(windll, "crypt32"):
            self.data_file = self.config_dir / "config.dpapi"
            self._mode = "dpapi"
        else:
            self.data_file = self.config_dir / "config.json"
            self._mode = "plain"

    def save(self, data: dict) -> None:
        """Save data using the best protection available on this platform."""
        payload = json.dumps(data).encode("utf-8")
        if self._mode == "dpapi":
            self.data_file.write_bytes(self._protect(payload))
        else:
            self.data_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> dict:
        """Load saved data, returning an empty dict if none is available."""
        if not self.data_file.exists():
            return {}

        try:
            if self._mode == "dpapi":
                payload = self._unprotect(self.data_file.read_bytes())
                return json.loads(payload.decode("utf-8"))
            return json.loads(self.data_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Error loading secure config: {exc}")
            return {}

    def has_api_key(self) -> bool:
        data = self.load()
        return bool(data.get("api_key"))

    def get_api_key(self) -> str:
        data = self.load()
        return data.get("api_key", "")

    def set_api_key(self, key: str) -> None:
        data = self.load()
        data["api_key"] = key
        self.save(data)

    def clear(self) -> None:
        if self.data_file.exists():
            self.data_file.unlink()

    def storage_description(self) -> str:
        if self._mode == "dpapi":
            return "Stored securely using your Windows account."
        return "Stored locally for development use on this machine."

    def _protect(self, payload: bytes) -> bytes:
        in_buffer = ctypes.create_string_buffer(payload)
        in_blob = _DataBlob(
            len(payload),
            ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        out_blob = _DataBlob()

        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "AI Transcription PC",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            raise ctypes.WinError()

        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)

    def _unprotect(self, payload: bytes) -> bytes:
        in_buffer = ctypes.create_string_buffer(payload)
        in_blob = _DataBlob(
            len(payload),
            ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        out_blob = _DataBlob()

        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            raise ctypes.WinError()

        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
