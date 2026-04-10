import io
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, dtype: str = "float32"):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._audio_callback,
            blocksize=1024,
        )
        self._stream.start()

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        # indata is a view into sounddevice's internal buffer — must copy
        with self._lock:
            self._chunks.append(indata.copy())

    def stop(self) -> tuple[np.ndarray | None, float]:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._chunks:
                return None, 0.0
            audio = np.concatenate(self._chunks, axis=0)

        duration = len(audio) / self.sample_rate
        return audio, duration

    def encode_wav(self, audio: np.ndarray) -> io.BytesIO:
        buffer = io.BytesIO()
        sf.write(buffer, audio, self.sample_rate, format="WAV", subtype="PCM_16")
        buffer.seek(0)
        buffer.name = "audio.wav"  # OpenAI SDK inspects .name for MIME type
        return buffer

    def get_available_devices(self) -> list[dict]:
        devices = sd.query_devices()
        return [d for d in devices if d["max_input_channels"] > 0]
