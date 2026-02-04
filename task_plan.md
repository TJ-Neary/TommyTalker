# TommyTalker — Task Plan

> **Phase**: Protocol 0 (Initialization)  
> **Status**: 🟡 In Progress

---

## Phase 0: Initialization ✅
- [x] Answer Discovery Questions
- [x] Create `gemini.md` (Project Constitution)
- [x] Create `task_plan.md` (this file)
- [x] Create `findings.md`
- [x] Create `progress.md`
- [ ] **GATE**: User approves Blueprint before Phase 1

---

## Phase 1: B — Blueprint (Vision & Logic)
- [ ] Finalize data schemas
- [ ] Lock behavioral rules
- [ ] User approval checkpoint

---

## Phase 2: L — Link (File & Folder Structure)
- [ ] Create `/gui` module skeleton
- [ ] Create `/engine` module skeleton
- [ ] Create `/utils` module skeleton
- [ ] Create `main.py` entry point
- [ ] Create `requirements.txt`
- [ ] Create `pyproject.toml`

---

## Phase 3: A — Architect (Core Logic)

### Hardware Detection
- [ ] `utils/hardware_detect.py` — RAM query, tier logic
- [ ] Model recommendation engine

### Audio Pipeline
- [ ] `engine/audio_capture.py` — Dual-stream architecture
- [ ] Stream A: Live feed to mlx_whisper
- [ ] Stream B: Archive to disk

### Permission System
- [ ] `utils/permissions.py` — Mic/Accessibility checks
- [ ] `gui/setup_guide.py` — Permission wizard UI

### GUI Foundation
- [ ] `gui/menu_bar.py` — System tray integration
- [ ] `gui/dashboard.py` — Main control panel

---

## Phase 4: S — Stylize (Modes & Features)

### Mode 1: Cursor
- [ ] Listen → Transcribe → Type at cursor
- [ ] Vocabulary injection into `initial_prompt`
- [ ] pyautogui integration

### Mode 2: Editor
- [ ] Record → Transcribe → LLM Rewrite
- [ ] `style_guide.txt` detection and application
- [ ] Clipboard paste

### Mode 3: Scribe
- [ ] Meeting assistant with timestamps
- [ ] pyannote.audio speaker diarization
- [ ] Speaker A/B labeling

### Mode 4: HUD
- [ ] Transparent overlay window
- [ ] `NSWindowSharingTypeNone` for screen-share invisibility
- [ ] Interview coaching UI

### Data Management
- [ ] `engine/rag_store.py` — ChromaDB operations
- [ ] Session hygiene ("Clear Session" wipe)
- [ ] SQLite session metadata

---

## Phase 5: T — Trigger (Bundling & Testing)
- [ ] PyInstaller spec file
- [ ] Bundle to `.app`
- [ ] Integration tests
- [ ] Screen-share invisibility verification
- [ ] Final delivery

---

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| Constitution Approved | Phase 0 | 🟡 Pending |
| Skeleton Built | Phase 2 | ⬜ Not Started |
| Core Logic Working | Phase 3 | ⬜ Not Started |
| All Modes Functional | Phase 4 | ⬜ Not Started |
| `.app` Delivered | Phase 5 | ⬜ Not Started |
