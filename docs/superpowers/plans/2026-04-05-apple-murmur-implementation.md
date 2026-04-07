# apple-murmur Implementation Plan

> **Status: COMPLETE** — All original tasks implemented and pushed. See post-plan additions below.

**Goal:** Build the Apple Silicon-native variant of murmur — identical UX, but using mlx-whisper on the Neural Engine for near-instant transcription (~150ms vs ~500ms).

**Architecture:** Same three-layer design as murmur. Six of seven source files are copied verbatim from murmur. Only `engine.py` differs — it uses `mlx-whisper` instead of PyTorch. Install dir is `~/.apple-murmur/` to avoid collision with murmur.

**Tech Stack:** Python 3.9+, mlx-whisper, pynput, sounddevice, pyperclip, pyautogui, toml, argparse

---

## Original Tasks (all complete)

- [x] **Task 1:** Copy shared files from murmur, update install paths to `~/.apple-murmur/`
- [x] **Task 2:** MLX engine module (`engine.py` + `test_engine.py`)
- [x] **Task 3:** Install script (`install.sh`) + README + push to GitHub

---

## Post-Plan Additions (2026-04-07)

The following were added after the original plan was completed:

### Hotkey fix
- Default hotkey changed from `fn` → `ctrl_l` (Left Control) on macOS. `fn` opens the emoji picker and cannot be captured system-wide by pynput.

### Silence auto-stop
- `audio.py` — real-time WebRTC VAD (webrtcvad, 30ms frames, aggressiveness=2). Recording stops automatically after ~1s of silence; second double-tap is still supported but optional.

### Audio preprocessing pipeline (`murmur/preprocessor.py`)
Applied before every Whisper inference call:
1. Noise reduction — `noisereduce` non-stationary, 75% reduction
2. Volume normalisation — RMS target 0.08, clips ±1.0
3. VAD silence stripping — remove non-speech frames using WebRTC VAD

### IT domain vocabulary correction
- `murmur/vocabulary.py` — rapidfuzz fuzzy matching (threshold 88) against an IT managed services vocabulary
- `murmur/kenlm_rescorer.py` — optional KenLM language model for log-prob candidate validation
- `scripts/build_domain_corpus.py` — 120-sentence IT corpus for KenLM training
- `murmur/normalizer.py` — extended with spoken punctuation rules; calls `vocabulary.correct()` on every pass

### Whisper tuning (`murmur/engine.py`)
- `temperature=0.0`, `beam_size=3`, `condition_on_previous_text=True`
- IT-biased `initial_prompt` seeding Whisper's vocabulary toward managed services terminology

### Bug fixes
- `engine.py` — added `device=None` param (was causing `TypeError` on daemon startup)
- `vocabulary.py` — LM validation now covers single-candidate cases (was bypassed by `len > 1` guard)
- `normalizer.py` — fixed `'\\'` backslash replacement (invalid `re.sub` template on Python 3.9)
- `normalizer.py` — removed colloquialism rules (`gonna`/`wanna`/`hafta`) that corrupted IT professional dictation
- `audio.py` — deduplicated `_VAD_AGGRESSIVENESS`; now imported from `preprocessor.py`

### Test suite expansion (24 → 48 tests)
- `tests/test_preprocessor.py` — normalize_volume, VAD stripping, noisereduce fallback, full pipeline
- `tests/test_vocabulary.py` — threshold, LM single/multi candidate, vocab skip logic
- `tests/test_kenlm_rescorer.py` — lazy load, idempotency, absent model, exception paths
- `tests/conftest.py` — extended mocks for webrtcvad, noisereduce, rapidfuzz, kenlm

### Performance monitor (`scripts/perf_monitor.py`)
Samples CPU, memory, and optionally ANE utilisation (via `powermetrics --ane`). Auto-detects daemon PID. Phase labelling via `/tmp/murmur_monitor_phase`. JSON summary on exit.
