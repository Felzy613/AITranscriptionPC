# AI Transcription PC

A Windows push-to-talk transcription app that listens to your microphone and types what you say into any focused window — in real time, as you speak.

Built with OpenAI's Realtime API (`gpt-4o-transcribe`) and PyQt6.

![Recording state](assets/icon_recording.png)

---

## How it works

1. Hold your hotkey (default: configurable) → recording starts instantly
2. Speak — transcribed text appears in whatever window you're typing in, word by word
3. Release the hotkey → finishes and stops

Works in any app: browsers, editors, chat clients, terminals, Office, etc.

---

## Features

- **Real-time streaming** — text appears as you speak, not after
- **Zero-latency mic start** — audio buffered before WebSocket connects so no words are lost at the start
- **Configurable hotkey** — set any modifier + key combination from Settings
- **Model selection** — `gpt-4o-transcribe` (best quality) or `gpt-4o-mini-transcribe` (faster/cheaper)
- **Language selection** — 18 languages or auto-detect
- **VAD tuning** — adjust silence timeout and detection threshold
- **Recording overlay** — subtle floating pill indicator showing recording/finalizing state
- **System tray** — runs in the background, right-click to open Settings or quit
- **Launch on startup** — optional Windows startup entry
- **Dark UI** — native Windows dark title bar + custom dark settings panel

---

## Requirements

- Windows 10 (build 17763+) or Windows 11
- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys) with Realtime API access

---

## Setup

**1. Clone the repo**
```cmd
git clone https://github.com/YosefDM/AITranscriptionPC.git
cd AITranscriptionPC
```

**2. Add your API key**

Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-proj-your-key-here
```

**3. Install dependencies**
```cmd
install.bat
```
This creates a `venv` and installs everything from `requirements.txt`.

**4. Run**
```cmd
venv\Scripts\python.exe main.py
```

The app starts in the system tray. Right-click the tray icon to open Settings.

---

## Settings

Open via the system tray icon → **Settings**.

| Setting | Description |
|---|---|
| Keyboard shortcut | The hotkey combo to hold while speaking |
| Model | `gpt-4o-transcribe` (quality) or `gpt-4o-mini-transcribe` (speed) |
| Language | Transcription language, or auto-detect |
| Silence timeout | How long a pause triggers a mid-speech commit (ms) |
| Detection threshold | VAD sensitivity — lower catches quieter voices |
| Show overlay | Toggle the floating recording indicator |
| Overlay position | Corner of screen for the indicator |
| Overlay opacity | Transparency of the indicator |
| Launch on startup | Start with Windows |

---

## Architecture notes

See [CLAUDE.md](CLAUDE.md) for a detailed breakdown of the threading model, state machine, transcription flow, and all the non-obvious design decisions.

---

## Cost

Uses the OpenAI Realtime API, billed per audio second. As of writing, `gpt-4o-transcribe` via the Realtime API costs ~$0.006/min. A typical short dictation (10–30 seconds) costs a fraction of a cent.

---

## Known limitations

- Paste injection won't work in UAC-elevated windows (Task Manager, etc.) unless the app is also run as administrator
- Requires an active internet connection (cloud transcription)
