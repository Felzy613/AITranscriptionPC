import json
import os
import copy
from dotenv import load_dotenv

DEFAULT_CONFIG = {
    "hotkey": {
        "modifiers": ["ctrl"],
        "key": "space"
    },
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "float32",
        "min_duration_seconds": 0.3
    },
    "transcription": {
        "model": "gpt-4o-transcribe",
        "language": "en",
        "prompt": "",
        "vad_threshold": 0.5,
        "vad_silence_ms": 300
    },
    "ui": {
        "show_overlay": True,
        "overlay_position": "bottom-right",
        "overlay_opacity": 0.85
    },
    "startup": {
        "run_on_windows_startup": False
    }
}


class ConfigManager:
    def __init__(self, config_path: str = "config.json", env_path: str = ".env"):
        self._config_path = config_path
        self._env_path = env_path
        load_dotenv(env_path)

    def load(self) -> dict:
        config = copy.deepcopy(DEFAULT_CONFIG)
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                config = self._merge(config, saved)
            except (json.JSONDecodeError, OSError):
                pass
        return config

    def save(self, config: dict) -> None:
        tmp_path = self._config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp_path, self._config_path)

    def get_api_key(self) -> str | None:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if key and not key.startswith("sk-your-key"):
            return key
        return None

    def _merge(self, base: dict, override: dict) -> dict:
        result = copy.deepcopy(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge(result[k], v)
            else:
                result[k] = v
        return result
