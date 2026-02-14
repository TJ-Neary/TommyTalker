# TommyTalker

![TommyTalker Hero](assets/images/hero-banner.png)

![Build](https://img.shields.io/github/actions/workflow/status/TJ-Neary/TommyTalker/ci.yml?style=flat-square)
![Tests](https://img.shields.io/badge/tests-95%20passing-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12+-blue?style=flat-square)

**Privacy-first voice-to-text for macOS with app-aware formatting.**

TommyTalker provides push-to-talk dictation that runs entirely on-device via mlx-whisper on Apple Silicon. Hold Right Command, speak, release — transcribed text appears at the cursor, automatically formatted for the frontmost application. No cloud services. No data leaves the machine.

## How It Works

1. **Hold** Right Command — recording starts with audio feedback
2. **Speak** — voice is captured locally
3. **Release** — speech is transcribed via mlx-whisper and pasted at the cursor

The frontmost application is detected automatically, and text formatting adapts:

| App Type | Formatting | Examples |
|----------|-----------|----------|
| **Prose** | Sentence case, proper punctuation | Pages, Notes, Word, Google Docs |
| **Code Editor** | Lowercase, no trailing punctuation | VS Code, Xcode, Terminal (vim) |
| **Terminal** | Filler words stripped, command-ready | Terminal, iTerm2, Warp |
| **Chat** | Casual case, no period at end | Slack, Messages, Discord, Teams |
| **Email** | Sentence case, professional tone | Mail, Outlook, Gmail |
| **Search** | All lowercase, no punctuation | Safari, Chrome, Spotlight |

97 app profiles are included, with category-based fallback for unrecognized apps.

## Features

### Core
- **Push-to-Talk** — Right Command key: hold to record, release to paste
- **App-Aware Formatting** — 97 app profiles with context-sensitive text output
- **100% Local** — mlx-whisper on Apple Silicon, nothing leaves the machine
- **Hardware-Aware** — Auto-selects Whisper model size based on available RAM

### Accuracy
- **Word Replacement** — Configurable patterns to correct persistent STT misrecognitions (e.g., "Tommy" → "TommyTalker")
- **Context Formatting** — Strips filler words for terminals, lowercases for search bars, capitalizes for prose

### Interface
- **Menu Bar App** — Custom TT icon in the system tray (red when recording)
- **Session Recording** — Record full audio sessions to WAV via the menu bar
- **Settings Dashboard** — Configure Whisper model, word replacements, and preferences
- **First-Run Wizard** — Guided setup for microphone and accessibility permissions

### Deployment
- **macOS App Bundle** — `build.sh` packages via PyInstaller
- **Start on Login** — LaunchAgent integration (`build.sh --install`)
- **CI/CD** — GitHub Actions pipeline: lint, test, security scan

## Hardware Tiers

TommyTalker detects available RAM and selects an appropriate Whisper model:

| Tier | RAM | Whisper Model |
|------|-----|---------------|
| 1 | <16 GB | distil-whisper-small |
| 2 | 16–32 GB | distil-whisper-medium |
| 3 | >32 GB | distil-whisper-large-v3 |

A custom model can be specified in the settings dashboard.

## Quick Start

```bash
git clone https://github.com/TJ-Neary/TommyTalker.git
cd TommyTalker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m tommy_talker.main
```

On first launch, grant **Microphone** and **Accessibility** permissions when prompted.

## Architecture

```
Right Cmd Down → audio feedback → start recording (sounddevice)
Right Cmd Up  → stop recording → transcribe (mlx-whisper)
            → detect frontmost app (NSWorkspace → 97 profiles)
            → format text (TextInputFormat rules)
            → apply word replacements
            → paste at cursor (clipboard + Cmd+V)
```

Key components:

| Component | Purpose |
|-----------|---------|
| `app_controller.py` | Push-to-talk orchestration, hotkey dispatch, text output |
| `engine/transcriber.py` | mlx-whisper speech-to-text (Metal-accelerated) |
| `engine/audio_capture.py` | Dual-stream audio pipeline + session recorder |
| `utils/app_context.py` | Frontmost app detection, 97 profiles, TextInputFormat |
| `utils/hotkeys.py` | Quartz Event Tap for modifier-only key support |
| `gui/menu_bar.py` | System tray with custom TT icon |

See [ARCHITECTURE.md](ARCHITECTURE.md) for full C4 diagrams and design decisions.

## Project Structure

```
TommyTalker/
├── src/tommy_talker/           # Main package
│   ├── main.py                 # Entry point + permission gatekeeper
│   ├── app_controller.py       # Central orchestrator
│   ├── engine/                 # Core processing
│   │   ├── audio_capture.py    # Dual-stream audio + session recorder
│   │   ├── transcriber.py      # mlx-whisper STT
│   │   └── modes.py            # Cursor mode controller
│   ├── gui/                    # PyQt6 interface
│   │   ├── menu_bar.py         # System tray with TT icon
│   │   ├── dashboard.py        # Settings window
│   │   ├── setup_guide.py      # Permission wizard
│   │   └── onboarding.py       # First-run wizard
│   ├── utils/                  # Infrastructure
│   │   ├── app_context.py      # App detection + 97 profiles
│   │   ├── audio_feedback.py   # System sound playback
│   │   ├── config.py           # Configuration + migration
│   │   ├── hardware_detect.py  # Apple Silicon tier detection
│   │   ├── hotkeys.py          # Quartz Event Tap manager
│   │   ├── logger.py           # Structured logging
│   │   ├── permissions.py      # macOS permission checks
│   │   └── typing.py           # Cursor text insertion
│   └── data/
│       └── app_profiles.json   # 97 app profiles
├── tests/                      # 95 tests across 5 files
├── scripts/
│   ├── security_scan.sh        # 9-phase pre-commit security scanner
│   └── generate_icon.py        # App icon generator (.icns)
├── .github/workflows/ci.yml    # CI pipeline
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Configuration

All settings are managed through the dashboard UI and persisted to `~/Documents/TommyTalker/config.json`.

| Setting | Default | Description |
|---------|---------|-------------|
| Whisper Model | Auto (by hardware tier) | Speech recognition model |
| App Context | Enabled | Detect frontmost app for formatting |
| Audio Feedback | Enabled | Play sounds on record start/stop |
| Feedback Variation | Enabled | Rotate between system sounds |
| Word Replacements | Empty | Correct persistent misrecognitions |
| Verbose Logging | Disabled | Detailed log output |

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/tommy_talker --cov-report=term-missing

# Mutation testing
mutmut run
```

95 tests covering app context detection, modifier-only hotkeys, audio feedback, word replacement, session recording, and configuration management.

## Privacy and Security

- **100% Local** — No audio or text leaves the machine
- **No Telemetry** — No usage tracking, analytics, or phone-home
- **Pre-Commit Security** — 9-phase scanner checks for secrets, PII, and sensitive paths
- **AST Code Validation** — Static analysis for code safety
- **Filesystem Boundary Enforcement** — Path guard prevents out-of-bounds access

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| GUI | PyQt6 |
| Speech-to-Text | mlx-whisper (Apple Silicon Metal) |
| Hotkeys | Quartz Event Tap (modifier-only key support) |
| Audio | sounddevice + soundfile |
| App Detection | pyobjc (NSWorkspace via Cocoa framework) |
| Hardware Detection | psutil |
| Packaging | PyInstaller |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License — See [LICENSE](LICENSE) for details.
