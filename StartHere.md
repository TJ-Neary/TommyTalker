# StartHere.md — TommyTalker Project Guide

> **Purpose**: This is the single entry point for understanding the TommyTalker project.
> Read this document first, then follow links to deeper documentation as needed.
> Designed for both human developers and LLM agents.

**TommyTalker** is a privacy-first voice-to-text app for macOS. Hold the Right Command key, speak, release — your words appear at the cursor, automatically formatted for the app you're using. All speech recognition runs locally via mlx-whisper on Apple Silicon. The engine also includes LLM rewriting, speaker diarization, and RAG storage — built and tested but hidden from the UI, reserved for future re-enablement.

---

## Document Map

### Primary Documentation

| Document | Path | Purpose |
|----------|------|---------|
| README | [./README.md](./README.md) | Project overview, features, installation, quick start |
| Development Plan | [./_project/DevPlan.md](./_project/DevPlan.md) | Architecture, phases, task tracker, technical decisions |
| Contributing Guide | [./CONTRIBUTING.md](./CONTRIBUTING.md) | Guidelines for contributors, code style, and workflow |
| License | [./LICENSE](./LICENSE) | MIT License |

### Agent Instructions

| Document | Path | Purpose |
|----------|------|---------|
| Claude Code (CCT) | [./CLAUDE.md](./CLAUDE.md) | Project context and instructions for Claude Code agent |
| Antigravity (AG) | [./ANTIGRAVITY.md](./ANTIGRAVITY.md) | Project context and instructions for Antigravity agent |
| AG Startup Workflow | [./.agent/workflows/gogogo.md](./.agent/workflows/gogogo.md) | AG session startup sequence |
| AG Wrapup Workflow | [./.agent/workflows/wrapup.md](./.agent/workflows/wrapup.md) | AG session close sequence |

### Legacy Documentation

These files were created during the initial Gemini-based build phase and are kept for historical reference. The Development Plan (`_project/DevPlan.md`) is now the authoritative planning document.

| Document | Path | Purpose |
|----------|------|---------|
| Blueprint | [./gemini.md](./gemini.md) | Original data schemas and behavioral rules |
| Task Plan | [./task_plan.md](./task_plan.md) | Original phase-based development breakdown |
| Progress Log | [./progress.md](./progress.md) | Original session log and error tracking |
| Research | [./findings.md](./findings.md) | Technical research and open questions |
| Issues Backlog | [./ISSUES_BACKLOG.md](./ISSUES_BACKLOG.md) | Original issues tracker |

### Configuration & Build

| Document | Path | Purpose |
|----------|------|---------|
| pyproject.toml | [./pyproject.toml](./pyproject.toml) | Project metadata, dependencies, tool config |
| requirements.txt | [./requirements.txt](./requirements.txt) | Runtime dependencies |
| requirements-dev.txt | [./requirements-dev.txt](./requirements-dev.txt) | Dev dependencies (pytest, black, ruff, mutmut, pyinstaller) |
| .env.example | [./.env.example](./.env.example) | Environment variable template |
| .gitignore | [./.gitignore](./.gitignore) | Git exclusion rules |
| TommyTalker.spec | [./TommyTalker.spec](./TommyTalker.spec) | PyInstaller bundling configuration |
| build.sh | [./build.sh](./build.sh) | Build macOS .app bundle |
| run_dev.sh | [./run_dev.sh](./run_dev.sh) | Development runner script |
| security_scan.sh | [./scripts/security_scan.sh](./scripts/security_scan.sh) | 9-phase pre-commit security scanner (v4) |

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │
│  │  Menu Bar   │  │  Dashboard  │  │  Setup Guide / Onboarding      │  │
│  │ (menu_bar)  │  │ (dashboard) │  │  (setup_guide, onboarding)     │  │
│  │             │  │             │  │                                 │  │
│  │ Record btn  │  │ Settings    │  │  Permission checks, model DL   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┬──────────────────┘  │
│         │                │                         │                     │
│         └────────────────┴─────────────────────────┘                     │
│                                   │                                      │
│                                   ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                       APP CONTROLLER                               │   │
│  │  • Push-to-talk (Right Cmd via Quartz Event Tap)                  │   │
│  │  • App context detection → TextInputFormat selection              │   │
│  │  • Text formatting + paste/type at cursor                         │   │
│  │  • Audio feedback on start/stop                                   │   │
│  └───────────────────────────────┬───────────────────────────────────┘   │
└──────────────────────────────────┼───────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────────────┐
│                            ENGINE LAYER                                   │
│                                  ▼                                        │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │  AUDIO CAPTURE  │   │   TRANSCRIBER   │   │    APP CONTEXT      │    │
│  │  DualStream:    │──▶│   mlx-whisper   │   │  NSWorkspace +      │    │
│  │  • Live feed    │   │   Apple Silicon │   │  97 app profiles    │    │
│  │  • Archive WAV  │   │   optimized     │   │  (app_profiles.json)│    │
│  └─────────────────┘   └────────┬────────┘   └──────────┬──────────┘    │
│                                 │                        │               │
│                                 ▼                        ▼               │
│                        ┌─────────────────────────────────────────┐       │
│                        │           TEXT OUTPUT                     │       │
│                        │  Format by context → paste at cursor    │       │
│                        │  (prose, code, terminal, chat, email...)│       │
│                        └─────────────────────────────────────────┘       │
│                                                                          │
│  ┌─ Built but UI hidden (future modes) ────────────────────────────┐    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │  LLM CLIENT  │  │  DIARIZER    │  │    RAG STORE         │  │    │
│  │  │  Ollama +    │  │  pyannote    │  │    ChromaDB          │  │    │
│  │  │  OpenAI API  │  │  .audio      │  │    vector store      │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │ MODE MANAGER │  │  SESSION DB  │  │  HUD OVERLAY         │  │    │
│  │  │ 4 modes      │  │  SQLite      │  │  NSWindowSharingType │  │    │
│  │  │ (engine only)│  │  metadata    │  │  None (invisible)    │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────────────┐
│                            UTILS LAYER                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │  hardware_  │ │   config    │ │ permissions │ │   hotkeys   │       │
│  │  detect     │ │   JSON I/O  │ │  Mic/A11y   │ │   Quartz    │       │
│  │  Tier 1-3   │ │  + migrate  │ │  checks     │ │  Event Tap  │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   typing    │ │   logger    │ │   audio_    │ │   secure_   │       │
│  │  pyautogui  │ │  structured │ │   feedback  │ │   creds     │       │
│  │  clipboard  │ │  logging    │ │  Blow.aiff  │ │  Keychain   │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘

DATA FLOW (Push-to-Talk):
  Right Cmd Down → AudioFeedback → AudioCapture (start)
  Right Cmd Up   → AudioFeedback → AudioCapture (stop) → Transcriber
       → AppContext (detect app) → Format text → Paste at cursor
```

---

## Source Code Map

### Entry Points

| File | Purpose | Key Functions | Status |
|------|---------|---------------|--------|
| `src/tommy_talker/main.py` | Application entry point | `main()`, `launch_main_app()`, `_after_permissions()` | **Active** |
| `src/tommy_talker/app_controller.py` | Central orchestrator | `AppController`, push-to-talk, text output | **Active** |

### Engine Modules (`src/tommy_talker/engine/`)

| File | Purpose | Key Classes/Functions | Status |
|------|---------|----------------------|--------|
| `__init__.py` | Package exports | Re-exports engine components | **Active** |
| `audio_capture.py` | Dual-stream recording | `AudioCapture`, `DualStreamRecorder` | **Active** |
| `transcriber.py` | Speech-to-text | `Transcriber`, `TranscriptionResult` | **Active** |
| `modes.py` | Operating mode logic | `OperatingMode`, `ModeManager`, `*ModeController` | **Engine only** |
| `llm_client.py` | Ollama/Cloud LLM | `LLMClient`, `RewriteResult` | **Engine only** |
| `diarizer.py` | Speaker identification | `Diarizer`, `SpeakerSegment` | **Engine only** |
| `rag_store.py` | ChromaDB vector store | `RAGStore`, `SearchResult` | **Engine only** |
| `session_db.py` | SQLite session storage | `SessionDatabase`, `Session` | **Engine only** |

### GUI Modules (`src/tommy_talker/gui/`)

| File | Purpose | Key Classes | Status |
|------|---------|-------------|--------|
| `__init__.py` | Package exports | Re-exports GUI components | **Active** |
| `menu_bar.py` | System tray app | `MenuBarApp` (cursor mode only) | **Active** |
| `dashboard.py` | Settings/control panel | `DashboardWindow` (simplified) | **Active** |
| `setup_guide.py` | Permission wizard | `SetupGuideWindow` | **Active** |
| `onboarding.py` | First-run wizard | `OnboardingWizard`, `ModelDownloadThread` | **Active** |
| `hud.py` | Transparent overlay | `HUDOverlay` (NSWindowSharingTypeNone) | **Engine only** |
| `hotkey_selector.py` | Hotkey config UI | `HotkeySelector` | **Not wired** |

### Utility Modules (`src/tommy_talker/utils/`)

| File | Purpose | Key Exports | Status |
|------|---------|-------------|--------|
| `__init__.py` | Package exports | Re-exports utility components | **Active** |
| `app_context.py` | App detection + text format | `AppContext`, `TextInputFormat`, `get_app_context()` | **Active** |
| `audio_feedback.py` | Audio notifications | `AudioFeedback`, `get_audio_feedback()` | **Active** |
| `config.py` | Configuration management | `UserConfig`, `load_config()`, `save_config()` | **Active** |
| `hardware_detect.py` | RAM/chip tier detection | `HardwareProfile`, `detect_hardware()` | **Active** |
| `permissions.py` | macOS permission checks | `PermissionStatus`, `check_permissions()` | **Active** |
| `hotkeys.py` | Quartz Event Tap hotkeys | `HotkeyManager`, `is_modifier_only_hotkey()` | **Active** |
| `typing.py` | Text input automation | `type_at_cursor()`, `paste_text()` | **Active** |
| `logger.py` | Logging configuration | `setup_logger()`, `get_logger()` | **Active** |
| `secure_credentials.py` | Credential storage | `store_credential()`, `get_credential()` | **Active** |
| `history.py` | Transcription history | `TranscriptionHistory` | **Orphaned** |

### Data Files (`src/tommy_talker/data/`)

| File | Purpose | Status |
|------|---------|--------|
| `app_profiles.json` | 97 app profiles (bundle IDs, categories, text formats) | **Active** |

### Tests (`tests/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_app_context.py` | 18 tests | App detection, profile matching, category fallback |
| `test_modifier_hotkey.py` | 22 tests | Quartz Event Tap, modifier-only keys, debounce |
| `test_app_aware_llm.py` | 15 tests | Text formatting by app context |
| `test_audio_feedback.py` | 15 tests | Sound playback, pool rotation, enable/disable |
| `test_example.py` | 6 tests | Core infrastructure |
| `conftest.py` | — | Shared fixtures for macOS API mocking |

**Total: 76 tests passing**

### Scripts

| File | Purpose | Status |
|------|---------|--------|
| `build.sh` | Build macOS .app bundle via PyInstaller | **Active** |
| `run_dev.sh` | Run application in development mode | **Active** |
| `scripts/security_scan.sh` | 9-phase pre-commit security scanner (v4) | **Active** |

### Assets

| Type | Path | Purpose |
|------|------|---------|
| Hero Image | `assets/images/hero-banner.png` | README hero banner |

### Legacy Bundle (`SW/Contents/Resources/`)

Pre-built PyInstaller bundle from original Gemini build. Contains audio files (Start/Stop/noResult .m4a), AppIcon.icns, LLM prompt templates (.jinja), and compiled frameworks.

---

## Known Issues & Discrepancies

| Issue | Type | Severity | Description |
|-------|------|----------|-------------|
| `utils/history.py` | Orphaned Code | **LOW** | Module defined but never imported. References non-existent `get_data_path()`. |
| pyobjc Python 3.13 | Compatibility | **LOW** | Circular import with objc module. Mitigated by using Quartz Event Tap instead of Carbon. |
| torchcodec FFmpeg | Compatibility | **LOW** | FFmpeg 8.x installed but torchcodec supports v4-7. Affects diarization (currently hidden). |
| No CI/CD | Gap | **LOW** | No GitHub Actions workflows configured yet. |

---

## Development Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Foundation | **Complete** |
| 2 | Core Features | **Complete** |
| 3 | GUI & UX | **Complete** |
| 4 | AI Integration | **Complete** |
| 5 | Bundling | **Complete** (code signing deferred) |
| 6 | Push-to-Talk Intelligence | **Complete** |
| 7 | UI Simplification | **Complete** |
| 8 | Portfolio Release | **In Progress** |

**Overall Maturity**: Active development — Push-to-talk operational with 76 tests.

---

## Quick Reference

### Running the Application

```bash
# Development mode
source .venv/bin/activate
PYTHONPATH=src python -m tommy_talker.main

# Or after pip install -e .
tommytalker

# Build macOS .app
./build.sh
```

### Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src/tommy_talker --cov-report=term-missing
mutmut run  # Mutation testing
```

### Hotkey

| Action | Key |
|--------|-----|
| Push-to-Talk | **Right Command** (hold to record, release to paste) |

### Key Entry Points

| Entry Point | Transport/Protocol |
|-------------|-------------------|
| `src/tommy_talker/main.py:main()` | Application launch |
| `src/tommy_talker/gui/menu_bar.py` | System tray (PyQt6) |
| `src/tommy_talker/gui/dashboard.py` | Settings UI (PyQt6) |
| Quartz Event Tap | Global hotkey events |

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

| Component | Technology | Detail |
|-----------|------------|--------|
| Language | Python | 3.12+ |
| GUI Framework | PyQt6 | 6.6.0+ |
| Speech-to-Text | mlx-whisper | Apple Silicon Metal-accelerated |
| LLM (Local) | Ollama | phi-3, llama-3-8b |
| LLM (Cloud) | httpx | OpenAI-compatible APIs |
| Hotkeys | Quartz Event Tap | Modifier-only key support |
| Diarization | pyannote.audio | 3.1+ (HF token required) |
| Vector Store | ChromaDB | 0.4.0+ |
| Database | SQLite | Standard library |
| Audio I/O | sounddevice, soundfile | Recording + WAV output |
| Hardware Detection | psutil | RAM/chip tier detection |
| Text Input | pyautogui | Clipboard + keyboard simulation |
| macOS Integration | pyobjc | Cocoa + Quartz frameworks |
| Credentials | macOS Keychain | Via secure_credentials.py |
| Build | PyInstaller | TommyTalker.spec |
| Testing | pytest | 76 tests + mutmut mutation testing |
| Formatting | black | 100 char line length |
| Linting | ruff | E, F, I, N, W rules |
| Security | security_scan.sh | 9-phase scanner (v4) |

---

## Runtime & Generated Files

Files that exist at runtime but are gitignored:

| Type | Path/Pattern | Purpose |
|------|--------------|---------|
| Virtual env | `.venv/`, `venv/` | Python dependencies |
| Python cache | `__pycache__/`, `*.pyc` | Compiled bytecode |
| Build artifacts | `build/`, `dist/` | PyInstaller output |
| Legacy bundle | `SW/` | Pre-compiled frameworks, audio, icons, templates |
| Logs | `*.log` | Application logs |
| Runtime data | `data/` | Local data directory |
| Test cache | `.pytest_cache/`, `.coverage` | Test artifacts |
| Linter cache | `.ruff_cache/` | Ruff linter cache |
| ML models | `*.gguf`, `*.bin`, `*.safetensors` | Large model files |
| Secrets | `.env`, `*.pem`, `*.key` | Credentials |
| User data | `~/Documents/TommyTalker/` | Config, sessions, recordings, embeddings |
| Agent sessions | `sessions/` | Agent coordination files |

---

## _HQ Integration

**Status**: Registered in `~/Tech_Projects/_HQ/SYNC_STATUS.yaml` since 2026-02-04.

**Visibility**: PUBLIC — private _HQ assets are skipped during sync.

**Synced assets**: All standards (TDD v2, Security, Conventions, Commit Format, Project Structure), all public guides, security scanner v4, evaluation references, agent integration templates.

**Available commands**: `/gogogo` (session startup + sync), `/wrapup` (session close), `/start-here` (update this file), `/commit` (security scan + commit)

**Relevant guides**:
- `~/Tech_Projects/_HQ/guides/universal/APPLE_SILICON.md`
- `~/Tech_Projects/_HQ/guides/universal/LOGGING.md`
- `~/Tech_Projects/_HQ/guides/universal/TESTING.md`
- `~/Tech_Projects/_HQ/guides/universal/ERROR_HANDLING.md`
- `~/Tech_Projects/_HQ/guides/universal/ENV_CONFIGURATION.md`

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Python Source Files | 30 |
| Test Files | 5 + conftest.py |
| Tests Passing | 76 |
| App Profiles | 97 |
| Documentation Files | 12+ |
| Runtime Dependencies | ~11 (pyproject.toml) |
| Dev Dependencies | 7 (pyproject.toml) |
| Orphaned Modules | 1 (`utils/history.py`) |

---

*Last updated: 2026-02-11*
