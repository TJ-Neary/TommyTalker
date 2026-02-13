# TommyTalker — Development Plan

> Single source of truth for project planning, architecture decisions, and task tracking.
> Update this file as the project evolves. Archive completed sections periodically.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Development Phases](#development-phases)
4. [Task Tracker](#task-tracker)
5. [Technical Decisions](#technical-decisions)
6. [Quality Standards](#quality-standards)
7. [Resolved Items](#resolved-items)

---

## Project Overview

**Project**: TommyTalker
**Description**: Privacy-first voice-to-text for macOS with push-to-talk dictation, app-aware text formatting, and local-only processing via mlx-whisper on Apple Silicon.
**Python**: 3.12+
**Created**: 2026-01

### Goals

1. Provide privacy-first voice dictation that runs entirely on-device
2. Push-to-talk with Right Command key — hold to record, release to paste
3. Automatically format transcribed text based on the frontmost application
4. Support multiple operating modes for future use cases (editing, meetings, coaching)

### Non-Goals

- Cloud-first transcription (only optional fallback)
- Windows/Linux support (macOS only)
- Real-time translation
- Always-listening mode (push-to-talk only for now)

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Menu Bar   │────▶│  Dashboard   │     │  Onboarding  │    │
│  │   (PyQt6)    │     │  (Settings)  │     │   Wizard     │    │
│  └──────┬───────┘     └──────┬───────┘     └──────────────┘    │
│         │                    │                                   │
│         └────────────┬───────┘                                   │
│                      ▼                                           │
│           ┌──────────────────┐                                   │
│           │  App Controller  │◀──── Right Cmd (Quartz Event Tap) │
│           │  Push-to-Talk    │                                   │
│           └──────────────────┘                                   │
│                      │                                           │
│           ┌──────────┴──────────┐                                │
│           ▼                     ▼                                │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ App Context  │     │  Audio Pipe  │                          │
│  │ 97 profiles  │     │ (sounddevice)│                          │
│  │ TextFormat   │     │              │                          │
│  └──────────────┘     └──────────────┘                          │
│                              │                                   │
│                              ▼                                   │
│                     ┌──────────────┐     ┌──────────────┐       │
│                     │  Transcriber │────▶│  Text Output │       │
│                     │ (mlx-whisper)│     │ format+paste │       │
│                     └──────────────┘     └──────────────┘       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Status |
|-----------|---------|--------|
| app_controller.py | Push-to-talk orchestration, hotkey handling, text output | **Active** |
| utils/app_context.py | Frontmost app detection, 97 profiles, TextInputFormat | **Active** |
| utils/hotkeys.py | Quartz Event Tap, modifier-only key support | **Active** |
| utils/audio_feedback.py | System sound playback (Blow.aiff) | **Active** |
| utils/typing.py | Cursor text insertion (pyautogui + clipboard) | **Active** |
| engine/audio_capture.py | Dual-stream audio recording | **Active** |
| engine/transcriber.py | mlx-whisper STT | **Active** |
| engine/modes.py | Cursor mode controller + ModeManager | **Active** |
| gui/menu_bar.py | System tray with TT icon (red when recording) | **Active** |
| gui/dashboard.py | Settings window (models + preferences) | **Active** |
| gui/setup_guide.py | Permission wizard | **Active** |
| gui/onboarding.py | First-run wizard | **Active** |
| utils/path_guard.py | Filesystem boundary enforcement | **Active** |
| utils/code_validator.py | AST-based code validation | **Active** |
| utils/prompt_injection.py | Prompt injection detection | **Active** |

### Data Flow (Push-to-Talk)

```
Right Cmd Down
    │
    ▼
Audio Feedback (Blow.aiff) → Start Recording (sounddevice)
    │
Right Cmd Up
    │
    ▼
Audio Feedback (Blow.aiff) → Stop Recording → WAV buffer
    │
    ▼
Transcriber (mlx-whisper) → raw text
    │
    ▼
App Context Detection (NSWorkspace → app_profiles.json → TextInputFormat)
    │
    ▼
Text Formatting (capitalize, strip fillers, etc. based on format)
    │
    ▼
Paste at Cursor (clipboard + Cmd+V) or Type (character-by-character)
```

---

## Development Phases

### Phase 1: Foundation ✓
- [x] Project scaffolding and configuration
- [x] Core audio capture pipeline
- [x] Basic transcription with mlx-whisper
- [x] Hardware tier detection

### Phase 2: Core Features ✓
- [x] Four operating modes (Cursor, Editor, Meeting, HUD)
- [x] Mode manager orchestration
- [x] Global hotkey system (Carbon)
- [x] Menu bar application

### Phase 3: GUI & UX ✓
- [x] Dashboard window with settings
- [x] Permission wizard
- [x] Onboarding wizard
- [x] HUD overlay with screen-share invisibility

### Phase 4: AI Integration ✓
- [x] Ollama LLM integration
- [x] Cloud mode fallback (OpenAI-compat)
- [x] Speaker diarization (pyannote)
- [x] RAG storage (ChromaDB)

### Phase 5: Bundling ✓
- [x] PyInstaller spec file
- [x] macOS app bundle (build.sh)
- [ ] Code signing (deferred)
- [ ] Notarization (deferred)

### Phase 6: Push-to-Talk Intelligence ✓ (2026-02-11)
- [x] Right Command push-to-talk via Quartz Event Tap
- [x] Modifier-only hotkey support (no Carbon dependency)
- [x] App context detection (NSWorkspace + 97 app profiles)
- [x] Context-aware text formatting (prose, code, terminal, chat, email, search)
- [x] Terminal command filler word stripping
- [x] Audio feedback system (macOS system sounds, round-robin variation)
- [x] Comprehensive test suite (76 tests across 5 files)
- [x] Fixed chromadb/pydantic crash on Python 3.14
- [x] Fixed bare imports (utils → tommy_talker.utils)
- [x] Config migration for upgrading old hotkey defaults
- [x] SIGINT handler for Ctrl+C exit from Qt event loop

### Phase 7: UI Simplification ✓ (2026-02-11)
- [x] Simplified to push-to-talk only (cursor mode)
- [x] Removed mode switching UI from menu bar
- [x] Removed editor/meeting/hud from dashboard modes tab
- [x] Removed hotkey configuration selectors from dashboard
- [x] Removed HUD wiring from main.py
- [x] Kept all engine code intact for future re-enablement
- [x] Static "Push-to-Talk: Right Command" label in settings

### Phase 8: Portfolio Release ✓ (2026-02-11)
- [x] Hero banner image (assets/images/hero-banner.png)
- [x] README.md rewrite with app-aware formatting showcase
- [x] MIT LICENSE
- [x] CONTRIBUTING.md
- [x] All documentation updated
- [ ] Push to GitHub public repository

### Phase 9: Production Readiness (2026-02-12)
- [x] CI/CD pipeline (GitHub Actions: lint, test, security scan)
- [x] Custom TT menu bar icon (white square, dark TT; red TT when recording)
- [x] App icon generation script (scripts/generate_icon.py → .icns)
- [x] LaunchAgent for start-on-login (com.tommytalker.app.plist)
- [x] Build script install/uninstall support (build.sh --install/--uninstall)
- [x] Cleanup: removed orphaned utils/history.py
- [x] Cleanup: removed 5 legacy Gemini-era docs (gemini.md, task_plan.md, progress.md, findings.md, ISSUES_BACKLOG.md)
- [x] Synced 3 security utilities from _HQ (path_guard, code_validator, prompt_injection)
- [ ] Code signing (deferred — requires Apple Developer account)
- [ ] Notarization (deferred — requires Apple Developer account)

### Phase 10: Feature Stripping ✓ (2026-02-12)
- [x] Deleted engine modules: llm_client.py, diarizer.py, rag_store.py, session_db.py
- [x] Deleted GUI modules: hud.py, hotkey_selector.py
- [x] Deleted test file: test_app_aware_llm.py (15 LLM tests)
- [x] Simplified modes.py to cursor-only (removed 3 mode controllers)
- [x] Removed Carbon hotkey code — Quartz Event Tap only
- [x] Simplified hardware_detect.py (removed LLM/diarization recommendations)
- [x] Simplified config.py (removed cloud mode, HuggingFace, RAG, LLM fields)
- [x] Cleaned dashboard.py (removed Ollama UI, session hygiene, cloud mode)
- [x] Cleaned onboarding.py (removed LLM download, hotkey config pages)
- [x] Removed ollama, pyannote.audio, chromadb from dependencies
- [x] Retina 2x menu bar icon rendering
- [x] All 61 tests passing, zero startup warnings
- [x] Updated CLAUDE.md, DevPlan.md, TommyTalker.spec

---

## Task Tracker

### Active

| Task | Status | Notes |
|------|--------|-------|
| Push to GitHub | Ready | All docs updated, portfolio release |
| Build and test .app | Ready | Run `./build.sh --install` to package and install |
| Code signing | Deferred | For App Store / public distribution |
| Notarization | Deferred | Requires Apple Developer account |

### Completed (Recent)

| Task | Status | Date |
|------|--------|------|
| Feature stripping (LLM, diarizer, RAG, HUD) | Done | 2026-02-12 |
| CI/CD GitHub Actions workflow | Done | 2026-02-12 |
| Custom TT menu bar icon | Done | 2026-02-12 |
| .app packaging with install/uninstall | Done | 2026-02-12 |
| Launch on login (LaunchAgent) | Done | 2026-02-12 |
| Remove orphaned history.py | Done | 2026-02-12 |
| Remove legacy Gemini-era docs | Done | 2026-02-12 |
| Sync HQ security utilities | Done | 2026-02-12 |
| Push-to-talk (Right Cmd) | Done | 2026-02-11 |
| App context detection (97 profiles) | Done | 2026-02-11 |
| Audio feedback system | Done | 2026-02-11 |
| 76-test suite | Done | 2026-02-11 |
| UI simplification | Done | 2026-02-11 |
| Fix startup crashes (chromadb, imports) | Done | 2026-02-11 |
| Config migration (old defaults) | Done | 2026-02-11 |
| Restructure to src/ layout | Done | 2026-02-04 |

### Future (Not Building Yet)

| Task | Trigger | Notes |
|------|---------|-------|
| Editor mode (LLM rewrite) | User demand | Would need to rebuild llm_client from git history |
| Meeting mode (diarization) | User demand | Would need to rebuild diarizer + rag_store |
| HUD mode (screen-share invisible) | User demand | Would need to rebuild hud.py |
| Windows port | Not planned | macOS-only design |

---

## Technical Decisions

### TD-001: mlx-whisper over Whisper.cpp
- **Decision**: Use mlx-whisper for transcription
- **Rationale**: Native Apple Silicon optimization via MLX framework, better performance on M-series chips
- **Alternatives considered**: Whisper.cpp (C++), faster-whisper (ctranslate2)
- **Date**: 2026-01

### TD-002: Hardware Tier System
- **Decision**: Three-tier system based on RAM (Tier 1: <16GB, Tier 2: 16-32GB, Tier 3: >32GB)
- **Rationale**: Automatically select appropriate model sizes for user's hardware
- **Alternatives considered**: Manual model selection, GPU VRAM-based tiers
- **Date**: 2026-01

### TD-004: Quartz Event Tap over Carbon
- **Decision**: Use Quartz Event Tap for hotkey handling instead of Carbon
- **Rationale**: Carbon is deprecated and removed in Python 3.14. Quartz Event Tap supports modifier-only keys (Right Command) which Carbon cannot detect as standalone hotkeys.
- **Alternatives considered**: Carbon (deprecated), pynput (no modifier-only support), CGEvent direct
- **Date**: 2026-02-11

### TD-005: App Profile System for Context Detection
- **Decision**: JSON-based app profile database (97 profiles) with bundle ID matching, regex patterns, and category-based fallback
- **Rationale**: Different apps need different text formatting. A data-driven approach allows easy additions without code changes. Categories provide fallback for unrecognized apps.
- **Alternatives considered**: Hardcoded app list, per-app plugins, no context detection
- **Date**: 2026-02-11

### TD-006: Strip Unused Features
- **Decision**: Fully remove Editor, Meeting, and HUD modes including engine code, dependencies, and tests
- **Rationale**: Only Cursor mode with push-to-talk is actively used. Removing dead code reduces attack surface, dependency count, startup warnings, and maintenance burden. Git history preserves everything for potential future rebuild.
- **Alternatives considered**: Keep engine code hidden but intact (previous approach), keep all modes visible
- **Date**: 2026-02-12 (updated from 2026-02-11 hide-only approach)

### TD-007: Audio Feedback via macOS System Sounds
- **Decision**: Use `/System/Library/Sounds/Blow.aiff` for both start and stop feedback, played via `afplay` subprocess
- **Rationale**: System sounds are always available, `afplay` is non-blocking, no additional dependencies needed. Blow.aiff provides distinct but unobtrusive feedback.
- **Alternatives considered**: Custom sound files (SW/ bundle), PyQt6 multimedia, no audio feedback
- **Date**: 2026-02-11

### TD-008: Custom TT Menu Bar Icon
- **Decision**: White filled square with "TT" letters, red TT when recording, dark TT when idle
- **Rationale**: Distinctive brand identity in menu bar. White square provides consistent background across light/dark mode. Red color signals recording state clearly.
- **Alternatives considered**: Microphone icon (generic), waveform icon, template image (loses color)
- **Date**: 2026-02-12

### TD-009: LaunchAgent for Start on Login
- **Decision**: Use macOS LaunchAgent plist (`~/Library/LaunchAgents/com.tommytalker.app.plist`) with RunAtLoad
- **Rationale**: Standard macOS mechanism for user-level login items. No elevated privileges needed. Easy to install/uninstall via build script.
- **Alternatives considered**: Login Items API (requires entitlements), SMAppService (Swift-only), manual Dock/System Preferences
- **Date**: 2026-02-12

---

## Quality Standards

- **Testing**: pytest with 61 tests, coverage reporting, mutation testing (mutmut)
- **Formatting**: black (100 char line length)
- **Linting**: ruff (E, F, I, N, W rules)
- **Type checking**: mypy
- **Security**: 9-phase pre-commit security scanner (v4)
- **Commit format**: `<type>: <description>` (feat/fix/docs/refactor/test/chore/perf)
- **TDD**: Red-Green-Refactor cycle per _HQ TDD standard v2

---

## Resolved Items

| Item | Resolution | Date |
|------|-----------|------|
| Project structure | Restructured to src/tommy_talker layout | 2026-02-04 |
| Import style | Changed to absolute imports (tommy_talker.module) | 2026-02-04 |
| chromadb Python 3.14 crash | Broadened except ImportError to except Exception | 2026-02-11 |
| Bare import in dashboard.py | Fixed to tommy_talker.utils.config | 2026-02-11 |
| Config override (Cmd+. → RightCmd) | Added config migration in load_config() | 2026-02-11 |
| Ctrl+C not exiting Qt | Added signal.signal(SIGINT) handler | 2026-02-11 |
| pyobjc Python 3.13 issue | Replaced Carbon with Quartz Event Tap | 2026-02-11 |
| Orphaned utils/history.py | Deleted — never imported, broken get_data_path dependency | 2026-02-12 |
| Legacy Gemini-era docs | Deleted 5 files — git history preserved, DevPlan is authoritative | 2026-02-12 |
| Private HQ assets not syncing | Reclassified path_guard, code_validator, prompt_injection as public | 2026-02-12 |
| Unused engine features | Fully removed LLM, diarizer, RAG, HUD, hotkey_selector + 6 deps | 2026-02-12 |
| Carbon hotkey warning | Removed Carbon entirely, Quartz-only hotkey system | 2026-02-12 |
| Startup warnings (chromadb, pyobjc, etc.) | All eliminated by removing unused dependencies | 2026-02-12 |

---

*Last updated: 2026-02-12*
