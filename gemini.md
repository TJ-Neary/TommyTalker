# TommyTalker — Project Constitution

> **Last Updated**: 2026-01-24  
> **Status**: ✅ APPROVED

---

## 1. North Star

**Build TommyTalker**: A professional, local-first macOS application for voice intelligence featuring:
- Dual-interface (Menu Bar + Dashboard)
- Hardware-aware AI logic that scales from MacBook Air to Max
- Four distinct operating modes (Cursor, Editor, Scribe, HUD)

### Core Philosophy
| Principle | Description |
|-----------|-------------|
| **Privacy-First** | All processing local. No cloud dependencies for core features. |
| **Local** | Data stored on local filesystem, ChromaDB, SQLite |
| **Hardware-Agnostic** | Scales from 8GB Air to 128GB Max via Smart Logic |
| **Modular** | Clean separation: `/gui`, `/engine`, `/utils` |

---

## 2. Data Schemas

### 2.1 Session Metadata (SQLite)
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mode TEXT CHECK(mode IN ('cursor', 'editor', 'scribe', 'hud')),
    duration_seconds INTEGER,
    audio_path TEXT,
    transcript_path TEXT,
    speaker_count INTEGER DEFAULT 1
);
```

### 2.2 Hardware Profile
```python
@dataclass
class HardwareProfile:
    ram_gb: int
    chip_type: str  # "M1", "M2", "M3", "M4", etc.
    tier: int       # 1, 2, or 3
    
    whisper_model: str      # "distil-whisper-small" | "medium" | "large-v3"
    llm_model: str          # "phi-3" | "llama-3-8b"
    diarization_enabled: bool
```

### 2.3 Recording Manifest
```python
@dataclass
class Recording:
    id: str                     # UUID
    timestamp: datetime
    audio_path: Path            # ~/Documents/MindMeld/Recordings/*.wav
    transcript: str | None
    mode: Literal["cursor", "editor", "scribe", "hud"]
    speakers: list[str]         # For Scribe mode diarization
```

### 2.4 User Configuration
```python
@dataclass
class UserConfig:
    vocabulary: list[str]       # Custom words for Whisper initial_prompt
    style_guide_path: Path | None
    hotkeys: dict[str, str]     # See DEFAULT_HOTKEYS below
    default_mode: str
    auto_clear_session: bool
    huggingface_token: str | None  # Required for pyannote.audio
    advanced_mode: bool         # Allow manual Ollama model tags

# DEFAULT HOTKEYS (Approved)
DEFAULT_HOTKEYS = {
    "cursor_mode": "Cmd+Shift+Space",
    "toggle_record": "Cmd+Shift+R",
    "open_dashboard": "Cmd+Shift+D"
}

# DEFAULT VOCABULARY (Whisper initial_prompt)
DEFAULT_VOCABULARY = [
    "MindMeld", "TommyTalker", "RAG", "LLM", "Diarization",
    "PyObjC", "PyQt6", "Ollama", "vector store"
]
```

---

## 3. Behavioral Rules

### 3.1 Smart Logic Installer (Hardware Detection)

| Tier | RAM | Whisper Model | LLM Model | Diarization |
|------|-----|---------------|-----------|-------------|
| 1 | <16GB | `distil-whisper-small` | `llama3.2:3b` | ❌ Disabled |
| 2 | 16-32GB | `distil-whisper-medium.en` | `llama3.1:8b` | ⚠️ Optional |
| 3 | >32GB | `distil-whisper-large-v3` | `gemma2:27b` | ✅ Enabled |

**Rule**: Query RAM on launch. Auto-configure based on tier. Show "Model Manager" window for manual override.

**Model Manager Features**:
- "Download" button with progress bar for default models
- **Advanced Mode** toggle in Settings:
  - When enabled: User can manually type any Ollama model tag (e.g., `mistral:latest`)
  - Suppresses auto-checks for users managing models via terminal

### 3.2 Dual-Stream Audio Pipeline

```
┌─────────────────────────────────────────────────────┐
│                   MICROPHONE INPUT                  │
└─────────────────────┬───────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│   STREAM A      │       │   STREAM B      │
│   (Live Feed)   │       │  (Archive Feed) │
│                 │       │                 │
│  mlx_whisper    │       │  Save to disk   │
│  → Live text    │       │  → .wav file    │
└─────────────────┘       └─────────────────┘
```

**Rule**: Both streams run in parallel. Stream B saves immediately with timestamp. Stream A processes through mlx_whisper.

### 3.3 The 4 Operating Modes

| Mode | Pipeline | Key Feature | Hotkey |
|------|----------|-------------|--------|
| **Cursor** | Listen → Transcribe → Type at cursor | Inject `vocabulary` into `initial_prompt` | `Cmd+Shift+Space` |
| **Editor** | Record → Transcribe → LLM Rewrite → Paste | Check `style_guide.txt` before rewrite | — |
| **Scribe** | Meeting → Timestamps + Diarization | Speaker A/B labels via pyannote | — |
| **HUD** | Transparent overlay | Screen-share invisible (see 3.4) | — |

**Global Hotkeys**:
- Toggle Recording: `Cmd+Shift+R`
- Open Dashboard: `Cmd+Shift+D`

### 3.4 Privacy Constraints

**HUD Invisibility Rule**:
```python
# MUST use pyobjc to set:
window.sharingType = NSWindowSharingTypeNone
```
This ensures the HUD is invisible to Zoom, Teams, and other screen sharing tools.

**Session Hygiene Rule**:
- "Clear Session" button MUST wipe ChromaDB vectors
- Prevents data bleeding between interviews/sessions

### 3.5 Settings Tab Requirements

**HuggingFace Token**:
- Text field to input/save HuggingFace User Access Token
- Required for pyannote.audio authentication at runtime
- Store in `.env` file (gitignored)

**Cloud Mode (Hybrid Cloud Uplink)**:
- Toggle to enable Cloud Mode for LLM offloading
- Fields for API Base URL and Model selection
- API Key stored in `.env` file (never in config.json)
- Supports OpenAI, Groq, OpenRouter (any OpenAI-compatible endpoint)

**Advanced Mode**:
- Toggle to bypass default model list
- Allows manual entry of custom Ollama model tags (e.g., `custom:model`)

**Environment Variables** (`.env` file):
```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
HUGGINGFACE_TOKEN=hf_...
```

### 3.6 Permission Gatekeeper

**On First Run**:
1. Check Microphone permission → If missing, show Setup Guide
2. Check Accessibility permission → If missing, show Setup Guide
3. Block main app until permissions granted

---

## 4. Architectural Invariants

### 4.1 File Structure (MANDATORY)
```
TommyTalker/
├── main.py                 # Entry point
├── requirements.txt
├── pyproject.toml
├── gui/
│   ├── __init__.py
│   ├── menu_bar.py         # System tray / menu bar
│   ├── dashboard.py        # Main control panel
│   ├── hud.py              # Transparent overlay
│   └── setup_guide.py      # Permission wizard
├── engine/
│   ├── __init__.py
│   ├── audio_capture.py    # sounddevice recording
│   ├── transcriber.py      # mlx_whisper STT
│   ├── llm_client.py       # Ollama integration
│   ├── diarizer.py         # pyannote speaker ID
│   └── rag_store.py        # ChromaDB operations
├── utils/
│   ├── __init__.py
│   ├── hardware_detect.py  # RAM/chip detection
│   ├── config.py           # User preferences
│   ├── permissions.py      # macOS permission checks
│   └── hotkeys.py          # Global hotkey registration
└── data/
    └── .gitkeep            # Created at runtime
```

### 4.2 Technology Stack (LOCKED)
| Component | Library | Rationale |
|-----------|---------|-----------|
| Language | Python 3.12+ | Modern async, type hints |
| GUI | PyQt6 | Menu bar, dashboard, HUD support |
| Native Bridge | pyobjc | Global hotkeys, window hiding |
| Audio Record | sounddevice | Low-latency capture |
| Audio Save | soundfile | WAV/MP3 export |
| STT | mlx_whisper | Apple Silicon optimized |
| LLM | ollama | Local inference |
| Diarization | pyannote.audio | Speaker identification |
| Vector DB | chromadb | RAG storage |
| Metadata DB | sqlite3 | Session tracking |

### 4.3 Data Paths (FIXED)
| Data Type | Path |
|-----------|------|
| Recordings | `~/Documents/TommyTalker/Recordings/` |
| Config | `~/Documents/TommyTalker/config.json` |
| Style Guide | `~/Documents/TommyTalker/style_guide.txt` |
| ChromaDB | `~/Documents/TommyTalker/chroma/` |
| SQLite | `~/Documents/TommyTalker/sessions.db` |

---

## 5. Do-Not Rules

1. **DO NOT** send any audio or text to external APIs
2. **DO NOT** use a single-file architecture
3. **DO NOT** hard-code model names (use hardware detection)
4. **DO NOT** skip permission checks on launch
5. **DO NOT** leave ChromaDB data between sessions without explicit user choice
6. **DO NOT** make HUD visible to screen sharing tools

---

## 6. Success Criteria

- [ ] App launches from Menu Bar on macOS
- [ ] Hardware tier detected correctly
- [ ] All 4 modes functional
- [ ] HUD invisible to screen share (verified)
- [ ] PyInstaller bundles to working `.app`
- [ ] Clean session wipe works
