# apple-murmur — Architecture

System-wide voice-to-text for Apple Silicon Macs. Double-tap a hotkey, speak, text appears at cursor — any app, any text field, no cloud, no API keys.

**14 source modules** | **12 test files** | **~1,025 lines of source** | **~1,229 lines of tests**

---

## Legend

| Term | Meaning |
|------|---------|
| ANE | Apple Neural Engine — dedicated ML accelerator on Apple Silicon chips |
| MLX | Apple's ML framework optimised for Apple Silicon (CPU + GPU + ANE unified memory) |
| Whisper | OpenAI's speech recognition model; apple-murmur uses the MLX-optimised tiny variant |
| VAD | Voice Activity Detection — identifies speech vs silence in audio |
| WebRTC VAD | Google's VAD algorithm from the WebRTC project, used for silence stripping |
| KenLM | Fast n-gram language model library; used for vocabulary correction scoring |
| rapidfuzz | Fuzzy string matching library (Levenshtein distance); used for vocabulary correction |
| pynput | Python library for monitoring keyboard/mouse input globally |
| sounddevice | Python bindings for PortAudio; captures microphone audio |
| pyautogui | Cross-platform GUI automation; used for clipboard paste simulation |
| RMS | Root Mean Square — measure of audio signal amplitude |
| PCM | Pulse-Code Modulation — raw digital audio format |
| TOML | Config file format used by `~/.apple-murmur/config.toml` |
| Bundle ID | macOS app identifier (e.g. `com.apple.Terminal`) used for profile selection |
| Profile | Pipeline configuration that varies per active app (default vs terminal) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        apple-murmur daemon                         │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐               │
│  │  Hotkey   │───▶│    Audio     │───▶│  Platform   │               │
│  │ Listener  │    │   Capture    │    │  Detection  │               │
│  │ (pynput)  │    │ (sounddevice)│    │ (osascript) │               │
│  └──────────┘    └──────────────┘    └──────┬──────┘               │
│                                             │                       │
│                                      ┌──────▼──────┐               │
│                                      │   Profile    │               │
│                                      │  Selection   │               │
│                                      └──────┬──────┘               │
│                                             │                       │
│  ┌──────────────────────────────────────────▼──────────────────┐   │
│  │                    Processing Pipeline                       │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐   │   │
│  │  │  Noise     │  │  Volume    │  │  VAD Silence Strip  │   │   │
│  │  │  Reduce    │──▶│  Normalise │──▶│  (default only)     │   │   │
│  │  │(noisereduce)│  │  (RMS)    │  │  (webrtcvad)        │   │   │
│  │  └────────────┘  └────────────┘  └─────────────────────┘   │   │
│  └─────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                      ┌──────▼──────┐                               │
│                      │   Whisper   │                               │
│                      │  tiny (MLX) │                               │
│                      │  ANE/GPU    │                               │
│                      └──────┬──────┘                               │
│                             │                                       │
│  ┌──────────────────────────▼──────────────────────────────────┐   │
│  │                  Post-Processing Pipeline                    │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │   │
│  │  │ De-abbrev  │  │ Symbol     │  │ Flag Fix   │            │   │
│  │  │ R.M.→rm    │──▶│ Normalizer │──▶│ rm-rf→     │            │   │
│  │  │            │  │ 140+ rules │  │ rm -rf     │            │   │
│  │  └────────────┘  └────────────┘  └────────────┘            │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │   │
│  │  │ Dash/Flag  │  │ Profile    │  │ Vocabulary │            │   │
│  │  │ Collapse   │──▶│ Extra Rules│──▶│ Correction │            │   │
│  │  │ -- verbose │  │ /compact   │  │ (rapidfuzz) │            │   │
│  │  └────────────┘  └────────────┘  └────────────┘            │   │
│  └─────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                      ┌──────▼──────┐                               │
│                      │  Injector   │                               │
│                      │ (clipboard  │                               │
│                      │  paste)     │                               │
│                      └─────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Module Map

### Core Pipeline

| Module | File | Lines | Responsibility |
|--------|------|-------|---------------|
| **Daemon** | `murmur/daemon.py` | 93 | Main loop. Wires hotkey → audio → preprocess → transcribe → normalise → inject. State machine: idle → recording → transcribing → idle. |
| **Engine** | `murmur/engine.py` | 96 | MLX Whisper wrapper. Loads model lazily. Transcribes float32 audio → text. Seeds Whisper with 500+ CLI/IT/name tokens via `initial_prompt`. |
| **Audio** | `murmur/audio.py` | 44 | Microphone capture via sounddevice. 16kHz mono, 480-sample blocks (30ms frames). Thread-safe frame buffer. |
| **Preprocessor** | `murmur/preprocessor.py` | 78 | Audio pipeline: noise reduction (noisereduce) → volume normalisation (RMS target 0.08) → VAD silence stripping (webrtcvad, aggressiveness=2). VAD skipped in terminal profile. |
| **Normalizer** | `murmur/normalizer.py` | 203 | Text pipeline: de-abbreviation → 140+ symbol rules → joined flag fix → dash collapse → dot collapse → multi-space collapse → profile extra rules → vocabulary correction. |
| **Vocabulary** | `murmur/vocabulary.py` | 110 | Fuzzy domain correction. 200+ terms across CLI tools, IT ops, Indian names. rapidfuzz threshold 88. Optional KenLM sentence-level validation. |
| **Injector** | `murmur/injector.py` | 48 | Text insertion. Primary: clipboard copy + Cmd-V paste. Fallback: pyautogui typewrite. Restores previous clipboard contents. |

### Support Modules

| Module | File | Lines | Responsibility |
|--------|------|-------|---------------|
| **Hotkey** | `murmur/hotkey.py` | 60 | Global key listener (pynput). Double-tap detection with configurable interval (default 300ms). Triple-tap guard prevents re-fire. |
| **Config** | `murmur/config.py` | 69 | TOML config loader. Three sections: hotkey (key, interval), model (name, device), audio (sample_rate, channels). Defaults work out-of-box. |
| **Profiles** | `murmur/profiles.py` | 38 | Profile definitions. DEFAULT_PROFILE: VAD on, no extras. TERMINAL_PROFILE: VAD off, prefix collapse (/~$ space removal), explicit "space" token protection. |
| **Platform** | `murmur/platform.py` | 45 | Active app detection via osascript. Maps 8 terminal bundle IDs (Terminal, iTerm2, Warp, Alacritty, Kitty, Ghostty, VS Code, Cursor) to terminal profile. |
| **KenLM Rescorer** | `murmur/kenlm_rescorer.py` | 43 | Optional n-gram LM. Lazy-loads `~/.apple-murmur/models/domain.klm`. Scores sentence log-probability. Graceful no-op when model absent. |
| **CLI** | `murmur/cli.py` | 98 | CLI entry point. Commands: start, stop, status, update. PID file management. Daemon spawns as background process. |

---

## Data Flow

### Audio Path

```
Microphone → sounddevice (16kHz, mono, float32)
    → 480-sample blocks buffered in AudioCapture._frames
    → np.concatenate on stop → single float32 array
    → preprocessor pipeline → cleaned audio
    → mlx_whisper.transcribe() → raw text string
```

### Text Path

```
Raw Whisper output (e.g. "R.M. dash R.F. the file")
    → _deabbreviate()      → "rm dash R.F. the file"
    → symbol rules (140+)  → "rm -R.F. the file"
    → _fix_joined_flags()  → "rm -R.F. the file"
    → dash collapse        → "rm -R.F. the file"
    → dot collapse         → "rm -R.F. the file"
    → profile extra rules  → (no change in default profile)
    → vocabulary.correct() → "rm -rf the file"
    → injector.inject()    → clipboard paste into active app
```

### State Machine

```
                 double-tap
    ┌──────┐  ────────────▶  ┌───────────┐
    │ idle │                 │ recording │
    └──────┘  ◀────────────  └───────────┘
        ▲       double-tap        │
        │       (stop + grab      │ double-tap
        │        audio)           │ (stop + grab audio)
        │                        ▼
        │                  ┌──────────────┐
        └──────────────────│ transcribing │
           (on complete    └──────────────┘
            or error)
```

Double-taps during `transcribing` state are ignored. State transitions are mutex-protected.

---

## Profile System

Profiles control pipeline behaviour based on the active application.

| Aspect | DEFAULT_PROFILE | TERMINAL_PROFILE |
|--------|----------------|-----------------|
| VAD silence strip | Yes — clean flowing prose | No — preserve pauses for word boundaries |
| Prefix collapse | No | Yes — `/`, `~`, `$` remove trailing space |
| Space token | Normal word | Protected marker → survives collapse → restored as literal space |
| Use case | Browsers, email, documents | Terminal, VS Code terminal, Cursor terminal |

### Profile Selection Flow

```
Transcription complete
    → platform.get_active_bundle()     (osascript → bundle ID)
    → bundle in TERMINAL_BUNDLES?
        → Yes: TERMINAL_PROFILE
        → No:  DEFAULT_PROFILE
    → preprocess(audio, profile=selected)
    → normalize(text, profile=selected)
```

### Adding a Profile

1. Define a new `Profile()` in `murmur/profiles.py` with custom `skip_vad` and `extra_rules`
2. Add bundle ID detection logic in `murmur/daemon.py` `_transcribe()`
3. No pipeline code changes needed — the profile drives behaviour

---

## Vocabulary Correction

Two-tier correction system:

### Tier 1: rapidfuzz (always active)

- 200+ domain terms across CLI, IT ops, Indian names
- Levenshtein ratio scoring, threshold 88
- Top 3 candidates evaluated per word
- Words < 3 characters skipped (too short for reliable fuzzy matching)

### Tier 2: KenLM (optional, improves accuracy)

- 3-gram language model trained on IT domain corpus
- Sentence-level log-probability scoring
- Candidate only applied if it improves overall sentence score
- Falls back to rapidfuzz-only when model absent
- Built at install time when `lmplz` binary available

---

## File Layout

```
apple-murmur/
├── murmur/                    # Source package (14 files, 1,025 lines)
│   ├── __init__.py
│   ├── daemon.py              # Main loop + state machine
│   ├── engine.py              # MLX Whisper transcription
│   ├── audio.py               # Microphone capture
│   ├── preprocessor.py        # Noise → volume → VAD pipeline
│   ├── normalizer.py          # 140+ symbol rules + post-processing
│   ├── vocabulary.py          # Fuzzy domain correction
│   ├── kenlm_rescorer.py      # Optional LM scoring
│   ├── injector.py            # Clipboard paste injection
│   ├── hotkey.py              # Double-tap detection
│   ├── config.py              # TOML config loader
│   ├── profiles.py            # Profile definitions
│   ├── platform.py            # Active app detection
│   └── cli.py                 # CLI entry point
├── tests/                     # Test suite (12 files, 1,229 lines)
│   ├── conftest.py            # MLX mock for CI
│   ├── test_normalizer.py     # 451 lines — largest test file
│   └── test_*.py              # One test file per module
├── scripts/
│   ├── build_domain_corpus.py # KenLM training data generator
│   ├── perf_monitor.py        # Idle/active profiling
│   └── claude_voice.md        # /voice command for Claude Code
├── docs/
│   ├── ISSUES.md              # Bug log with causes + fixes
│   └── ARCHITECTURE.md        # This file
├── install.sh                 # One-line curl installer
├── setup.py                   # Package config (entry point: murmur)
├── requirements.txt           # 12 dependencies
└── README.md                  # User-facing docs
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| mlx-whisper | ≥0.3.0 | Whisper inference on Apple Neural Engine |
| sounddevice | ≥0.4.6 | Microphone audio capture (PortAudio bindings) |
| pynput | ≥1.7.6 | Global keyboard listener for hotkey |
| pyperclip | ≥1.8.2 | Cross-app clipboard access |
| pyautogui | ≥0.9.54 | Keyboard simulation (Cmd-V paste, typewrite fallback) |
| toml | ≥0.10.2 | Config file parsing |
| numpy | ≥1.24.0 | Audio array operations |
| rapidfuzz | ≥3.0.0 | Fuzzy string matching for vocabulary correction |
| webrtcvad | ≥2.0.10 | Voice activity detection for silence stripping |
| noisereduce | ≥3.0.0 | Spectral noise reduction |
| huggingface_hub | ≥0.20.0 | Model download at install time |
| pytest | ≥7.4.0 | Test framework |

**Optional:** `kenlm` (not in requirements.txt — built from source when `lmplz` available)

---

## Security & Privacy

- **No network calls at runtime.** All inference runs locally on the Neural Engine. No API keys, no cloud endpoints, no telemetry.
- **No data persistence.** Audio is discarded after transcription. No recordings saved to disk.
- **Clipboard restoration.** Previous clipboard contents are restored after injection.
- **macOS Accessibility permission.** Required for global hotkey capture. Granted per-terminal, not per-process.
- **PID file management.** `~/.apple-murmur/murmur.pid` tracks daemon process. Stale PIDs cleaned up automatically.

---

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| 10s audio transcription | ~150ms | MLX on Apple Neural Engine |
| Model load (first call) | ~300ms | Lazy load, cached after |
| Memory footprint | ~120MB | MLX unified memory |
| Power draw | Low | ANE is power-efficient vs GPU |
| Audio frame size | 30ms (480 samples) | Required by webrtcvad |
| Hotkey detection | <1ms | pynput callback, threading |

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| MLX Whisper engine | Done | Whisper tiny, temperature=0, initial_prompt seeding |
| Audio capture | Done | 16kHz mono, 480-sample blocks |
| Hotkey listener | Done | Configurable key, 300ms double-tap interval |
| Noise reduction | Done | noisereduce, stationary=False |
| Volume normalisation | Done | RMS target 0.08, clip to [-1, 1] |
| VAD silence stripping | Done | webrtcvad aggressiveness=2, profile-controlled |
| Symbol normalizer | Done | 140+ rules, ordered by specificity |
| De-abbreviation | Done | R.M. → rm pattern collapse |
| Joined flag fix | Done | rm-rf → rm -rf |
| Prefix collapse | Done | Terminal profile only, /~$ |
| Space token protection | Done | Survives prefix collapse |
| Vocabulary correction | Done | 200+ terms, rapidfuzz threshold 88 |
| KenLM rescoring | Done | Optional, graceful fallback |
| Profile system | Done | Default + terminal, extensible |
| Platform detection | Done | 8 terminal bundle IDs |
| Text injection | Done | Clipboard paste + typewrite fallback |
| CLI commands | Done | start/stop/status/update |
| Config system | Done | TOML, three sections |
| Install script | Done | One-line curl, venv, model download |
| Claude /voice command | Done | Installed to ~/.claude/commands/ |
| Test suite | Done | 12 test files covering all modules |
