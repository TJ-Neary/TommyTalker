# TommyTalker - Issues Backlog

## Open Issues

### 🔴 HIGH - pyobjc Python 3.13 Incompatibility

**Status:** Open  
**Impact:** HUD overlay visible to screen sharing (Zoom/Teams)  
**Affected Feature:** HUD Mode privacy

**Details:**
```
ImportError: cannot import name '_objc' from partially initialized module 'objc' 
(most likely due to a circular import)
```

**Root Cause:** pyobjc has compatibility issues with Python 3.13

**Possible Fixes:**
1. Downgrade to Python 3.12 (recommended for production)
2. Wait for pyobjc update with 3.13 support
3. Build pyobjc from source (complex)

---

### 🟡 MEDIUM - torchcodec FFmpeg Version Mismatch

**Status:** Open  
**Impact:** Speaker diarization may not work optimally  
**Affected Feature:** Scribe Mode diarization

**Details:**
```
torchcodec is not installed correctly so built-in audio decoding will fail.
FFmpeg version 7: Library not loaded: @rpath/libavutil.59.dylib
```

**Root Cause:** 
- Installed FFmpeg: **8.0.1** (via Homebrew)
- torchcodec supports: **FFmpeg 4, 5, 6, 7** only

**Possible Fixes:**
1. Install FFmpeg 7 alongside FFmpeg 8:
   ```bash
   brew tap homebrew-ffmpeg/ffmpeg
   brew install homebrew-ffmpeg/ffmpeg/ffmpeg@7
   ```
2. Use `brew install ffmpeg@7` and update PATH
3. Wait for torchcodec to support FFmpeg 8

---

## Resolved Issues

| Date | Issue | Resolution |
|------|-------|------------|
| 2026-01-24 | Default hotkeys conflict with macOS | Changed to Ctrl+Shift+... |
| 2026-01-24 | Mic test crash in onboarding | Replaced with blocking test |
| 2026-01-24 | Settings hotkey layout unreadable | Fixed widths + grid layout |
| 2026-01-24 | HUD can't be dragged | Added mouse event handlers |
| 2026-01-24 | HUD memory crash (982GB) | Fixed audio buffer shape |
| 2026-01-24 | SF Pro font warning | Changed to Helvetica Neue |

---

## Notes

- **Python Version:** 3.13.1
- **macOS Version:** (check with `sw_vers`)
- **FFmpeg Version:** 8.0.1_1
