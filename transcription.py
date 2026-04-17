import io
import time

from openai import OpenAI, APIConnectionError, AuthenticationError, RateLimitError


class TranscriptionError(Exception):
    pass


class TranscriptionClient:
    MAX_RETRIES = 2
    RETRY_DELAY = 1.5

    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key)

    def transcribe(
        self,
        wav_buffer: io.BytesIO,
        model: str = "gpt-4o-transcribe",
        language: str = "en",
        temperature: float = 0.0,
        prompt: str = "",
    ) -> str:
        kwargs: dict = dict(
            model=model,
            file=wav_buffer,
            response_format="json",
            temperature=temperature,
        )
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = self._client.audio.transcriptions.create(**kwargs)
                return result.text.strip()
            except AuthenticationError:
                raise TranscriptionError("Invalid API key. Update your saved key or .env file.")
            except RateLimitError:
                raise TranscriptionError("OpenAI quota exceeded. Check your billing at platform.openai.com.")
            except APIConnectionError:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
                    wav_buffer.seek(0)
                    continue
                raise TranscriptionError("Network error connecting to OpenAI.")
            except Exception as e:
                raise TranscriptionError(f"Transcription failed: {e}")

        raise TranscriptionError("All retry attempts failed.")
