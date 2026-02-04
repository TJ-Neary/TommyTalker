# TommyTalker — Findings & Research

> **Purpose**: Document research, discoveries, and constraints encountered during development.

---

## Discovery Phase Findings

### User Requirements (2026-01-23)

**North Star**: Local-first macOS voice intelligence app with:
- Dual-interface (Menu Bar + Dashboard)
- Hardware-aware AI scaling
- 4 operating modes

**Key Constraints Identified**:
1. Must be modular (`/gui`, `/engine`, `/utils`) — NOT a single script
2. Privacy-first: All processing local
3. HUD must be invisible to screen sharing (Zoom/Teams)
4. Session hygiene required (wipe ChromaDB between sessions)

---

## Technical Research

### pyobjc Window Hiding
**Finding**: To hide a window from screen sharing, must use:
```python
from AppKit import NSWindowSharingTypeNone
window.sharingType = NSWindowSharingTypeNone
```
**Source**: macOS AppKit documentation  
**Status**: ✅ Confirmed viable

### mlx_whisper vs whisper.cpp
**Finding**: `mlx_whisper` is Apple Silicon optimized via MLX framework
- Faster than whisper.cpp on M-series chips
- Native Metal acceleration
**Status**: ✅ Selected for project

### Hardware Tier Logic
**Finding**: Python `psutil` can query RAM:
```python
import psutil
ram_gb = psutil.virtual_memory().total / (1024**3)
```
**Status**: ✅ Confirmed approach

---

## Constraints Log

| ID | Constraint | Source | Impact |
|----|------------|--------|--------|
| C1 | No cloud APIs | User requirement | All AI must run locally |
| C2 | PyInstaller bundling | User requirement | Must structure for single `.app` |
| C3 | macOS only | User requirement | Can use pyobjc freely |
| C4 | Python 3.12+ | User requirement | Modern syntax available |

---

## Open Questions

| ID | Question | Status | Resolution |
|----|----------|--------|------------|
| Q1 | Which Ollama models ship by default? | 🟡 Open | Need to verify during Phase 3 |
| Q2 | pyannote.audio license for commercial use? | 🟡 Open | May need user to accept terms |
| Q3 | Global hotkey conflicts with system? | 🟡 Open | Test during Phase 4 |

---

## Resources

- [mlx_whisper GitHub](https://github.com/ml-explore/mlx-examples)
- [pyobjc Documentation](https://pyobjc.readthedocs.io/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
