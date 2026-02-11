# StartHere.md — TommyTalker Project Guide

> **Purpose**: This is the single entry point for understanding the TommyTalker project.
> Read this document first, then follow links to deeper documentation as needed.
> Designed for both human developers and LLM agents.

**TommyTalker** is a privacy-first voice intelligence suite for macOS. It provides local-first speech-to-text, LLM-powered text rewriting, speaker diarization, and RAG-based meeting transcription — all running on-device with hardware-aware model selection. The system operates as a menu bar app with four operating modes (Cursor, Editor, Meeting, HUD), supports global hotkeys, and features a transparent overlay invisible to screen sharing.

---

## Document Map

### Primary Documentation

| Document | Path | Purpose |
|----------|------|---------|
| README | [./README.md](./README.md) | Project overview, features, installation, quick start |
| Project Constitution | [./gemini.md](./gemini.md) | Approved blueprint: data schemas, behavioral rules, architectural invariants |
| Development Plan | [./_project/DevPlan.md](./_project/DevPlan.md) | Architecture, phases, task tracker, technical decisions |
| Task Plan | [./task_plan.md](./task_plan.md) | Phase-based development breakdown (Phases 0-5) |
| Progress Log | [./progress.md](./progress.md) | Session log, error tracking, verification checkpoints |
| Research Findings | [./findings.md](./findings.md) | Technical research, constraints, open questions |
| Issues Backlog | [./ISSUES_BACKLOG.md](./ISSUES_BACKLOG.md) | Open and resolved issues tracker |

### Agent Instructions

| Document | Path | Purpose |
|----------|------|---------|
| Claude Code (CCT) | [./CLAUDE.md](./CLAUDE.md) | Project context and instructions for Claude Code agent |
| Antigravity (AG) | [./ANTIGRAVITY.md](./ANTIGRAVITY.md) | Project context and instructions for Antigravity agent |
| AG Startup Workflow | [./.agent/workflows/gogogo.md](./.agent/workflows/gogogo.md) | AG session startup sequence |
| AG Wrapup Workflow | [./.agent/workflows/wrapup.md](./.agent/workflows/wrapup.md) | AG session close sequence |

### Configuration & Build

| Document | Path | Purpose |
|----------|------|---------|
| pyproject.toml | [./pyproject.toml](./pyproject.toml) | Project metadata, dependencies, tool config |
| requirements.txt | [./requirements.txt](./requirements.txt) | Runtime dependencies (16 packages) |
| requirements-dev.txt | [./requirements-dev.txt](./requirements-dev.txt) | Dev dependencies (pytest, black, ruff, pyinstaller, etc.) |
| .env.example | [./.env.example](./.env.example) | Environment variable template |
| .gitignore | [./.gitignore](./.gitignore) | Git exclusion rules |
| TommyTalker.spec | [./TommyTalker.spec](./TommyTalker.spec) | PyInstaller bundling configuration |
| build.sh | [./build.sh](./build.sh) | Build macOS .app bundle |
| run_dev.sh | [./run_dev.sh](./run_dev.sh) | Development runner script |
| scripts/security_scan.sh | [./scripts/security_scan.sh](./scripts/security_scan.sh) | Pre-commit security scanner (7-category scan) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Menu Bar   │  │  Dashboard  │  │  HUD Overlay│  │  Setup/Onboarding   │ │
│  │ (menu_bar)  │  │ (dashboard) │  │   (hud)     │  │ (setup_guide,       │ │
│  │             │  │             │  │ NSWindow-   │  │  onboarding,        │ │
│  │ Mode select │  │ Settings    │  │ SharingType │  │  hotkey_selector)   │ │
│  │ Record btn  │  │ Model mgmt  │  │ None        │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                    │            │
│         └────────────────┴────────────────┴────────────────────┘            │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         APP CONTROLLER                                   ││
│  │  • Mode orchestration    • Hotkey management    • Signal coordination   ││
│  └─────────────────────────────────┬───────────────────────────────────────┘│
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                              ENGINE LAYER                                    │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          MODE MANAGER                                    ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 ││
│  │  │  CURSOR  │  │  EDITOR  │  │ MEETING  │  │   HUD    │                 ││
│  │  │ Live STT │  │ STT+LLM  │  │ STT+     │  │ Live STT │                 ││
│  │  │ →cursor  │  │ rewrite  │  │ Diarize+ │  │ →overlay │                 ││
│  │  │          │  │ →cursor  │  │ RAG      │  │          │                 ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘                 ││
│  └─────────────────────────────────┬───────────────────────────────────────┘│
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         ▼                          ▼                          ▼             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  AUDIO CAPTURE  │  │   TRANSCRIBER   │  │        LLM CLIENT           │  │
│  │  DualStream:    │  │   mlx-whisper   │  │  Ollama (local)             │  │
│  │  • Live feed    │  │   Apple Silicon │  │  ....or....                 │  │
│  │  • Archive WAV  │  │   optimized     │  │  OpenAI-compatible (cloud)  │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
│           │                    │                          │                 │
│           ▼                    ▼                          │                 │
│  ┌─────────────────┐  ┌─────────────────┐                │                 │
│  │    DIARIZER     │  │    RAG STORE    │◄───────────────┘                 │
│  │  pyannote.audio │  │    ChromaDB     │                                  │
│  │  HF token req'd │  │  vector store   │                                  │
│  └─────────────────┘  └─────────────────┘                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         SESSION DATABASE                                 ││
│  │                    SQLite: ~/Documents/TommyTalker/sessions.db          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                              UTILS LAYER                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  hardware_  │ │   config    │ │ permissions │ │   hotkeys   │           │
│  │  detect     │ │   JSON I/O  │ │  Mic/A11y   │ │   Carbon/   │           │
│  │  Tier 1-3   │ │             │ │  checks     │ │   Quartz    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   typing    │ │   logger    │ │   audio_    │ │   secure_   │           │
│  │  pyautogui  │ │  structured │ │   feedback  │ │   creds     │           │
│  │  clipboard  │ │  logging    │ │  sounds     │ │   .env      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘

DATA FLOW:
  Microphone → AudioCapture → Transcriber → [Diarizer] → [LLMClient] → Output
                    ↓                              ↓
              Archive WAV                    RAGStore (embed)
                    ↓                              ↓
              SessionDB                      ChromaDB
```

---

## Source Code Map

### Entry Points

| File | Purpose | Key Functions | Status |
|------|---------|---------------|--------|
| `src/tommy_talker/main.py` | Application entry point | `main()`, `TommyTalkerApp` | **Wired** |
| `src/tommy_talker/app_controller.py` | Central orchestrator | `AppController`, mode switching, hotkey handling | **Wired** |

### Engine Modules (`src/tommy_talker/engine/`)

| File | Purpose | Key Classes/Functions | Status |
|------|---------|----------------------|--------|
| `__init__.py` | Package exports | Re-exports all engine components | **Wired** |
| `modes.py` | Operating mode logic | `OperatingMode`, `ModeManager`, `*ModeController` | **Wired** |
| `audio_capture.py` | Dual-stream recording | `AudioCapture`, `DualStreamRecorder`, `AudioChunk` | **Wired** |
| `transcriber.py` | Speech-to-text | `Transcriber`, `TranscriptionResult` | **Wired** |
| `llm_client.py` | Ollama/Cloud LLM | `LLMClient`, `RewriteResult` | **Wired** |
| `diarizer.py` | Speaker identification | `Diarizer`, `SpeakerSegment`, `DiarizationResult` | **Wired** |
| `rag_store.py` | ChromaDB vector store | `RAGStore`, `Document`, `SearchResult` | **Wired** |
| `session_db.py` | SQLite session storage | `SessionDatabase`, `Session`, `get_session_db()` | **Wired** |

### GUI Modules (`src/tommy_talker/gui/`)

| File | Purpose | Key Classes | Status |
|------|---------|-------------|--------|
| `__init__.py` | Package exports | Re-exports GUI components | **Wired** |
| `menu_bar.py` | System tray app | `MenuBarApp` | **Wired** |
| `dashboard.py` | Settings/control panel | `DashboardWindow`, `OllamaDownloadThread` | **Wired** |
| `hud.py` | Transparent overlay | `HUDOverlay` (NSWindowSharingTypeNone) | **Wired** |
| `setup_guide.py` | Permission wizard | `SetupGuideWindow` | **Wired** |
| `onboarding.py` | First-run wizard | `OnboardingWizard`, `ModelDownloadThread` | **Wired** |
| `hotkey_selector.py` | Hotkey config UI | `HotkeySelector` | **Wired** |

### Utility Modules (`src/tommy_talker/utils/`)

| File | Purpose | Key Exports | Status |
|------|---------|-------------|--------|
| `__init__.py` | Package exports | Re-exports utility components | **Wired** |
| `config.py` | Configuration management | `UserConfig`, `load_config()`, `save_config()` | **Wired** |
| `hardware_detect.py` | RAM/chip tier detection | `HardwareProfile`, `detect_hardware()`, `TIER_CONFIG` | **Wired** |
| `permissions.py` | macOS permission checks | `PermissionStatus`, `check_permissions()` | **Wired** |
| `hotkeys.py` | Global hotkey registration | `HotkeyManager`, `KEY_CODES` | **Wired** |
| `typing.py` | Text input automation | `TypingController`, `type_at_cursor()`, `paste_text()` | **Wired** |
| `logger.py` | Logging configuration | `setup_logger()`, `get_logger()` | **Wired** |
| `audio_feedback.py` | Audio notifications | `AudioFeedback`, `get_audio_feedback()` | **Wired** |
| `secure_credentials.py` | Credential storage | `store_credential()`, `get_credential()` | **Wired** |
| `history.py` | Transcription history | `TranscriptionHistory`, `HistoryEntry` | **Orphaned** |

### Scripts

| File | Purpose | Status |
|------|---------|--------|
| `build.sh` | Build macOS .app bundle via PyInstaller | **Wired** |
| `run_dev.sh` | Run application in development mode | **Wired** |
| `scripts/security_scan.sh` | Pre-commit security scanner | **Wired** |

### Assets (`SW/Contents/Resources/`)

| Type | Files | Purpose |
|------|-------|---------|
| Audio | `Start{1-4}.m4a`, `Stop{1-4}.m4a`, `noResult{1-4}.m4a`, `Intro.m4a`, `Loop.m4a` | UI sound feedback |
| Icons | `AppIcon.icns` | Application icon |
| Templates | `*.jinja` (deepseek, gpt-oss, llama, mistral, phi, ministral) | LLM prompt templates |
| Frameworks | `Frameworks/`, `*.bundle/` | Pre-compiled dependencies |

---

## Known Issues & Discrepancies

| Issue | Type | Severity | Description |
|-------|------|----------|-------------|
| pyobjc Python 3.13 | Compatibility | **HIGH** | Circular import error with objc module. HUD overlay visible to screen sharing. Workaround: Use Python 3.12. |
| torchcodec FFmpeg | Compatibility | **MEDIUM** | FFmpeg 8.0.1 installed but torchcodec only supports v4-7. Speaker diarization may have issues. |
| `utils/history.py` | Orphaned Code | **LOW** | Module defined but never imported. References non-existent `get_data_path()` from `utils.config`. Will fail if imported. |
| Missing Tests | Gap | **MEDIUM** | Test infrastructure ready (conftest.py fixtures, test_example.py stub) but no production tests written. |
| No CI/CD | Gap | **LOW** | No GitHub Actions workflows configured. |

---

## Development Status

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 0 | Initialization | **Complete** | Blueprint approved, task plan created |
| 1 | Blueprint | **Complete** | Data schemas, behavioral rules defined in gemini.md |
| 2 | Link | **Complete** | File structure, requirements.txt, pyproject.toml |
| 3 | Architect | **Complete** | Hardware detection, audio pipeline, permissions, GUI |
| 4 | Stylize | **Complete** | All 4 modes implemented, data management, ChromaDB |
| 5 | Trigger | **In Progress** | PyInstaller bundling, integration tests, final delivery |

**Overall Maturity**: Alpha — Core functionality implemented, bundling in progress.

---

## Roadmap

See [task_plan.md](./task_plan.md) for phase breakdown and [_project/DevPlan.md](./_project/DevPlan.md) for architecture and task tracker.

| Priority | Item | Status |
|----------|------|--------|
| P0 | Fix Python 3.13 pyobjc issue | Blocked (upstream) |
| P1 | Complete PyInstaller bundling | In Progress |
| P2 | Write unit tests | Not Started |
| P3 | Add CI/CD workflows | Not Started |
| P4 | Resolve FFmpeg/torchcodec mismatch | Not Started |

---

## Quick Reference

### Running the Application

```bash
# Development mode
./run_dev.sh

# Or manually
source .venv/bin/activate
PYTHONPATH=src python -m tommy_talker.main

# Or after pip install -e .
tommytalker

# Build macOS .app
./build.sh
# Output: dist/TommyTalker.app
```

### Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src/tommy_talker --cov-report=term-missing
```

### Default Hotkeys

| Hotkey | Action |
|--------|--------|
| `Cmd+Shift+Space` | Cursor Mode (live transcription) |
| `Cmd+Shift+R` | Toggle Recording |
| `Cmd+Shift+D` | Open Dashboard |

### Key Entry Points

| Entry Point | Transport/Protocol |
|-------------|-------------------|
| `src/tommy_talker/main.py:main()` | Application launch |
| `src/tommy_talker/gui/menu_bar.py` | System tray (PyQt6) |
| `src/tommy_talker/gui/dashboard.py` | Settings UI (PyQt6) |
| Global hotkeys | Carbon/Quartz events |

### Configuration Files

| File | Location | Gitignored? |
|------|----------|-------------|
| `.env` | Project root | Yes |
| `.env.example` | Project root | No |
| `config.json` | `~/Documents/TommyTalker/` | N/A (user data) |
| `sessions.db` | `~/Documents/TommyTalker/` | N/A (user data) |
| `chroma/` | `~/Documents/TommyTalker/` | N/A (user data) |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HUGGINGFACE_TOKEN` | (none) | Required for pyannote.audio diarization |
| `OPENAI_API_KEY` | (none) | Cloud LLM mode (optional) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Cloud LLM endpoint |

---

## Technology Stack

| Component | Technology | Version/Detail |
|-----------|------------|----------------|
| Language | Python | 3.12+ (3.13 has pyobjc issues) |
| GUI Framework | PyQt6 | 6.6.0+ |
| Speech-to-Text | mlx-whisper | Apple Silicon optimized |
| LLM (Local) | Ollama | 0.1.0+ |
| LLM (Cloud) | httpx | OpenAI-compatible APIs |
| Diarization | pyannote.audio | 3.1+ (HF token required) |
| Vector Store | ChromaDB | 0.4.0+ |
| Database | SQLite | Standard library |
| Audio I/O | sounddevice, soundfile | 0.4.6+, 0.12.1+ |
| Hardware Detection | psutil | 5.9.0+ |
| Text Input | pyautogui | 0.9.54+ |
| macOS Integration | pyobjc-framework-Cocoa/Quartz | 10.0+ |
| Credentials | python-dotenv | 1.0.0+ |
| Build | PyInstaller | Via TommyTalker.spec |

### Hardware Tiers

| Tier | RAM | Recommended Model | Use Case |
|------|-----|-------------------|----------|
| 1 | <16GB | Small/quantized | Basic transcription |
| 2 | 16-32GB | Medium | Full features |
| 3 | >32GB | Large | Maximum quality |

---

## Runtime & Generated Files

Files that exist at runtime but are gitignored:

| Type | Path/Pattern | Purpose |
|------|--------------|---------|
| Virtual env | `.venv/`, `venv/` | Python dependencies |
| Python cache | `__pycache__/`, `*.pyc` | Compiled bytecode |
| Build artifacts | `build/`, `dist/` | PyInstaller output |
| App bundle assets | `SW/` | Pre-compiled frameworks, audio, icons, templates |
| Logs | `*.log` | Application logs |
| Runtime data | `data/` | Local data directory |
| Test cache | `.pytest_cache/`, `.coverage` | Test artifacts |
| Linter cache | `.ruff_cache/` | Ruff linter cache |
| ML models | `*.gguf`, `*.bin`, `*.safetensors` | Large model files |
| Secrets | `.env`, `*.pem`, `*.key` | Credentials |
| User data | `~/Documents/TommyTalker/` | Config, sessions, recordings, embeddings |

---

## Project Templates Integration

**Status**: This project is registered in `Tech_Projects/_HQ/SYNC_STATUS.yaml` (as of 2026-02-04).

**Relevant guides** (based on project features):
- `Tech_Projects/_HQ/guides/universal/LOGGING.md` — Structured logging patterns
- `Tech_Projects/_HQ/guides/universal/ERROR_HANDLING.md` — Exception hierarchies
- `Tech_Projects/_HQ/guides/universal/TESTING.md` — Testing strategy
- `Tech_Projects/_HQ/guides/universal/APPLE_SILICON.md` — Apple Silicon optimization
- `Tech_Projects/_HQ/guides/universal/ENV_CONFIGURATION.md` — .env patterns
- `Tech_Projects/_HQ/guides/universal/RAG_HITL_PIPELINE.md` — RAG pipeline patterns

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Python Modules | 28 |
| Lines of Code | ~6,350 |
| Documentation Files | 12 .md files |
| Operating Modes | 4 (Cursor, Editor, Meeting, HUD) |
| Runtime Dependencies | 16 (requirements.txt) |
| Dev Dependencies | 5+ (requirements-dev.txt) |
| Orphaned Modules | 1 (`utils/history.py`) |
| Test Files | 1 stub + conftest.py fixtures |
| TODO/FIXME Comments | 0 |

---

*Last updated: 2026-02-11*
