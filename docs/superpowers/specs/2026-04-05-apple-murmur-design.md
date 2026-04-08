# apple-murmur — Design Spec
**Date:** 2026-04-05  
**Last updated:** 2026-04-09  
**Version:** 3.0  
**Platform:** Apple Silicon macOS only (M1/M2/M3/M4)

---

## Overview

apple-murmur is the Apple Silicon-native sibling of murmur. Identical UX — double-tap Left Control anywhere, speak, double-tap again, text injects at cursor — but uses Apple's MLX framework to run Whisper on the Neural Engine instead of PyTorch MPS. Result: near-instant transcription, lower power draw, smaller memory footprint.

This is not a cross-platform tool. It is purpose-built for Apple Silicon and accepts that constraint in exchange for maximum on-device performance.

**v2 additions:** audio preprocessing pipeline (noisereduce + webrtcvad), IT domain vocabulary correction (rapidfuzz + optional KenLM), spoken punctuation normalizer, Whisper tuning params.

**v3 additions:** explicit double-tap stop only (silence auto-stop removed), comprehensive CLI tool vocabulary (100+ tools in prompt and fuzzy corrector), Indian names recognition (~70 first names + ~50 surnames), full spoken-symbol normalizer for terminal use (31 new rules covering all CLI operators and punctuation).

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                       │
│   murmur CLI (start/stop/status/update)                   │
│   /voice  — Claude Code slash command                     │
├──────────────────────────────────────────────────────────┤
│                      DAEMON LAYER                         │
│   Hotkey listener  (pynput, global, Left Control ×2)      │
│   Audio capture    (sounddevice, 16kHz, 30ms frames)      │
│   Preprocessor     (noisereduce → normalise → VAD strip)  │
│   Text injector    (clipboard + paste, any app)           │
│   Normalizer       (spoken symbols → chars, 50+ rules)    │
│   Vocabulary       (CLI + IT + Indian names, rapidfuzz)   │
│   State machine    (idle / recording / transcribing)      │
├──────────────────────────────────────────────────────────┤
│                      ENGINE LAYER                         │
│   mlx-whisper (Apple MLX framework)                       │
│   Runs on Neural Engine (ANE)                             │
│   Whisper tiny model — MLX format                         │
│   CLI + IT + names initial prompt, beam=3, temperature=0  │
└──────────────────────────────────────────────────────────┘
```

---

## Components

### 1. CLI (`murmur/cli.py`)
Identical to murmur. Binary name: `murmur`. Commands: `start`, `stop`, `status`, `update`.

### 2. Daemon (`murmur/daemon.py`)
State machine: `idle → recording → transcribing → idle`. On second double-tap while recording: calls `preprocessor.preprocess()` then `engine.transcribe()` then `normalizer.normalize()` (which includes vocabulary correction). SIGTERM-safe. There is no silence-based auto-stop — recording continues until the user explicitly double-taps again.

### 3. Hotkey Listener (`murmur/hotkey.py`)
Default key: `ctrl_l` (Left Control) on macOS. `fn` is **not** used — macOS reserves it for the emoji picker. 300ms double-tap interval. Global capture via pynput; requires Accessibility permission.

Configurable via `~/.apple-murmur/config.toml`:
```toml
[hotkey]
key = "ctrl_l"   # ctrl_l | ctrl_r | alt_r | cmd
double_tap_interval_ms = 300
```

### 4. Audio Capture (`murmur/audio.py`)
sounddevice, 16kHz mono, 30ms frames (480 samples). Captures audio continuously from start to explicit stop — no silence detection or auto-stop. The 480-sample frame size is kept in sync with `preprocessor._VAD_FRAME_SAMPLES` (used for post-recording VAD stripping).

### 5. Preprocessor (`murmur/preprocessor.py`)
Applied to every recording before Whisper inference:

1. **Noise reduction** — `noisereduce` non-stationary mode, 75% reduction. Graceful fallback if unavailable.
2. **Volume normalisation** — scales RMS to 0.08; clips to ±1.0.
3. **VAD silence stripping** — removes non-speech frames using WebRTC VAD (aggressiveness=2). Returns original if all frames stripped.

### 6. Inference Engine (`murmur/engine.py`)
Uses `mlx-whisper` with tuned parameters:

```python
mlx_whisper.transcribe(
    audio,
    path_or_hf_repo=model_path,
    temperature=0.0,
    beam_size=3,
    condition_on_previous_text=True,
    initial_prompt=_INITIAL_PROMPT,
)
```

`_INITIAL_PROMPT` seeds Whisper's vocabulary toward:
- **Shell built-ins and file ops:** bash, zsh, chmod, sudo, find, grep, awk, sed, xargs, …
- **Version control:** git, gh, svn, clone, commit, push, pull, rebase, GitHub, GitLab, …
- **Package managers:** npm, pip, brew, apt, yarn, cargo, gem, poetry, conda, …
- **Containers/infra:** docker, kubectl, helm, terraform, ansible, pulumi, podman, …
- **Languages/runtimes:** python, node, ruby, rust, java, golang, swift, …
- **Databases:** psql, mysql, redis, mongo, sqlite3, …
- **Networking:** ssh, curl, wget, rsync, nmap, dig, …
- **System/process:** systemctl, journalctl, crontab, tmux, …
- **Build/cloud:** make, webpack, vite, aws, gcloud, az, vercel, heroku, …
- **IT managed services:** ITSM, ITIL, ServiceNow, SLA, MTTR, Kubernetes, Azure, …
- **Indian first names:** Nithin, Rahul, Priya, Arjun, Aditya, Sharma, … (~70 names)
- **Indian surnames:** Sharma, Patel, Reddy, Nair, Krishnan, Balakrishnan, … (~50 surnames)

Model runs on Apple Neural Engine via MLX. Lazy-loaded on first inference call.

### 7. Normalizer (`murmur/normalizer.py`)
Regex rules applied post-transcription, in priority order (longer/more-specific before shorter):

**URL suffixes:** `dot com` → `.com`, `dot io` → `.io`, …

**Multi-character operators (before single-char):**
`double dash` → `--`, `double equals` → `==`, `double colon` → `::`, `double pipe` / `pipe pipe` → `||`, `double greater than` / `greater greater` → `>>`, `double less than` → `<<`, `double ampersand` / `ampersand ampersand` → `&&`, `fat arrow` / `equals greater than` → `=>`, `right arrow` / `dash greater than` → `->`, `at the rate` → `@`, `triple dot` / `ellipsis` → `...`, `double dot` / `dot dot` → `..`

**Punctuation names (existing):**
`at sign` → `@`, `hashtag` → `#`, `open paren` → `(`, `close paren` → `)`, `open bracket` → `[`, `close bracket` → `]`, `open brace` → `{`, `close brace` → `}`, `forward slash` → `/`, `back slash` → `\`, `underscore` → `_`, `ampersand` → `&`, `percent sign` → `%`

**Single-character CLI symbols:**
`pipe` → `|`, `greater than` → `>`, `less than` → `<`, `semicolon` → `;`, `tilde` → `~`, `asterisk` / `star` → `*`, `dollar sign` / `dollar` → `$`, `dash` → `-`, `equals sign` / `equals` → `=`, `bang` / `exclamation mark` → `!`, `caret` / `hat` → `^`, `backtick` / `back tick` / `grave` → `` ` ``, `colon` → `:`, `question mark` → `?`, `single quote` → `'`, `double quote` → `"`, `plus sign` / `plus` → `+`, `comma` → `,`, `period` / `full stop` → `.`

**Post-processing:** spaces between a `-` or `--` and the immediately following argument are collapsed (`-- verbose` → `--verbose`). Spaces around a `.` between non-space characters are collapsed (`out . txt` → `out.txt`). Multiple consecutive spaces are collapsed.

Calls `vocabulary.correct()` at the end of every normalize pass.

### 8. Vocabulary Corrector (`murmur/vocabulary.py`)
Fuzzy matching using rapidfuzz (threshold 88). Covers three domains:

- **CLI tools and shell:** git, docker, kubectl, npm, pip, brew, ssh, curl, terraform, ansible, vim, tmux, GitHub, GitLab, Homebrew, and 60+ more
- **IT managed services:** ITSM, ITIL, ServiceNow, Jira, SLA, MTTR, Kubernetes, Azure, AWS, Datadog, and the full v2 IT ops vocabulary
- **Indian names:** ~70 first names (Rahul, Priya, Arjun, Nithin, Deepak, Sharma, …) and ~50 surnames (Sharma, Patel, Reddy, Nair, Krishnan, Balakrishnan, …)

When KenLM is loaded, candidates are validated by sentence-level log-probability improvement before substitution. Single-candidate paths are LM-validated too.

### 9. KenLM Rescorer (`murmur/kenlm_rescorer.py`)
Optional. Lazy-loads `~/.apple-murmur/models/domain.klm` on first use. Graceful fallback to pure rapidfuzz if `kenlm` is not installed or model is absent. Built at install time from `scripts/build_domain_corpus.py` when `lmplz` is available.

### 10. Text Injector (`murmur/injector.py`)
Clipboard paste into any focused text field, system-wide. Falls back to `pyautogui.typewrite` if clipboard fails.

### 11. Config (`murmur/config.py`)
```toml
[hotkey]
key = "ctrl_l"
double_tap_interval_ms = 300

[model]
name = "whisper-tiny-mlx"

[audio]
sample_rate = 16000
```

---

## Install Flow

```bash
curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/apple-murmur/main/install.sh | bash
```

1. Check Apple Silicon (`uname -m` == `arm64`), Python 3.9+
2. Clone repo to `~/.apple-murmur/`
3. Create venv, `pip3 install -r requirements.txt` (includes rapidfuzz, webrtcvad, noisereduce)
4. Install package with `pip3 install -e`
5. Download `mlx-community/whisper-tiny-mlx` (~75MB) to `~/.apple-murmur/models/`
6. **Optional:** build KenLM domain LM if `lmplz` is available
7. Install `murmur` CLI to `/usr/local/bin/`
8. Copy `scripts/claude_voice.md` to `~/.claude/commands/voice.md`
9. Prompt for Accessibility permission (non-blocking)
10. Run `murmur status` to verify

---

## File Structure

```
apple-murmur/
├── install.sh
├── requirements.txt
├── setup.py
├── README.md
├── murmur/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── daemon.py
│   ├── hotkey.py
│   ├── audio.py           # sounddevice capture, 30ms frames, no silence detection
│   ├── engine.py          # mlx-whisper, ANE, tuned params, CLI+IT+names prompt
│   ├── preprocessor.py    # noisereduce → normalise → VAD strip (post-recording)
│   ├── normalizer.py      # spoken symbols → chars (50+ rules); calls vocabulary
│   ├── vocabulary.py      # CLI + IT + Indian names fuzzy correction (rapidfuzz + KenLM)
│   ├── kenlm_rescorer.py  # optional KenLM LM, lazy-loaded
│   └── injector.py
├── scripts/
│   ├── claude_voice.md
│   ├── build_domain_corpus.py   # 120-sentence IT corpus for KenLM
│   └── perf_monitor.py          # CPU/memory/ANE profiler
├── tests/
│   ├── conftest.py              # mocks for mlx_whisper, webrtcvad, noisereduce, rapidfuzz, kenlm
│   ├── test_audio.py
│   ├── test_config.py
│   ├── test_daemon.py
│   ├── test_engine.py
│   ├── test_hotkey.py
│   ├── test_injector.py
│   ├── test_kenlm_rescorer.py
│   ├── test_normalizer.py       # 55 tests covering all symbol rules + compositions
│   ├── test_preprocessor.py
│   └── test_vocabulary.py
├── models/              # .gitignored — downloaded at install
└── docs/
    └── superpowers/
        ├── specs/
        └── plans/
```

---

## Dependencies

```
mlx-whisper>=0.3.0       # Whisper on Apple Neural Engine
sounddevice>=0.4.6       # audio capture
pynput>=1.7.6            # global hotkey
pyperclip>=1.8.2         # clipboard
pyautogui>=0.9.54        # fallback text injection
toml>=0.10.2             # config
numpy>=1.24.0
huggingface_hub>=0.20.0  # model download
rapidfuzz>=3.0.0         # vocabulary fuzzy matching
webrtcvad>=2.0.10        # post-recording VAD silence stripping (preprocessor only)
noisereduce>=3.0.0       # pre-inference noise reduction
# kenlm — optional, installed separately, built from build_domain_corpus.py
```

---

## Performance vs murmur

| Metric | murmur (PyTorch MPS) | apple-murmur (MLX ANE) |
|---|---|---|
| 10s audio latency | ~500ms | ~150ms |
| Model load time | ~800ms | ~300ms |
| Memory footprint | ~300MB | ~120MB |
| Power draw | Medium | Low |
| Cross-platform | Yes | No |

---

## Test Suite

109 tests, all passing. Run with:

```bash
source ~/.apple-murmur/venv/bin/activate
pytest -v
```

Key test files:
- `test_normalizer.py` — 55 tests, one per symbol rule plus composition tests
- `test_vocabulary.py` — mock-based rapidfuzz/KenLM tests + vocab membership checks
- `test_engine.py` — prompt content checks + transcribe pipeline
- `test_daemon.py` — state machine transitions

---

## Relationship to murmur

apple-murmur started as murmur with only `engine.py` different, but has since diverged:
- **Shared:** `cli.py`, `config.py`, `hotkey.py`, `injector.py`
- **Extended:** `audio.py`, `daemon.py`, `normalizer.py`
- **New:** `engine.py`, `preprocessor.py`, `vocabulary.py`, `kenlm_rescorer.py`, `scripts/build_domain_corpus.py`

A `murmur-core` shared package remains a future option if divergence continues.

---

## Non-Goals (v3)

- No Intel Mac support
- No GUI, no menu bar icon
- No multi-language (tiny model only)
- No streaming transcription
- No shared package with murmur (duplication is intentional and simple)
- No NL-to-command conversion (transcription is verbatim; user composes commands)
- No terminal context detection (symbol normalizer is always active, not context-aware)
