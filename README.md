# TommyTalker

![TommyTalker Hero](assets/images/hero-banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 76 Passing](https://img.shields.io/badge/tests-76%20passing-brightgreen.svg)](tests/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Privacy-First Voice-to-Text for macOS**

TommyTalker is a local-first macOS voice dictation app built for Apple Silicon. Hold the Right Command key, speak, release — your words appear at the cursor, automatically formatted for the app you're using. All processing happens on-device via mlx-whisper. No cloud. No data leaves your machine.

## How It Works

**Push-to-Talk in 3 Steps:**

1. **Hold** Right Command key — recording starts with audio feedback
2. **Speak** — your voice is captured locally
3. **Release** — speech is transcribed and pasted at your cursor

TommyTalker detects the frontmost application and automatically formats your text:

| App Type | Formatting | Examples |
|----------|-----------|----------|
| **Prose** | Sentence case, proper punctuation | Pages, Notes, Word, Google Docs |
| **Code Editor** | Lowercase, no trailing punctuation | VS Code, Xcode, Terminal (vim) |
| **Terminal** | Filler words stripped, command-ready | Terminal, iTerm2, Warp |
| **Chat** | Casual case, no period at end | Slack, Messages, Discord, Teams |
| **Email** | Sentence case, professional tone | Mail, Outlook, Gmail |
| **Search** | All lowercase, no punctuation | Safari, Chrome, Spotlight |

97 app profiles are included out of the box, with automatic category-based fallback for unrecognized apps.

## Features

- **Push-to-Talk** — Right Command key hold-to-record, release-to-paste
- **App-Aware Formatting** — 97 app profiles with context-sensitive text output
- **100% Local** — mlx-whisper runs on Apple Silicon, nothing leaves your machine
- **Hardware-Aware** — Auto-selects Whisper model size based on your Mac's RAM
- **Audio Feedback** — Distinct sounds for recording start, stop, and errors
- **Menu Bar App** — Unobtrusive system tray with dashboard for settings
- **First-Run Wizard** — Guided setup for permissions and model downloads

### Hardware Tiers

TommyTalker detects your hardware and selects appropriate models:

| Tier | RAM | Whisper Model | LLM Model |
|------|-----|---------------|-----------|
| 1 | <16GB | distil-whisper-small | phi-3 |
| 2 | 16-32GB | distil-whisper-medium | llama-3-8b |
| 3 | >32GB | distil-whisper-large-v3 | llama-3-8b |

### Engine Capabilities (Available for Future Modes)

The engine layer includes additional capabilities that are built and tested but not yet exposed in the UI:

- **LLM Text Rewriting** — Ollama-powered rewrite-before-paste (Editor mode)
- **Speaker Diarization** — pyannote.audio for meeting transcripts (Meeting mode)
- **RAG Storage** — ChromaDB vector store for searchable transcripts (Meeting mode)
- **HUD Overlay** — Screen-share invisible overlay via `NSWindowSharingTypeNone` (HUD mode)

## Requirements

- macOS 12.0+ (Monterey or later)
- Python 3.12+
- Apple Silicon recommended (M1/M2/M3/M4)
- Ollama installed for LLM features (optional)

## Installation

```bash
# Clone the repository
git clone https://github.com/TJ-Neary/TommyTalker.git
cd TommyTalker

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the application
PYTHONPATH=src python -m tommy_talker.main

# Or after pip install -e .
tommytalker
```

On first launch:
1. Grant **Microphone** permission when prompted
2. Grant **Accessibility** permission for global hotkeys
3. The app detects your hardware tier and recommends models
4. Hold **Right Command** to start dictating

## Project Structure

```
TommyTalker/
├── src/tommy_talker/           # Main package
│   ├── main.py                 # Entry point + permission gatekeeper
│   ├── app_controller.py       # Central orchestrator (hotkeys, recording, output)
│   ├── engine/                 # Core AI processing
│   │   ├── audio_capture.py    # Dual-stream audio pipeline
│   │   ├── transcriber.py      # mlx-whisper speech-to-text
│   │   ├── llm_client.py       # Ollama/OpenAI LLM client
│   │   ├── diarizer.py         # pyannote speaker diarization
│   │   ├── rag_store.py        # ChromaDB meeting storage
│   │   ├── modes.py            # Operating mode controllers
│   │   └── session_db.py       # SQLite session metadata
│   ├── gui/                    # PyQt6 interface
│   │   ├── menu_bar.py         # System tray app
│   │   ├── dashboard.py        # Settings window
│   │   ├── hud.py              # Screen-share invisible overlay
│   │   ├── setup_guide.py      # Permission wizard
│   │   └── onboarding.py       # First-run wizard
│   ├── utils/                  # Infrastructure
│   │   ├── app_context.py      # App detection + text format selection
│   │   ├── audio_feedback.py   # System sound playback
│   │   ├── config.py           # Configuration management
│   │   ├── hardware_detect.py  # Apple Silicon tier detection
│   │   ├── hotkeys.py          # Quartz Event Tap hotkey manager
│   │   ├── logger.py           # Structured logging
│   │   ├── permissions.py      # macOS permission checks
│   │   ├── typing.py           # Cursor text insertion
│   │   └── secure_credentials.py # Keychain integration
│   └── data/                   # Static data files
│       └── app_profiles.json   # 97 app profiles for context detection
├── tests/                      # 76 tests across 5 test files
├── scripts/
│   └── security_scan.sh        # 9-phase pre-commit security scanner
├── pyproject.toml              # Package configuration
├── requirements.txt            # Runtime dependencies
└── requirements-dev.txt        # Development dependencies
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/tommy_talker --cov-report=term-missing

# Mutation testing
mutmut run
```

76 tests covering app context detection, modifier-only hotkeys, audio feedback, app-aware LLM formatting, and core infrastructure.

## Data Storage

All user data is stored locally in `~/Documents/TommyTalker/`:

| Data | Path | Purpose |
|------|------|---------|
| Config | `~/Documents/TommyTalker/config.json` | User preferences |
| Recordings | `~/Documents/TommyTalker/Recordings/` | Audio files |
| Sessions | `~/Documents/TommyTalker/sessions.db` | Session metadata |
| Embeddings | `~/Documents/TommyTalker/chroma/` | Meeting RAG store |

## Privacy & Security

- **100% Local Processing** — No audio or text leaves your machine
- **No Telemetry** — No usage tracking, no analytics, no phone-home
- **Secure Credentials** — API keys stored in macOS Keychain
- **Pre-Commit Security** — 9-phase scanner checks for secrets, PII, and sensitive paths

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| GUI | PyQt6 |
| Speech-to-Text | mlx-whisper (Apple Silicon Metal) |
| LLM | Ollama (local) / OpenAI-compatible (cloud) |
| Hotkeys | Quartz Event Tap (modifier-only key support) |
| Audio | sounddevice + soundfile |
| Diarization | pyannote.audio |
| Vector Store | ChromaDB |
| Hardware Detection | psutil |
| macOS Integration | pyobjc (Cocoa + Quartz frameworks) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License — See [LICENSE](LICENSE) for details.
