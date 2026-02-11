# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## HQ Access Level: PUBLIC

This is a **PUBLIC repository**. Content restrictions apply.

**Allowed HQ reads:**
- `~/Tech_Projects/_HQ/me/persona_public.md`
- `~/Tech_Projects/_HQ/standards/*`
- `~/Tech_Projects/_HQ/guides/*`
- `~/Tech_Projects/_HQ/templates/*`

**Blocked:**
- `~/Tech_Projects/_HQ/me/persona.md` (CONTEXT-ONLY sections)
- `~/Tech_Projects/_HQ/me/_private/*`
- `~/Tech_Projects/_HQ/sessions/*`

**Rule:** Never output personal context to any file in this repo.

---

## Project Overview

TommyTalker is a privacy-first voice-to-text app for macOS. It provides push-to-talk dictation via Right Command key, with app-aware text formatting powered by 97 app profiles. Speech recognition runs locally via mlx-whisper on Apple Silicon. The engine also includes LLM rewriting (Ollama), speaker diarization (pyannote.audio), and RAG storage (ChromaDB) — these are built but hidden from the UI, reserved for future modes.

**Status:** Active — Push-to-talk operational, 76 tests passing, UI simplified to cursor mode only.

## Current Focus

- **Active:** Push-to-talk (Right Command hold-to-record), app context detection, menu bar + dashboard
- **Engine complete but UI hidden:** Editor mode (LLM rewrite), Meeting mode (diarization+RAG), HUD mode (screen-share invisible overlay)

## Development Commands

### Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

### Running
```bash
# Run from source (with PYTHONPATH)
PYTHONPATH=src python -m tommy_talker.main

# Or after pip install -e .
tommytalker
```

### Testing
```bash
pytest tests/ -v
pytest tests/ --cov=src/tommy_talker --cov-report=term-missing
mutmut run  # Mutation testing
```

### Building
```bash
./build.sh  # Creates macOS .app bundle via PyInstaller
```

## Architecture

```
TommyTalker/
├── src/tommy_talker/           # Main package
│   ├── __init__.py             # Package exports
│   ├── main.py                 # Entry point + permission gatekeeper
│   ├── app_controller.py       # Central orchestrator (hotkeys, recording, text output)
│   ├── engine/                 # Core AI processing
│   │   ├── audio_capture.py    # Dual-stream audio pipeline
│   │   ├── transcriber.py      # mlx-whisper STT
│   │   ├── llm_client.py       # Ollama/OpenAI LLM client
│   │   ├── diarizer.py         # pyannote speaker diarization
│   │   ├── rag_store.py        # ChromaDB meeting storage
│   │   ├── modes.py            # Operating mode controllers
│   │   └── session_db.py       # SQLite session metadata
│   ├── gui/                    # PyQt6 interface
│   │   ├── menu_bar.py         # System tray app (cursor mode only)
│   │   ├── dashboard.py        # Settings window (simplified)
│   │   ├── hud.py              # Screen-share invisible overlay (not wired)
│   │   ├── hotkey_selector.py  # Hotkey config widget (not wired)
│   │   ├── setup_guide.py      # Permission wizard
│   │   └── onboarding.py       # First-run wizard
│   ├── utils/                  # Infrastructure
│   │   ├── app_context.py      # App detection + text format selection (97 profiles)
│   │   ├── audio_feedback.py   # System sound playback (Blow.aiff)
│   │   ├── config.py           # Configuration management + migration
│   │   ├── hardware_detect.py  # Apple Silicon tier detection
│   │   ├── hotkeys.py          # Quartz Event Tap hotkey manager
│   │   ├── logger.py           # Structured logging
│   │   ├── permissions.py      # macOS permission checks
│   │   ├── typing.py           # Cursor text insertion (pyautogui + clipboard)
│   │   ├── secure_credentials.py # Keychain integration
│   │   └── history.py          # Transcription history (orphaned)
│   └── data/                   # Static data files
│       └── app_profiles.json   # 97 app profiles for context detection
├── tests/                      # 76 tests across 5 files
├── scripts/
│   └── security_scan.sh        # 9-phase pre-commit security scanner (v4)
├── _project/
│   └── DevPlan.md              # Development plan
├── pyproject.toml              # Package configuration
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Development dependencies
```

## Key Concepts

### Push-to-Talk Flow
```
Right Cmd Down → audio feedback → start recording
    ↓
Right Cmd Up → stop recording → transcribe (mlx-whisper)
    ↓
Detect frontmost app → select TextInputFormat → format text
    ↓
Paste at cursor (or type character-by-character)
```

### App Context Detection
- `app_context.py` uses NSWorkspace to detect the frontmost app's bundle ID
- Matches against `data/app_profiles.json` (97 profiles with bundle IDs + regex patterns)
- Each profile specifies a `TextInputFormat`: prose, code, terminal_command, chat, email, search, etc.
- `app_controller.py` applies format-specific transformations before output

### Hotkey System
- Uses Quartz Event Tap (not Carbon) for Python 3.14+ compatibility
- Supports modifier-only keys (Right Command) via flagsChanged events
- Falls back to standard key combos for non-modifier hotkeys

## Import Convention

All imports use absolute paths with the package prefix:
```python
from tommy_talker.utils.config import load_config
from tommy_talker.utils.app_context import get_app_context, TextInputFormat
from tommy_talker.gui.dashboard import DashboardWindow
```

## Security

- API keys stored in macOS Keychain via `secure_credentials.py`
- No hardcoded credentials
- `.env` file is gitignored
- See `.env.example` for required environment variables
- 9-phase security scanner runs pre-commit

## Related HQ Resources

- `~/Tech_Projects/_HQ/standards/SECURITY.md`
- `~/Tech_Projects/_HQ/guides/universal/APPLE_SILICON.md`
- `~/Tech_Projects/_HQ/guides/universal/LOGGING.md`
- `~/Tech_Projects/_HQ/guides/universal/TESTING.md`
