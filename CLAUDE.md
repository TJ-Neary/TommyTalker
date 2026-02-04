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

TommyTalker is a privacy-first voice intelligence suite for macOS. It provides local speech-to-text via mlx-whisper, LLM-powered text rewriting via Ollama, speaker diarization via pyannote.audio, and RAG-based meeting transcription via ChromaDB.

**Status:** Alpha (Phase 5/5: Bundling)

## Key Features

- 4 Operating Modes: Cursor (live STT), Editor (STT+LLM), Meeting (diarization+RAG), HUD (screen-share invisible)
- Hardware-aware tier system (auto-selects models based on RAM)
- Local speech recognition (mlx-whisper, Metal-accelerated)
- Multiple LLM backends (Ollama local, OpenAI-compat cloud fallback)
- Speaker diarization for meeting transcripts
- Screen-share invisible HUD overlay (NSWindowSharingTypeNone)
- Global hotkeys via Carbon/Quartz
- Menu bar interface with dashboard

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
```

### Building
```bash
./build.sh  # Creates macOS .app bundle via PyInstaller
```

## Architecture

```
TommyTalker/
├── src/tommy_talker/        # Main package
│   ├── __init__.py          # Package exports
│   ├── main.py              # Entry point
│   ├── app_controller.py    # Application orchestration
│   ├── engine/              # Core AI processing
│   │   ├── audio_capture.py # Dual-stream audio pipeline
│   │   ├── transcriber.py   # mlx-whisper STT
│   │   ├── llm_client.py    # Ollama/OpenAI LLM
│   │   ├── diarizer.py      # pyannote speaker diarization
│   │   ├── rag_store.py     # ChromaDB meeting storage
│   │   ├── modes.py         # 4 mode controllers
│   │   └── session_db.py    # SQLite session metadata
│   ├── gui/                 # PyQt6 interface
│   │   ├── menu_bar.py      # System tray app
│   │   ├── dashboard.py     # Settings window
│   │   ├── hud.py           # Screen-share invisible overlay
│   │   ├── setup_guide.py   # Permission wizard
│   │   └── onboarding.py    # First-run wizard
│   └── utils/               # Infrastructure
│       ├── config.py        # Configuration management
│       ├── hardware_detect.py # Apple Silicon tier detection
│       ├── hotkeys.py       # Global hotkey manager
│       ├── permissions.py   # macOS permission checks
│       ├── typing.py        # Cursor text insertion
│       └── secure_credentials.py # Keychain integration
├── tests/                   # Test suite
├── _project/                # Project planning
│   └── DevPlan.md           # Development plan
├── data/                    # Runtime data (gitignored)
├── pyproject.toml           # Package configuration
├── requirements.txt         # Runtime dependencies
└── requirements-dev.txt     # Development dependencies
```

## Import Convention

All imports use absolute paths with the package prefix:
```python
from tommy_talker.utils.config import load_config
from tommy_talker.engine.modes import OperatingMode
from tommy_talker.gui.dashboard import DashboardWindow
```

## Security

- API keys stored in macOS Keychain via `secure_credentials.py`
- No hardcoded credentials
- `.env` file is gitignored
- See `.env.example` for required environment variables
- HuggingFace token required for speaker diarization

## Related HQ Resources

- `~/Tech_Projects/_HQ/standards/SECURITY.md`
- `~/Tech_Projects/_HQ/guides/universal/APPLE_SILICON.md`
- `~/Tech_Projects/_HQ/guides/universal/LOGGING.md`
- `~/Tech_Projects/_HQ/guides/universal/SCREEN_SHARE_INVISIBLE_OVERLAY.md`
