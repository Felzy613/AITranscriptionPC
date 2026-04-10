"""Recording overlay — PyQt6 frameless translucent pill window."""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QApplication
from PyQt6.QtCore    import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui     import QPainter, QColor, QPainterPath, QBrush, QFont
import ctypes

# ── State config ───────────────────────────────────────────────────────────────
_STATES = {
    "IDLE":         (None,                   "",           "#888888"),
    "RECORDING":    (["#ff4444", "#ff8888"], "Listening",  "#ff6666"),
    "TRANSCRIBING": (["#44cc88", "#88eecc"], "Finalizing", "#55dd99"),
    "ERROR":        (["#ff8844", "#ffcc88"], "Error",      "#ffaa55"),
}

_POSITIONS = {
    "bottom-right": lambda r, w, h: QPoint(r.right()  - w - 24, r.bottom() - h - 64),
    "bottom-left":  lambda r, w, h: QPoint(r.left()   + 24,     r.bottom() - h - 64),
    "top-right":    lambda r, w, h: QPoint(r.right()  - w - 24, r.top() + 24),
    "top-left":     lambda r, w, h: QPoint(r.left()   + 24,     r.top() + 24),
}

_BG     = "#1a1a1a"
_RADIUS = 10


class OverlayWindow(QWidget):
    _sig = pyqtSignal(str, str)   # (state, error_msg) — emitted from any thread

    def __init__(self, position: str = "bottom-right",
                 opacity: float = 0.85, enabled: bool = True) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,           # no taskbar entry
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)

        self._position  = position
        self._opacity   = opacity
        self._enabled   = enabled
        self._state     = "IDLE"
        self._dot_clrs: list[str] = []
        self._phase     = 0

        # Layout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(8)
        self._dot  = _Dot(self)
        self._text = QLabel("", self)
        self._text.setFont(QFont("Segoe UI Semibold", 11))
        self._text.setStyleSheet("background: transparent;")
        lay.addWidget(self._dot)
        lay.addWidget(self._text)

        # Blink timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink)

        # Thread-safe state changes
        self._sig.connect(self._apply)
        self.hide()

    # ── Public API (thread-safe) ───────────────────────────────────────────────

    def set_state(self, state: str, error_msg: str = "") -> None:
        self._sig.emit(state, error_msg)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._sig.emit("IDLE", "")

    def update_position(self, position: str) -> None:
        self._position = position
        if self._state != "IDLE":
            self._reposition()

    def update_opacity(self, opacity: float) -> None:
        self._opacity = opacity
        self.setWindowOpacity(opacity)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _apply(self, state: str, error_msg: str) -> None:
        self._state = state
        self._timer.stop()

        if state == "IDLE" or not self._enabled:
            self.hide()
            return

        dot_clrs, text, text_color = _STATES.get(state, _STATES["ERROR"])
        self._dot_clrs = dot_clrs or []
        self._phase    = 0

        if state == "ERROR" and error_msg:
            text = (error_msg[:55] + "…") if len(error_msg) > 55 else error_msg

        self._text.setText(text)
        self._text.setStyleSheet(f"color: {text_color}; background: transparent;")

        if self._dot_clrs:
            self._blink()
            self._timer.start(600)
        else:
            self._dot.set_color(QColor("transparent"))

        self._reposition()
        self.show()
        self._make_click_through()   # re-apply after show (Windows resets styles)

    def _blink(self) -> None:
        if self._dot_clrs:
            self._dot.set_color(QColor(self._dot_clrs[self._phase % len(self._dot_clrs)]))
            self._phase += 1

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        sz    = self.sizeHint()
        fn    = _POSITIONS.get(self._position, _POSITIONS["bottom-right"])
        pt    = fn(avail, sz.width(), sz.height())
        self.move(avail.x() + pt.x(), avail.y() + pt.y())

    def _make_click_through(self) -> None:
        """Apply WS_EX_TRANSPARENT so mouse clicks pass through to underlying windows."""
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception:
            pass

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r    = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), _RADIUS, _RADIUS)
        p.fillPath(path, QColor(_BG))


class _Dot(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor("#ff4444")

    def set_color(self, c: QColor) -> None:
        self._color = c
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(1, 1, 8, 8)
