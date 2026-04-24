"""Settings window — PyQt6 + PyQt6-Frameless-Window + Fluent QSS."""

import copy
import ctypes
import os
from typing import Callable

_DIR = os.path.dirname(os.path.abspath(__file__))
_ARROW_DOWN = os.path.join(_DIR, "arrow_down.svg").replace("\\", "/")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QLabel, QPushButton, QComboBox, QSlider, QLineEdit,
    QAbstractButton, QSizePolicy, QApplication, QStyleOptionSlider, QStyle,
)
from PyQt6.QtCore    import (
    Qt, QTimer, QSize, QRectF, QByteArray, pyqtSignal, QPropertyAnimation,
    QEasingCurve, pyqtProperty, QEventLoop, QObject, QEvent,
)
from PyQt6.QtGui     import (
    QPainter, QColor, QPainterPath, QBrush, QFont, QPen, QFontMetrics,
)
from PyQt6.QtCore import QPointF
from PyQt6.QtSvg import QSvgRenderer
from pynput import keyboard as pynput_keyboard
import startup_manager


# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#202020"
CARD     = "#2a2a2a"
DIVIDER  = "#333333"
BORDER   = "#3a3a3a"
FOOTER   = "#1c1c1c"
FG       = "#ffffff"
FG_DIM   = "#a1a1a1"
ACCENT   = "#60cdff"
ACCENT_FG = "#000000"
INPUT_BG = "#2d2d2d"
KBD_BG   = "rgba(255,255,255,26)"   # ~10% white, matches HTML kbd-win
KBD_BDR  = "rgba(255,255,255,26)"

# ── Data ───────────────────────────────────────────────────────────────────────
LANGUAGES = [
    ("Auto-detect", ""), ("English", "en"), ("Spanish", "es"),
    ("French", "fr"),   ("German", "de"),   ("Italian", "it"),
    ("Portuguese", "pt"), ("Russian", "ru"), ("Japanese", "ja"),
    ("Chinese", "zh"),  ("Korean", "ko"),   ("Arabic", "ar"),
    ("Hindi", "hi"),    ("Dutch", "nl"),    ("Polish", "pl"),
    ("Swedish", "sv"),  ("Turkish", "tr"),  ("Ukrainian", "uk"),
]
MODELS = [
    ("GPT-4o Transcribe", "gpt-4o-transcribe"),
    ("GPT-4o Mini Transcribe", "gpt-4o-mini-transcribe"),
]
NOISE_REDUCTION = [
    ("Laptop / computer mic", "far_field"),
    ("Headset / close mic",   "near_field"),
    ("Off",                   ""),
]
OVERLAY_POSITIONS = [
    ("Bottom-right", "bottom-right"), ("Bottom-left", "bottom-left"),
    ("Top-right",    "top-right"),    ("Top-left",    "top-left"),
]


def _label_for(pairs, value):
    for lbl, v in pairs:
        if v == value: return lbl
    return pairs[0][0] if pairs else ""

def _value_for(pairs, label):
    for lbl, v in pairs:
        if lbl == label: return v
    return pairs[0][1] if pairs else ""


# ── Global QSS ─────────────────────────────────────────────────────────────────
_QSS = f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 13px; color: {FG}; }}
QLabel {{ border: none; background: transparent; }}

QWidget#footer {{ background: {FOOTER}; }}

QScrollArea                   {{ background: transparent; border: none; }}
QScrollArea > QWidget         {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.15); border-radius: 3px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.25); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QComboBox {{
    background: {INPUT_BG};
    border: 1px solid {BORDER};
    border-bottom: 2px solid rgba(255,255,255,0.35);
    border-radius: 4px;
    padding: 4px 10px;
    color: {FG};
    min-width: 140px;
}}
QComboBox:hover  {{ border-bottom-color: rgba(255,255,255,0.6); }}
QComboBox:focus  {{ border-bottom-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    image: url({_ARROW_DOWN});
    width: 10px; height: 6px;
}}
QComboBox QAbstractItemView {{
    background: #2c2c2c;
    border: 1px solid {BORDER};
    color: {FG};
    selection-background-color: rgba(96,205,255,0.2);
    selection-color: {FG};
    outline: none;
    padding: 4px;
}}

QLineEdit {{
    background: {INPUT_BG};
    border: 1px solid {BORDER};
    border-bottom: 2px solid rgba(255,255,255,0.35);
    border-radius: 4px;
    padding: 5px 10px;
    color: {FG};
}}
QLineEdit:hover {{ border-bottom-color: rgba(255,255,255,0.6); }}
QLineEdit:focus {{ border-bottom-color: {ACCENT}; }}

QSlider::groove:horizontal {{
    height: 4px; border-radius: 2px; background: #999999;
}}
QSlider::sub-page:horizontal {{
    height: 4px; border-radius: 2px; background: #999999;
}}
QSlider::handle:horizontal {{
    width: 0px; height: 0px; background: transparent; border: none; margin: 0;
}}

QPushButton#btn_save {{
    background: {ACCENT}; color: {ACCENT_FG};
    border: none; border-radius: 4px;
    padding: 6px 28px; font-weight: 600;
}}
QPushButton#btn_save:hover   {{ background: #50bde0; }}
QPushButton#btn_save:pressed {{ background: #40b8e0; }}

QPushButton#btn_cancel, QPushButton#btn_edit {{
    background: rgba(255,255,255,13);
    color: {FG};
    border: 1px solid rgba(255,255,255,26);
    border-radius: 4px;
    padding: 5px 20px;
}}
QPushButton#btn_cancel:hover, QPushButton#btn_edit:hover {{
    background: rgba(255,255,255,26);
}}
QPushButton#btn_cancel:pressed, QPushButton#btn_edit:pressed {{
    background: rgba(255,255,255,10);
}}
"""


# ── Toggle switch widget ────────────────────────────────────────────────────────
class _Toggle(QAbstractButton):
    """Animated Windows 11-style pill toggle switch."""

    _W, _H = 40, 20

    def __init__(self, parent: QWidget | None = None, checked: bool = False) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Animate the thumb position (0.0 = off, 1.0 = on)
        self._pos: float = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"_anim_pos", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.toggled.connect(self._start_anim)

    def _start_anim(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    @pyqtProperty(float)
    def _anim_pos(self) -> float:
        return self._pos

    @_anim_pos.setter
    def _anim_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    @staticmethod
    def _lerp_color(c1: str, c2: str, t: float) -> QColor:
        r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        return QColor(
            int(r1 + (r2-r1)*t),
            int(g1 + (g2-g1)*t),
            int(b1 + (b2-b1)*t),
        )

    def paintEvent(self, _event) -> None:
        t   = self._pos
        w,h = self._W, self._H

        track_clr = self._lerp_color("#464646", ACCENT, t)
        thumb_clr = self._lerp_color("#aaaaaa", "#000000", t)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        # Track pill
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, h/2, h/2)
        p.fillPath(path, track_clr)

        # Thumb circle
        r      = 5
        pad    = h/2
        x_off  = pad
        x_on   = w - pad
        tx     = x_off + (x_on - x_off) * t
        cy     = h / 2
        p.setBrush(QBrush(QColor(thumb_clr)))
        p.drawEllipse(QRectF(tx - r, cy - r, r*2, r*2))

    def sizeHint(self) -> QSize:
        return QSize(self._W, self._H)


# ── SVG keyboard icon (matches HTML mockup) ────────────────────────────────────
class _KeyboardIcon(QWidget):
    _SVG = QByteArray(b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
        fill="none" stroke="white" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2"/>
      <path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/>
    </svg>""")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._renderer = QSvgRenderer(self._SVG, self)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw dark badge background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 13))
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, 28, 28), 4, 4)
        p.fillPath(path, QColor(255, 255, 255, 13))
        # Render SVG icon centered (16×16 inside 28×28)
        self._renderer.render(p, QRectF(6, 6, 16, 16))


# ── Wheel-scroll guard: ignore scroll on interactive widgets unless focused ────
class _WheelGuard(QObject):
    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Wheel and not obj.hasFocus():
            event.ignore()
            return True
        return False

_wheel_guard = _WheelGuard()


# ── Custom slider with perfectly circular handle ───────────────────────────────
class _Slider(QSlider):
    """QSlider that draws its own circle handle so DPI scaling can't distort it."""

    _R = 7   # handle radius in logical px

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, e) -> None:
        if not self.hasFocus():
            e.ignore()
        else:
            super().wheelEvent(e)

    def paintEvent(self, event) -> None:
        # Let Qt draw the groove via stylesheet, then draw our own handle on top
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the groove manually
        groove_y = self.height() // 2 - 2
        groove_rect = self.rect().adjusted(self._R, groove_y, -self._R, groove_y + 4 - self.height())
        path = QPainterPath()
        path.addRoundedRect(
            float(groove_rect.x()), float(groove_rect.y()),
            float(groove_rect.width()), 4.0, 2.0, 2.0
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#999999"))
        p.drawPath(path)

        # Draw handle as a perfect circle
        style = self.style()
        handle_rect = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self
        )
        cx = handle_rect.center().x()
        cy = self.height() // 2
        r  = self._R
        p.setBrush(QColor(ACCENT))
        p.setPen(QPen(QColor("#454545"), 2.5))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


# ── Settings window ─────────────────────────────────────────────────────────────
class SettingsDialog:
    """Wraps SettingsWindow; provides the same show() interface as the old dialog."""

    def __init__(self, config: dict, on_save: Callable[[dict], None]) -> None:
        self._config  = config
        self._on_save = on_save
        self._win: SettingsWindow | None = None

    def show(self) -> None:
        if self._win and self._win.isVisible():
            self._win.raise_()
            self._win.activateWindow()
            return
        self._win = SettingsWindow(self._config, self._on_save)
        self._win.show()


class SettingsWindow(QWidget):
    def __init__(self, config: dict, on_save: Callable[[dict], None]) -> None:
        super().__init__()
        self._config  = copy.deepcopy(config)
        self._on_save = on_save

        self.setWindowTitle("AI Transcription — Settings")
        self.resize(560, 680)
        self.setStyleSheet(f"QWidget#SettingsWindow {{ background: {BG}; }}" + _QSS)
        self.setObjectName("SettingsWindow")

        self._build_ui()
        self._center()

    def _apply_dark_titlebar(self) -> None:
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_dark_titlebar)

    def _center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.center() - self.rect().center())

    # ── Build ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Scrollable content ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content.setStyleSheet(f"background: {BG};")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(0)

        # Title
        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {FG};")
        c_lay.addWidget(title_lbl)
        c_lay.addSpacing(16)

        # ── Activation ─────────────────────────────────────────────────────────
        c_lay.addWidget(self._sec("Activation"))
        grp = self._group()
        right = self._row(grp, "Keyboard shortcut", "Press this to start transcribing", icon=True)
        self._build_hotkey_controls(right)
        c_lay.addWidget(grp)
        c_lay.addSpacing(24)

        # ── Engine ─────────────────────────────────────────────────────────────
        c_lay.addWidget(self._sec("Engine"))
        grp = self._group()
        right = self._row(grp, "Model selection", "Choose performance vs. accuracy")
        self._model_cb = self._add_combo(right, MODELS,
            _label_for(MODELS, self._config["transcription"]["model"]))
        self._divider(grp)
        right = self._row(grp, "Transcription language", "Select primary language or auto-detect")
        self._lang_cb = self._add_combo(right, LANGUAGES,
            _label_for(LANGUAGES, self._config["transcription"]["language"]))
        self._divider(grp)
        right = self._row(grp, "Noise reduction", "Match to your microphone type")
        self._noise_cb = self._add_combo(right, NOISE_REDUCTION,
            _label_for(NOISE_REDUCTION, self._config["transcription"].get("noise_reduction", "far_field")))
        self._divider(grp)
        self._prompt_edit = self._add_prompt_row(
            grp,
            "Transcription hint",
            "Names, terms, or style notes to help the model (optional)",
            self._config["transcription"].get("prompt", ""),
        )
        c_lay.addWidget(grp)
        c_lay.addSpacing(24)

        # ── Voice activity ─────────────────────────────────────────────────────
        c_lay.addWidget(self._sec("Voice activity"))
        grp = self._group()
        right = self._row(grp, "Silence timeout", "Stop after 500ms of silence")
        self._vad_ms_sl, self._vad_ms_lbl = self._add_slider(
            right, 100, 1500, 50,
            self._config["transcription"].get("vad_silence_ms", 500),
            lambda v: f"{v}ms")
        self._divider(grp)
        right = self._row(grp, "Detection threshold", "Sensitivity to your voice")
        self._vad_thr_sl, self._vad_thr_lbl = self._add_slider(
            right, 10, 90, 5,
            int(self._config["transcription"].get("vad_threshold", 0.5) * 100),
            lambda v: f"{v/100:.1f}")
        c_lay.addWidget(grp)
        c_lay.addSpacing(24)

        # ── System ─────────────────────────────────────────────────────────────
        c_lay.addWidget(self._sec("System"))
        grp = self._group()
        right = self._row(grp, "Show recording overlay", "Visual feedback while speaking")
        self._overlay_tog = self._add_toggle(right, self._config["ui"]["show_overlay"])
        self._divider(grp)
        right = self._row(grp, "Launch on startup", "Start when Windows boots up")
        self._startup_tog = self._add_toggle(right, startup_manager.is_enabled())
        c_lay.addWidget(grp)
        c_lay.addSpacing(24)

        # ── Overlay ────────────────────────────────────────────────────────────
        c_lay.addWidget(self._sec("Overlay"))
        grp = self._group()
        right = self._row(grp, "Position", "Where to show the indicator")
        self._pos_cb = self._add_combo(right, OVERLAY_POSITIONS,
            _label_for(OVERLAY_POSITIONS, self._config["ui"]["overlay_position"]))
        self._divider(grp)
        right = self._row(grp, "Opacity", "Transparency level")
        self._opacity_sl, self._opacity_lbl = self._add_slider(
            right, 20, 100, 5,
            int(self._config["ui"].get("overlay_opacity", 0.85) * 100),
            lambda v: f"{v}%")
        c_lay.addWidget(grp)
        c_lay.addStretch()

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        # ── Footer ─────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,13);")
        root_lay.addWidget(sep)

        footer = QWidget()
        footer.setObjectName("footer")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer.setFixedHeight(56)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 0, 24, 0)
        f_lay.addStretch()

        btn_save = QPushButton("Save")
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._save)
        f_lay.addWidget(btn_save)
        f_lay.addSpacing(8)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.close)
        f_lay.addWidget(btn_cancel)

        root_lay.addWidget(footer)

    # ── UI helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sec(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: #e5e5e5; background: transparent; padding-left: 2px;")
        lbl.setContentsMargins(0, 0, 0, 6)
        return lbl

    @staticmethod
    def _group() -> QFrame:
        f = QFrame()
        f.setObjectName("group")
        f.setStyleSheet("""
            QFrame#group {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(255,255,255,13);
                border-radius: 4px;
            }
            QLabel { border: none; background: transparent; }
        """)
        f.setLayout(QVBoxLayout())
        f.layout().setContentsMargins(0, 0, 0, 0)
        f.layout().setSpacing(0)
        return f

    @staticmethod
    def _divider(group: QFrame) -> None:
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background: rgba(255,255,255,5); border: none; margin: 0 16px;")
        group.layout().addWidget(d)

    @staticmethod
    def _row(group: QFrame, title: str, desc: str, icon: bool = False) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        # Left: optional icon badge + title + description
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(2)

        title_row = QWidget()
        tr_lay = QHBoxLayout(title_row)
        tr_lay.setContentsMargins(0, 0, 0, 0)
        tr_lay.setSpacing(10)
        tr_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if icon:
            badge = _KeyboardIcon(title_row)
            tr_lay.addWidget(badge)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; color: {FG};")
        tr_lay.addWidget(title_lbl)
        tr_lay.addStretch()
        left_lay.addWidget(title_row)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"font-size: 12px; color: {FG_DIM};")
        left_lay.addWidget(desc_lbl)

        lay.addWidget(left, stretch=1)

        right = QWidget()
        r_lay = QHBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(8)
        r_lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(right)

        group.layout().addWidget(row)
        return right

    @staticmethod
    def _add_combo(parent: QWidget, pairs: list, current: str) -> QComboBox:
        cb = QComboBox(parent)
        cb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        cb.installEventFilter(_wheel_guard)
        for label, _ in pairs:
            cb.addItem(label)
        cb.setCurrentText(current)
        parent.layout().addWidget(cb)
        return cb

    @staticmethod
    def _add_toggle(parent: QWidget, checked: bool) -> "_Toggle":
        tog = _Toggle(parent, checked=checked)
        parent.layout().addWidget(tog)
        return tog

    @staticmethod
    def _add_prompt_row(group: QFrame, title: str, desc: str, value: str) -> QLineEdit:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; color: {FG};")
        lay.addWidget(title_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"font-size: 12px; color: {FG_DIM};")
        lay.addWidget(desc_lbl)
        edit = QLineEdit()
        edit.setPlaceholderText("e.g. Names: John, Sarah. Terms: API, VAD, gpt-4o.")
        edit.setText(value)
        lay.addWidget(edit)
        group.layout().addWidget(container)
        return edit

    @staticmethod
    def _add_slider(parent: QWidget, min_v: int, max_v: int, step: int,
                    value: int, fmt) -> tuple:
        sl = _Slider(parent)
        sl.setMinimum(min_v)
        sl.setMaximum(max_v)
        sl.setSingleStep(step)
        sl.setPageStep(step * 4)
        sl.setValue(value)
        sl.setFixedWidth(130)

        lbl = QLabel(fmt(value))
        lbl.setFixedWidth(52)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"color: {FG_DIM}; font-family: Consolas; font-size: 12px;")
        sl.valueChanged.connect(lambda v: lbl.setText(fmt(v)))

        parent.layout().addWidget(sl)
        parent.layout().addWidget(lbl)
        return sl, lbl

    # ── Hotkey controls ──────────────────────────────────────────────────────────

    def _build_hotkey_controls(self, parent: QWidget) -> None:
        self._badge_container = QWidget(parent)
        bc_lay = QHBoxLayout(self._badge_container)
        bc_lay.setContentsMargins(0, 0, 0, 0)
        bc_lay.setSpacing(4)
        self._rebuild_badges()

        btn_edit = QPushButton("Edit", parent)
        btn_edit.setObjectName("btn_edit")
        btn_edit.setFixedWidth(64)
        btn_edit.clicked.connect(self._capture_hotkey)

        parent.layout().addWidget(self._badge_container)
        parent.layout().addSpacing(4)
        parent.layout().addWidget(btn_edit)

    def _rebuild_badges(self) -> None:
        lay = self._badge_container.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mods = self._config["hotkey"]["modifiers"]
        key  = self._config["hotkey"]["key"].upper()
        parts = [m.capitalize() for m in mods] + [key]
        for i, part in enumerate(parts):
            if i:
                sep = QLabel("+")
                sep.setStyleSheet(f"color: #555555; background: transparent; font-size: 12px;")
                lay.addWidget(sep)
            kbd = QLabel(f" {part} ")
            kbd.setStyleSheet(
                f"background: {KBD_BG}; color: #cccccc; border: 1px solid {KBD_BDR};"
                f"border-radius: 4px; font-family: Consolas; font-size: 12px; padding: 2px 4px;"
            )
            lay.addWidget(kbd)

    def _capture_hotkey(self) -> None:
        dlg = _HotkeyCapture(self)
        dlg.exec()
        if dlg.result_mods is not None and dlg.result_key:
            self._config["hotkey"]["modifiers"] = dlg.result_mods
            self._config["hotkey"]["key"]       = dlg.result_key
            self._rebuild_badges()

    # ── Save ────────────────────────────────────────────────────────────────────

    def _save(self) -> None:
        cfg = self._config
        cfg["transcription"]["model"]           = _value_for(MODELS, self._model_cb.currentText())
        cfg["transcription"]["language"]        = _value_for(LANGUAGES, self._lang_cb.currentText())
        cfg["transcription"]["noise_reduction"] = _value_for(NOISE_REDUCTION, self._noise_cb.currentText()) or None
        cfg["transcription"]["prompt"]          = self._prompt_edit.text().strip()
        cfg["transcription"]["vad_silence_ms"]  = self._vad_ms_sl.value()
        cfg["transcription"]["vad_threshold"]  = round(self._vad_thr_sl.value() / 100, 2)
        cfg["ui"]["show_overlay"]              = self._overlay_tog.isChecked()
        cfg["ui"]["overlay_position"]          = _value_for(OVERLAY_POSITIONS, self._pos_cb.currentText())
        cfg["ui"]["overlay_opacity"]           = round(self._opacity_sl.value() / 100, 2)
        startup = self._startup_tog.isChecked()
        if startup:
            startup_manager.enable()
        else:
            startup_manager.disable()
        cfg["startup"]["run_on_windows_startup"] = startup
        self._on_save(cfg)
        self.close()


# ── Hotkey capture dialog ────────────────────────────────────────────────────────
class _HotkeyCapture(QWidget):
    """Plain QWidget so closeEvent is never intercepted by FramelessWindow."""

    _update_sig = pyqtSignal(str)
    _close_sig  = pyqtSignal()   # emitted from pynput thread → closes on Qt thread

    def __init__(self, parent: QWidget) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.result_mods: list[str] | None = None
        self.result_key:  str | None       = None
        self._loop: QEventLoop | None      = None

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFixedSize(360, 200)
        self.setStyleSheet(f"background: {BG};" + _QSS)

        # Center on parent
        pr = parent.geometry()
        self.move(
            pr.x() + (pr.width()  - self.width())  // 2,
            pr.y() + (pr.height() - self.height()) // 2,
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(12)

        lbl_title = QLabel("Hold your shortcut, then release")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {FG};")
        lay.addWidget(lbl_title)

        lbl_hint = QLabel("Press Esc to cancel")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setStyleSheet(f"font-size: 12px; color: {FG_DIM};")
        lay.addWidget(lbl_hint)

        lay.addSpacing(8)

        # Combo display box
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background: {CARD};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(16, 14, 16, 14)
        self._cap_lbl = QLabel("Waiting for input…")
        self._cap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cap_lbl.setStyleSheet(f"font-family: Consolas; font-size: 16px; color: {FG_DIM};")
        box_lay.addWidget(self._cap_lbl)
        lay.addWidget(box)

        self._update_sig.connect(self._update_display)
        self._close_sig.connect(self.close)
        self._start_listener()

    def _update_display(self, text: str) -> None:
        self._cap_lbl.setText(text)
        self._cap_lbl.setStyleSheet(
            f"font-family: Consolas; font-size: 16px; color: {ACCENT};")

    def _start_listener(self) -> None:
        pressed_mods: set[str] = set()
        pressed_key:  list     = [None]
        _result:      dict     = {}
        _done         = [False]

        MODIFIER_KEYS = {
            pynput_keyboard.Key.ctrl,    pynput_keyboard.Key.ctrl_l,  pynput_keyboard.Key.ctrl_r,
            pynput_keyboard.Key.shift,   pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r,
            pynput_keyboard.Key.alt,     pynput_keyboard.Key.alt_l,   pynput_keyboard.Key.alt_r,
            pynput_keyboard.Key.alt_gr,
            pynput_keyboard.Key.cmd,     pynput_keyboard.Key.cmd_l,   pynput_keyboard.Key.cmd_r,
        }
        MOD_NAMES = {
            pynput_keyboard.Key.ctrl:    "ctrl",  pynput_keyboard.Key.ctrl_l:  "ctrl",
            pynput_keyboard.Key.ctrl_r:  "ctrl",
            pynput_keyboard.Key.shift:   "shift", pynput_keyboard.Key.shift_l: "shift",
            pynput_keyboard.Key.shift_r: "shift",
            pynput_keyboard.Key.alt:     "alt",   pynput_keyboard.Key.alt_l:   "alt",
            pynput_keyboard.Key.alt_r:   "alt",   pynput_keyboard.Key.alt_gr:  "alt",
            pynput_keyboard.Key.cmd:     "win",   pynput_keyboard.Key.cmd_l:   "win",
            pynput_keyboard.Key.cmd_r:   "win",
        }
        SPECIAL = {
            pynput_keyboard.Key.space: "space", pynput_keyboard.Key.enter: "enter",
            pynput_keyboard.Key.tab:   "tab",
            **{getattr(pynput_keyboard.Key, f"f{i}"): f"f{i}" for i in range(1, 13)},
        }
        VK_PUNCT = {186:";",187:"=",188:",",189:"-",190:".",191:"/",
                    192:"`",219:"[",220:"\\",221:"]",222:"'"}

        def resolve(key) -> str | None:
            n = SPECIAL.get(key)
            if n: return n
            vk = getattr(key, "vk", None)
            if vk:
                if 65 <= vk <= 90:   return chr(vk).lower()
                if 48 <= vk <= 57:   return chr(vk)
                if 112 <= vk <= 123: return f"f{vk-111}"
                if vk in VK_PUNCT:   return VK_PUNCT[vk]
            ch = getattr(key, "char", None)
            if ch and ord(ch) >= 32: return ch.lower()
            return None

        def close(save: bool) -> None:
            if _done[0]: return
            _done[0] = True
            if save and _result.get("key"):
                self.result_mods = _result["modifiers"]
                self.result_key  = _result["key"]
            self._close_sig.emit()  # marshalled to Qt thread via pyqtSignal

        def on_press(key) -> None:
            if _done[0]: return
            if key == pynput_keyboard.Key.esc:
                close(False)
                return
            if key in MODIFIER_KEYS:
                pressed_mods.add(MOD_NAMES[key])
            else:
                name = resolve(key)
                if name:
                    pressed_key[0] = name
                    mods_str = " + ".join(m.capitalize() for m in sorted(pressed_mods))
                    combo = f"{mods_str} + {name.upper()}" if mods_str else name.upper()
                    self._update_sig.emit(combo)

        def on_release(key) -> None:
            if _done[0]: return
            if key == pynput_keyboard.Key.esc: return
            if key not in MODIFIER_KEYS and pressed_key[0]:
                _result["modifiers"] = sorted(pressed_mods)
                _result["key"]       = pressed_key[0]
                close(True)
            elif key in MODIFIER_KEYS:
                pressed_mods.discard(MOD_NAMES.get(key, ""))

        self._listener = listener = pynput_keyboard.Listener(
            on_press=on_press, on_release=on_release, suppress=False)
        listener.start()

    def closeEvent(self, event) -> None:
        try:
            self._listener.stop()
        except Exception:
            pass
        if hasattr(self, "_loop") and self._loop is not None:
            self._loop.quit()
            self._loop = None
        super().closeEvent(event)

    def exec(self) -> None:
        """Show modal and block via a local event loop; quits when window closes."""
        self._loop = QEventLoop()
        self.show()
        self._loop.exec()
