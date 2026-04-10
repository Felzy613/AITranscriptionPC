"""System tray icon — QSystemTrayIcon (Qt-native, runs on main thread)."""

from typing import Callable

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui     import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore    import Qt, QRectF


def _make_icon(circle_color: str, size: int = 64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    m = 6
    # Outer circle
    p.setBrush(QColor(circle_color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(m, m, size - 2 * m, size - 2 * m)
    # Mic body (white rounded rect)
    cx, cy = size // 2, size // 2
    bw, bh = size // 7, size // 4
    p.setBrush(QColor(255, 255, 255, 210))
    p.drawRoundedRect(QRectF(cx - bw, cy - bh, bw * 2, bh * 1.8), bw, bw)
    # Stand
    p.setPen(p.pen())
    sw = 2
    from PyQt6.QtGui import QPen
    p.setPen(QPen(QColor(255, 255, 255, 180), sw))
    p.drawLine(cx, cy + int(bh * 0.9), cx, cy + int(bh * 0.9) + 6)
    p.drawLine(cx - bw, cy + int(bh * 0.9) + 6, cx + bw, cy + int(bh * 0.9) + 6)
    p.end()
    return QIcon(pix)


class TrayIcon:
    def __init__(
        self,
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
        hotkey_modifiers: list[str] | None = None,
        hotkey_key: str = "space",
    ) -> None:
        self._on_settings = on_settings
        self._on_quit     = on_quit

        parts = [m.capitalize() for m in (hotkey_modifiers or ["ctrl"])] + [hotkey_key.upper()]
        self._idle_tooltip = f"AI Transcription — Ready (Hold {'+'.join(parts)})"

        self._icons = {
            "idle":       _make_icon("#646464"),
            "recording":  _make_icon("#c82828"),
            "processing": _make_icon("#28a028"),
        }

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._icons["idle"])
        self._tray.setToolTip(self._idle_tooltip)

        menu = QMenu()
        menu.addAction("AI Transcription").setEnabled(False)
        menu.addSeparator()
        act_settings = menu.addAction("Settings")
        act_settings.triggered.connect(on_settings)
        act_quit = menu.addAction("Quit")
        act_quit.triggered.connect(on_quit)
        self._tray.setContextMenu(menu)

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._tray.show()

    def stop(self) -> None:
        self._tray.hide()

    def set_state(self, state: str) -> None:
        _map = {
            "IDLE":         ("idle",       self._idle_tooltip),
            "RECORDING":    ("recording",  "AI Transcription — Recording…"),
            "TRANSCRIBING": ("processing", "AI Transcription — Transcribing…"),
            "ERROR":        ("idle",       "AI Transcription — Error"),
        }
        icon_key, tip = _map.get(state, ("idle", "AI Transcription"))
        self._tray.setIcon(self._icons[icon_key])
        self._tray.setToolTip(tip)

    def update_hotkey_tooltip(self, modifiers: list[str], key: str) -> None:
        parts = [m.capitalize() for m in modifiers] + [key.upper()]
        self._idle_tooltip = f"AI Transcription — Ready (Hold {'+'.join(parts)})"
        self._tray.setToolTip(self._idle_tooltip)
