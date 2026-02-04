# TommyTalker

**Privacy-First Voice Intelligence Suite for macOS**

A professional, local-first macOS application for voice intelligence featuring:
- 🎤 **Dual-Interface**: Menu Bar + Dashboard
- 🧠 **Hardware-Aware AI**: Scales from MacBook Air to Max
- 🔒 **Privacy-First**: All processing happens locally

## Features

### 4 Operating Modes

| Mode | Description | Hotkey |
|------|-------------|--------|
| **Cursor** | Live transcription → Type at cursor | `Cmd+Shift+Space` |
| **Editor** | Record → LLM Rewrite → Paste | — |
| **Scribe** | Meeting assistant with speaker diarization | — |
| **HUD** | Transparent overlay (invisible to screen sharing) | — |

### Smart Logic (Hardware Detection)

TommyTalker automatically detects your hardware and recommends appropriate AI models:

| Tier | RAM | Whisper Model | LLM Model | Diarization |
|------|-----|---------------|-----------|-------------|
| 1 | <16GB | distil-whisper-small | phi-3 | ❌ |
| 2 | 16-32GB | distil-whisper-medium | llama-3-8b | Optional |
| 3 | >32GB | distil-whisper-large-v3 | llama-3-8b | ✅ |

## Requirements

- macOS 12.0+ (Monterey or later)
- Python 3.12+
- Apple Silicon recommended (M1/M2/M3/M4)
- Ollama installed for LLM features

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/TommyTalker.git
cd TommyTalker

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Ollama models (optional, can be done via GUI)
ollama pull phi3:mini
ollama pull llama3:8b
```

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the application
python main.py
```

On first launch:
1. Grant **Microphone** permission when prompted
2. Grant **Accessibility** permission for global hotkeys
3. The app will detect your hardware tier and recommend models
4. Configure your HuggingFace token in Settings if using diarization

## Project Structure

```
TommyTalker/
├── main.py                 # Entry point
├── requirements.txt
├── pyproject.toml
├── gui/                    # PyQt6 UI components
│   ├── menu_bar.py         # System tray
│   ├── dashboard.py        # Main control panel
│   ├── hud.py              # Transparent overlay
│   └── setup_guide.py      # Permission wizard
├── engine/                 # Audio/AI processing
│   ├── audio_capture.py    # Dual-stream recording
│   ├── transcriber.py      # mlx_whisper STT
│   ├── llm_client.py       # Ollama integration
│   ├── diarizer.py         # Speaker identification
│   └── rag_store.py        # ChromaDB operations
└── utils/                  # Core utilities
    ├── hardware_detect.py  # RAM/chip detection
    ├── config.py           # User preferences
    ├── permissions.py      # macOS permission checks
    └── hotkeys.py          # Global hotkey registration
```

## Data Storage

All data is stored locally in `~/Documents/TommyTalker/`:
- **Recordings**: `~/Documents/TommyTalker/Recordings/`
- **Config**: `~/Documents/TommyTalker/config.json`
- **ChromaDB**: `~/Documents/TommyTalker/chroma/`
- **Sessions**: `~/Documents/TommyTalker/sessions.db`

## Privacy & Security

- 🔒 **100% Local Processing**: No audio or text leaves your machine
- 🙈 **HUD Screen-Share Invisibility**: Uses `NSWindowSharingTypeNone`
- 🧹 **Session Hygiene**: One-click wipe of all session data
- 🔑 **Secure Token Storage**: HuggingFace tokens stored locally

## License

MIT License - See LICENSE file for details
