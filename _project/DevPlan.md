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
**Description**: Privacy-first voice intelligence suite for macOS with local-first STT, LLM rewriting, speaker diarization, and RAG-based meeting transcription.
**Python**: 3.12+
**Created**: 2026-01

### Goals

1. Provide privacy-first voice transcription that runs entirely on-device
2. Support multiple operating modes for different use cases (dictation, editing, meetings, interviews)
3. Integrate with local LLMs via Ollama for text enhancement
4. Enable speaker diarization for meeting transcripts

### Non-Goals

- Cloud-first transcription (only optional fallback)
- Windows/Linux support (macOS only)
- Real-time translation

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        TommyTalker                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   Menu Bar   │────▶│  Dashboard   │────▶│     HUD      │   │
│  │   (rumps)    │     │   (PyQt6)    │     │   (PyQt6)    │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│          │                   │                                  │
│          └───────────┬───────┘                                  │
│                      ▼                                          │
│           ┌──────────────────┐                                  │
│           │  App Controller  │◀──── Hotkey Events               │
│           └──────────────────┘                                  │
│                      │                                          │
│           ┌──────────┴──────────┐                               │
│           ▼                     ▼                               │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │ Mode Manager │────▶│  Audio Pipe  │                         │
│  │  (4 modes)   │     │ (sounddevice)│                         │
│  └──────────────┘     └──────────────┘                         │
│           │                     │                               │
│           ▼                     ▼                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │  Transcriber │     │  Diarizer    │     │  RAG Store   │   │
│  │ (mlx-whisper)│     │ (pyannote)   │     │  (ChromaDB)  │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────┐                                               │
│  │  LLM Client  │────▶ Ollama (local) / OpenAI-compat (cloud)  │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Status |
|-----------|---------|--------|
| engine/audio_capture | Dual-stream audio recording | Complete |
| engine/transcriber | mlx-whisper STT | Complete |
| engine/llm_client | Ollama/OpenAI-compat LLM | Complete |
| engine/diarizer | pyannote speaker diarization | Complete |
| engine/rag_store | ChromaDB meeting storage | Complete |
| engine/modes | 4 operating mode controllers | Complete |
| gui/menu_bar | System tray interface | Complete |
| gui/dashboard | Settings and controls | Complete |
| gui/hud | Screen-share invisible overlay | Complete |
| gui/setup_guide | Permission wizard | Complete |
| gui/onboarding | First-run wizard | Complete |
| utils/hardware_detect | Apple Silicon tier detection | Complete |
| utils/hotkeys | Global hotkey manager | Complete |

### Data Flow

```
Microphone → AudioCapture → DualStreamRecorder
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            Live Callback                    Archive to Disk
            (streaming)                       (WAV file)
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                              Transcriber
                            (mlx-whisper)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Cursor Mode     Editor Mode     Meeting Mode
              (type text)   (LLM rewrite)   (diarize+RAG)
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
- [x] Global hotkey system
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

### Phase 5: Bundling (Current)
- [x] PyInstaller spec file
- [x] macOS app bundle
- [ ] Code signing
- [ ] Notarization

---

## Task Tracker

### Critical Priority

| Task | Status | Notes |
|------|--------|-------|
| Restructure to src/ layout | Done | _HQ template compliance |
| Fix Python 3.13 pyobjc compatibility | Blocked | Waiting for pyobjc update |

### High Priority

| Task | Status | Notes |
|------|--------|-------|
| Add comprehensive test suite | Not Started | conftest.py created |
| Fix orphaned utils/history.py | Not Started | References non-existent get_data_path() |

### Medium Priority

| Task | Status | Notes |
|------|--------|-------|
| Notarization workflow | Not Started | For App Store / public distribution |
| Auto-update mechanism | Not Started | Sparkle or custom |

### Low Priority

| Task | Status | Notes |
|------|--------|-------|
| Windows port | Not Planned | macOS-only design |

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

### TD-003: NSWindowSharingTypeNone for HUD

- **Decision**: Use pyobjc to set NSWindowSharingTypeNone on HUD overlay
- **Rationale**: Makes overlay invisible to screen sharing (Zoom, Teams) for interview coaching
- **Alternatives considered**: Separate window process, overlay-only app
- **Date**: 2026-01

---

## Quality Standards

- **Testing**: pytest with coverage (`--cov=src/tommy_talker --cov-report=term-missing`)
- **Formatting**: black (100 char line length)
- **Linting**: ruff
- **Type checking**: mypy
- **Security**: bandit + security_scan.sh pre-commit hook
- **Commit format**: `<type>: <description>` (feat/fix/docs/refactor/test/chore/perf)

---

## Resolved Items

| Item | Resolution | Date |
|------|-----------|------|
| Project structure | Restructured to src/tommy_talker layout | 2026-02-04 |
| Import style | Changed to absolute imports (tommy_talker.module) | 2026-02-04 |

---

*Last updated: 2026-02-04*
