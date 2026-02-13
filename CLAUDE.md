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

TommyTalker is a privacy-first voice-to-text app for macOS. It provides push-to-talk dictation via Right Command key, with app-aware text formatting powered by 97 app profiles. Speech recognition runs locally via mlx-whisper on Apple Silicon.

**Status:** Active — Push-to-talk operational, 61 tests passing, cursor mode only.

## Development Commands

### Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
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
./build.sh              # Creates macOS .app bundle via PyInstaller
./build.sh --install    # Build + install to /Applications + launch on login
./build.sh --uninstall  # Remove from /Applications + disable launch on login
```

## Architecture

```
TommyTalker/
├── src/tommy_talker/           # Main package
│   ├── __init__.py             # Package exports
│   ├── main.py                 # Entry point + permission gatekeeper
│   ├── app_controller.py       # Central orchestrator (hotkeys, recording, text output)
│   ├── engine/                 # Core processing
│   │   ├── audio_capture.py    # Dual-stream audio pipeline
│   │   ├── transcriber.py      # mlx-whisper STT
│   │   └── modes.py            # Cursor mode controller + ModeManager
│   ├── gui/                    # PyQt6 interface
│   │   ├── menu_bar.py         # System tray app with TT icon
│   │   ├── dashboard.py        # Settings window
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
│   │   ├── secure_credentials.py # Credential storage (.env)
│   │   ├── path_guard.py       # Filesystem boundary enforcement
│   │   ├── code_validator.py   # AST-based code validation
│   │   └── prompt_injection.py # Prompt injection detection
│   └── data/                   # Static data files
│       └── app_profiles.json   # 97 app profiles for context detection
├── tests/                      # 61 tests across 4 files
├── scripts/
│   ├── security_scan.sh        # 9-phase pre-commit security scanner (v4)
│   └── generate_icon.py        # App icon generator (.icns)
├── resources/
│   └── com.tommytalker.app.plist  # LaunchAgent for start on login
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
- Uses Quartz Event Tap for Python 3.13+ compatibility
- Supports modifier-only keys (Right Command) via flagsChanged events
- Standard key combos (Option+R, Option+D) via keyDown/keyUp events

## Import Convention

All imports use absolute paths with the package prefix:
```python
from tommy_talker.utils.config import load_config
from tommy_talker.utils.app_context import get_app_context, TextInputFormat
from tommy_talker.gui.dashboard import DashboardWindow
```

## Security

- Credentials stored in `.env` file via `secure_credentials.py`
- No hardcoded credentials
- `.env` file is gitignored
- 9-phase security scanner runs pre-commit

## Related HQ Resources

- `~/Tech_Projects/_HQ/standards/SECURITY.md`
- `~/Tech_Projects/_HQ/guides/universal/APPLE_SILICON.md`
- `~/Tech_Projects/_HQ/guides/universal/LOGGING.md`
- `~/Tech_Projects/_HQ/guides/universal/TESTING.md`
