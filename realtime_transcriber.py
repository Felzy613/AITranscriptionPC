"""
Real-time transcription using OpenAI Realtime WebSocket API.

Key design decisions:
- Audio capture starts IMMEDIATELY on hotkey press, before WebSocket connects.
  Chunks are buffered locally and flushed once the session is ready, so the
  first words are never lost to connection setup time (~1-2 seconds).
- Server VAD with short silence_duration (300ms) commits segments frequently
  so text appears in near-real-time bursts rather than one big block at the end.
- Transcription deltas from each VAD segment are injected as they stream in.

Audio format required by OpenAI Realtime API: PCM16, 24 kHz, mono.
"""

import asyncio
import base64
import json
import threading
import time
from collections import deque
from typing import Callable

import numpy as np
import sounddevice as sd
import websockets


class RealtimeTranscriber:
    WS_URL = "wss://api.openai.com/v1/realtime"
    # Connection model — must be a realtime-capable model
    REALTIME_MODEL = "gpt-4o-realtime-preview"
    SAMPLE_RATE = 24_000   # Required by OpenAI Realtime API
    CHANNELS = 1
    CHUNK_MS = 20          # 20 ms per audio callback → 480 samples
    CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-transcribe",  # transcription model inside session
        language: str = "en",
        vad_threshold: float = 0.5,
        vad_silence_ms: int = 300,          # short silence → more frequent commits
        prompt: str = "",
    ):
        self._api_key = api_key
        self._model = model
        self._language = language
        self._vad_threshold = vad_threshold
        self._vad_silence_ms = vad_silence_ms
        self._prompt = prompt

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self._session_ready: asyncio.Event | None = None
        self._stop_requested = False  # True if stop() called before _session() created _stop_event

        # Audio captured before WebSocket is ready is stored here
        self._pre_buffer: deque[bytes] = deque()
        self._pre_buffer_lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._audio_queue: asyncio.Queue | None = None

        self._on_delta: Callable[[str], None] | None = None
        self._on_complete: Callable[[str], None] | None = None
        self._on_error: Callable[[str], None] | None = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start(
        self,
        on_delta: Callable[[str], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Start transcription session.
        Audio capture begins immediately; WebSocket connects concurrently.
        """
        self._on_delta = on_delta
        self._on_complete = on_complete
        self._on_error = on_error

        # Start mic BEFORE the event loop so no audio is lost to setup time
        self._start_mic_prebuffer()

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="RealtimeTranscriber"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop mic and signal to commit remaining audio (hotkey released)."""
        self._stop_requested = True

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._loop and self._stop_event and not self._stop_event.is_set():
            self._loop.call_soon_threadsafe(self._stop_event.set)

    # ------------------------------------------------------------------ #
    # Pre-buffer mic (before WebSocket is ready)                          #
    # ------------------------------------------------------------------ #

    def _start_mic_prebuffer(self) -> None:
        """Capture audio into pre_buffer until the session is ready."""
        def callback(indata: np.ndarray, frames: int, t, status) -> None:
            pcm16 = (indata[:, 0] * 32_767).astype(np.int16)
            chunk = pcm16.tobytes()

            if self._audio_queue is not None and self._loop is not None:
                # Session is ready — send directly to async queue
                asyncio.run_coroutine_threadsafe(
                    self._audio_queue.put(chunk), self._loop
                )
            else:
                # Still connecting — buffer locally
                with self._pre_buffer_lock:
                    self._pre_buffer.append(chunk)

        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=self.CHUNK_SAMPLES,
            callback=callback,
        )
        self._stream.start()

    # ------------------------------------------------------------------ #
    # Event loop thread                                                    #
    # ------------------------------------------------------------------ #

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session())
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))

    async def _session(self) -> None:
        self._stop_event = asyncio.Event()
        if self._stop_requested:
            self._stop_event.set()
        self._audio_queue = asyncio.Queue()

        url = f"{self.WS_URL}?model={self.REALTIME_MODEL}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            async with websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                max_size=None,
            ) as ws:
                await self._setup_session(ws)

                # Flush everything captured during connection setup
                await self._flush_prebuffer(ws)

                send_task = asyncio.create_task(self._send_audio(ws))
                recv_task = asyncio.create_task(self._receive_events(ws))
                await asyncio.gather(send_task, recv_task, return_exceptions=True)

        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError as e:
            if self._on_error:
                self._on_error(f"Connection closed: {e}")
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))

    async def _setup_session(self, ws) -> None:
        """Wait for session.created, then configure transcription session."""
        async for raw in ws:
            event = json.loads(raw)
            if event.get("type") == "session.created":
                break
            if event.get("type") == "error":
                raise RuntimeError(str(event.get("error", "Session creation failed")))

        session_cfg: dict = {
            "modalities": ["text"],
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": self._model,
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": self._vad_threshold,
                "prefix_padding_ms": 500,   # generous prefix so speech onset is captured
                "silence_duration_ms": self._vad_silence_ms,
            },
        }
        if self._language:
            session_cfg["input_audio_transcription"]["language"] = self._language
        if self._prompt:
            session_cfg["input_audio_transcription"]["prompt"] = self._prompt

        await ws.send(json.dumps({"type": "session.update", "session": session_cfg}))

        async for raw in ws:
            event = json.loads(raw)
            if event.get("type") == "session.updated":
                break
            if event.get("type") == "error":
                raise RuntimeError(str(event.get("error", "Session update failed")))

    async def _flush_prebuffer(self, ws) -> None:
        """Send all audio buffered during connection setup, then switch to queue mode."""
        with self._pre_buffer_lock:
            buffered = list(self._pre_buffer)
            self._pre_buffer.clear()

        for chunk in buffered:
            b64 = base64.b64encode(chunk).decode()
            await ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": b64}))

    # ------------------------------------------------------------------ #
    # Audio sender                                                         #
    # ------------------------------------------------------------------ #

    async def _send_audio(self, ws) -> None:
        """Forward audio from queue to WebSocket until stop_event, then commit."""
        while not self._stop_event.is_set():
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=0.05)
                b64 = base64.b64encode(chunk).decode()
                await ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": b64}))
            except asyncio.TimeoutError:
                continue
            except Exception:
                return

        # Small delay to catch last frames from sounddevice callback
        await asyncio.sleep(0.08)
        while not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get_nowait()
                b64 = base64.b64encode(chunk).decode()
                await ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": b64}))
            except Exception:
                break

        # Disable server VAD so the explicit commit is processed immediately
        # (without VAD, the server no longer waits for its silence window)
        try:
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {"turn_detection": None},
            }))
        except Exception:
            pass

        # Commit remaining buffered audio on the server side
        try:
            await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Event receiver                                                       #
    # ------------------------------------------------------------------ #

    async def _receive_events(self, ws) -> None:
        try:
            async for raw in ws:
                event = json.loads(raw)
                t = event.get("type", "")

                if t == "conversation.item.input_audio_transcription.delta":
                    delta = event.get("delta", "")
                    if delta and self._on_delta:
                        # Run in executor so time.sleep inside inject_delta doesn't
                        # block the event loop and starve _send_audio of cycles
                        await asyncio.get_event_loop().run_in_executor(
                            None, self._on_delta, delta
                        )

                elif t == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if self._on_complete:
                        self._on_complete(transcript)
                    # If hotkey already released, this was the final segment
                    if self._stop_event.is_set():
                        return

                elif t == "error":
                    err = event.get("error", {})
                    code = err.get("code", "")
                    # Ignore empty-buffer commits (very short/silent presses)
                    if code == "input_audio_buffer_commit_empty":
                        return
                    msg = err.get("message", str(err))
                    if self._on_error:
                        self._on_error(f"{code}: {msg}" if code else msg)
                    return

        except (websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError):
            pass
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
