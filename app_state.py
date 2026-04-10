from dataclasses import dataclass, field
from enum import Enum, auto
import threading


class RecordingState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    ERROR = auto()


@dataclass
class AppState:
    state: RecordingState = RecordingState.IDLE
    _lock: threading.Lock = field(default_factory=threading.Lock)

    start_recording_event: threading.Event = field(default_factory=threading.Event)
    stop_recording_event: threading.Event = field(default_factory=threading.Event)

    last_error: str = ""

    def set_state(self, new_state: RecordingState) -> None:
        with self._lock:
            self.state = new_state

    def get_state(self) -> RecordingState:
        with self._lock:
            return self.state
