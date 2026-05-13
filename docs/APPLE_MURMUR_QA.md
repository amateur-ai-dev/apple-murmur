# apple-murmur — Q&A

Comprehensive Q&A covering design decisions, how things work, known issues, and development history. Written for anyone reviewing, extending, or debugging the codebase.

---

## 0. Legend

### Audio & Signal Processing

| Term | Meaning |
|------|---------|
| ANE | Apple Neural Engine — dedicated ML hardware on M1/M2/M3/M4 chips |
| MLX | Apple's ML framework for unified CPU/GPU/ANE memory |
| Whisper | OpenAI's speech recognition model |
| VAD | Voice Activity Detection — distinguishes speech from silence |
| WebRTC VAD | Google's VAD from the WebRTC project |
| RMS | Root Mean Square — measure of audio amplitude |
| PCM | Pulse-Code Modulation — raw digital audio format |
| 16kHz | Sample rate — 16,000 samples per second, standard for speech |
| float32 | 32-bit floating-point audio representation (range -1.0 to 1.0) |

### Text Processing

| Term | Meaning |
|------|---------|
| Normalizer | Converts spoken symbol names to actual characters |
| De-abbreviation | Reverses Whisper's R.M. → rm expansion quirk |
| Prefix collapse | Removes spaces after /, ~, $ in terminal mode |
| Space token | Spoken word "space" that inserts literal space in terminal mode |
| rapidfuzz | Fuzzy string matching library using Levenshtein distance |
| KenLM | N-gram language model for sentence probability scoring |

### System

| Term | Meaning |
|------|---------|
| Bundle ID | macOS application identifier (e.g. `com.apple.Terminal`) |
| Profile | Pipeline configuration selected per active app |
| pynput | Python library for global keyboard monitoring |
| sounddevice | Python bindings for PortAudio audio capture |
| pyautogui | GUI automation library for keyboard/clipboard simulation |
| TOML | Configuration file format (`~/.apple-murmur/config.toml`) |

---

## 1. Architecture & Design

**Q: Why MLX instead of PyTorch/ONNX/CoreML?**

MLX runs Whisper on Apple's Neural Engine with unified memory — no CPU↔GPU copies. Result: ~150ms for 10s audio vs ~500ms with PyTorch MPS. Memory footprint is ~120MB vs ~300MB. The tradeoff is Apple Silicon exclusivity, which is the explicit scope of this project (murmur covers cross-platform).

**Q: Why Whisper tiny specifically?**

Latency over accuracy. Tiny is 39M params, runs in ~150ms on ANE. Whisper small (244M params) would be ~800ms — too slow for real-time dictation. The accuracy gap is compensated by the vocabulary correction layer and initial_prompt seeding.

**Q: Why does the engine use `initial_prompt` with 500+ terms?**

Whisper's decoder biases toward tokens it has recently seen. Seeding with CLI commands (`rm`, `chmod`, `kubectl`), IT terms (`Kubernetes`, `ITSM`), and Indian names (`Nithin`, `Sharma`) dramatically improves first-pass accuracy for these domains. Without it, Whisper produces generic English transcriptions that miss technical vocabulary.

**Q: Why is the model loaded lazily?**

MLX models auto-load on first inference call. Explicit `.load()` is a no-op stub so the daemon can call `engine.load()` without branching. Actual model load happens on first `transcribe()` and takes ~300ms, cached after.

**Q: Why clipboard paste instead of direct text injection?**

No macOS API exists for injecting arbitrary text into any app's focused text field. Clipboard paste (Cmd-V) is the only universal method that works across Terminal, browsers, Electron apps, native apps, etc. The typewrite fallback (simulating individual keystrokes) exists for edge cases where clipboard access fails but is slower and doesn't handle special characters.

**Q: Why restore previous clipboard contents?**

Users don't expect voice dictation to overwrite their clipboard. After injection, the previous clipboard is restored. If restoration fails (e.g. clipboard was an image), the failure is silently ignored — the text injection already succeeded.

---

## 2. Profile System

**Q: Why two profiles instead of a single pipeline?**

Terminal command dictation and prose dictation have conflicting requirements. Prose benefits from silence stripping (clean flowing text). Terminal commands need pauses preserved — Whisper uses gaps between spoken words to infer word boundaries. Without pauses, "git status" becomes "gitstatus". Prefix collapse (`/compact` not `/ compact`) is only useful in terminals and would break prose.

**Q: How does profile selection work?**

At transcription time (not recording start), the daemon calls `platform.get_active_bundle()` via osascript. If the bundle ID matches any of the 8 known terminal emulators, TERMINAL_PROFILE is used. Otherwise DEFAULT_PROFILE. Selection happens after audio capture because the user might switch apps between starting and stopping recording.

**Q: What terminals are detected?**

Terminal.app, iTerm2, Warp, Alacritty, Kitty, Ghostty, VS Code (integrated terminal), and Cursor editor terminal. Each identified by macOS bundle ID.

**Q: How does the explicit "space" token work?**

In TERMINAL_PROFILE, the prefix collapse step removes spaces after `/`, `~`, `$`. But sometimes you want a space (e.g. `/ compact` as two separate tokens). Saying "space" inserts a placeholder marker (`\x01`) before collapse runs. After collapse, the marker is restored to a real space. So `slash space compact` → `/ compact` while `slash compact` → `/compact`.

**Q: How do I add a new profile?**

Define a new `Profile()` in `murmur/profiles.py` with `skip_vad` and `extra_rules`. Add the app's bundle ID to detection logic in `daemon.py`. No pipeline changes needed — profiles are data, not code branches.

---

## 3. Audio Pipeline

**Q: Why 480-sample blocks?**

WebRTC VAD requires frame sizes of exactly 10, 20, or 30ms. At 16kHz, 30ms = 480 samples. Both `AudioCapture._BLOCK_SIZE` and `preprocessor._VAD_FRAME_SAMPLES` use this value and must stay in sync.

**Q: Why is VAD aggressiveness set to 2?**

Scale is 0 (least aggressive) to 3 (most aggressive). Level 2 balances removing background silence without clipping speech edges. Level 3 was too aggressive — it clipped quiet consonants at word boundaries.

**Q: What happens if noisereduce or webrtcvad aren't installed?**

Both degrade gracefully. `_reduce_noise()` catches ImportError and returns audio unchanged. `_strip_silence_vad()` checks for webrtcvad import and skips if missing. The pipeline always produces output, just with less preprocessing.

**Q: Why is the RMS target 0.08?**

Whisper expects normalised audio around this amplitude range. Too quiet and it hallucinates. Too loud and it clips. 0.08 RMS with clip to [-1.0, 1.0] keeps the signal in Whisper's sweet spot.

**Q: What happens to trailing audio samples that don't fill a 480-sample frame?**

They are discarded. At most ~30ms of audio is lost at the end of a recording — inaudible and well below the threshold for a recognisable phoneme.

---

## 4. Normalizer

**Q: Why are there 140+ rules instead of a simpler approach?**

Each rule is a regex mapping a spoken form to a character. The high count comes from covering: multi-character operators (20+ rules), comparison operators (6), bracket/brace variants (12), single-character symbols (40+), URL domains (8), and edge cases. No LLM or ML is involved — pure deterministic regex replacement.

**Q: Why does rule ordering matter?**

Longer/more-specific patterns must come before shorter ones. `not equal to` must match before `not` or `equal` individually. `double dash` before `dash`. `at sign` before `at`. Wrong ordering produces partial matches and garbage output.

**Q: What is de-abbreviation?**

Whisper sometimes transcribes short CLI commands as abbreviation-style tokens: `rm` → `R.M.`, `ls` → `L.S.`, `git` → `G.I.T.`. The `_deabbreviate()` step collapses any `X.Y.` pattern back to lowercase before other processing runs.

**Q: What is the joined flag fix?**

Whisper sometimes outputs `rm-rf` instead of `rm -rf` (joins command and flags with a hyphen). `_fix_joined_flags()` detects patterns where a 2-4 letter command is directly hyphenated to a 1-6 letter flag and reinserts the space.

**Q: Why does the newline rule not work end-to-end?**

The `\bnew\s*line\b` rule correctly injects `\n` into the text. But `vocabulary.correct()` uses `str.split()` which collapses all whitespace including newlines. The newline is lost. This is a known limitation — low priority because newlines aren't useful in the current dictation workflow.

---

## 5. Vocabulary Correction

**Q: Why fuzzy matching instead of an exact dictionary?**

Whisper's output varies. "Kubernetes" might come out as "Kubernetis", "Kubenetes", or "Kubernetees". Exact matching would need every possible misspelling. Fuzzy matching (Levenshtein ratio ≥ 88) catches all of these with a single canonical entry.

**Q: Why threshold 88?**

Empirically tuned. Lower thresholds (80-85) produced false positives — short common words being "corrected" to unrelated domain terms. Higher thresholds (90+) missed legitimate corrections. 88 is the sweet spot for the current vocabulary size.

**Q: Why skip words shorter than 3 characters?**

Two-letter words like "rm", "ls", "cd" are too short for reliable fuzzy matching — they match too many candidates. The de-abbreviation step handles the main failure mode (R.M. → rm) without fuzzy matching.

**Q: What does KenLM add over rapidfuzz alone?**

rapidfuzz picks the closest match. KenLM validates that match in context. If "CUDA" fuzzy-matches to "Cuda" but the sentence probability drops, KenLM rejects the substitution. This prevents false corrections where the Whisper output was actually correct but happened to fuzzy-match a domain term.

**Q: What if KenLM isn't installed?**

Vocabulary correction falls back to rapidfuzz-only. The first candidate above threshold 88 is used without sentence-level validation. Accuracy is slightly lower but still functional.

---

## 6. Hotkey

**Q: Why Left Control instead of fn?**

macOS reserves `fn` for the emoji picker system-wide. pynput cannot intercept it. `alt_r` (Right Option) conflicts with Claude Desktop. Left Control (`ctrl_l`) has no system conflict and is physically accessible.

**Q: How does double-tap detection work?**

`HotkeyListener` tracks `_last_press_time`. On each press of the target key, it checks if the elapsed time since the last press is within the configured interval (default 300ms). If yes → double-tap detected, callback fires in a new daemon thread. `_last_press_time` is reset to 0 to prevent triple-tap re-fire.

**Q: Why is the callback fired in a thread?**

Transcription takes ~150ms+ and must not block the hotkey listener. A daemon thread allows the listener to continue monitoring for the next double-tap while transcription runs. The daemon's state machine prevents concurrent recordings.

**Q: What happens if I double-tap during transcription?**

Nothing. The daemon's state is `transcribing`, so the double-tap callback exits without action. No queuing, no race condition.

---

## 7. Injection

**Q: How does text injection work?**

1. Save current clipboard contents
2. Copy transcribed text to clipboard
3. Simulate Cmd-V (macOS) or Ctrl-V (Linux)
4. Wait 100ms for paste to complete
5. Restore previous clipboard contents

**Q: Why the 50ms + 100ms delays?**

The 50ms after clipboard copy lets the system clipboard settle — some apps poll clipboard state asynchronously. The 100ms after paste gives the target app time to process the paste event before we overwrite the clipboard with the restored contents.

**Q: What if clipboard injection fails?**

Falls back to `pyautogui.typewrite()` which simulates individual keystrokes. Slower (~10ms per char) and doesn't handle non-ASCII characters, but works when clipboard access is restricted.

---

## 8. Configuration

**Q: What's configurable?**

Three sections in `~/.apple-murmur/config.toml`:

```toml
[hotkey]
key = "ctrl_l"              # ctrl_l | ctrl_r | alt_r | cmd_r | cmd_l | shift_r | caps_lock
double_tap_interval_ms = 300

[model]
name = "whisper-tiny-mlx"
device = "auto"              # unused — MLX auto-selects

[audio]
sample_rate = 16000
channels = 1
```

**Q: What happens if config.toml doesn't exist?**

Defaults are used — Left Control, whisper-tiny-mlx, 16kHz mono. The file is optional.

---

## 9. Installation

**Q: What does install.sh do?**

1. Checks Apple Silicon (`uname -m` = arm64)
2. Checks Python 3.9+
3. Clones repo to `~/.apple-murmur/` (or pulls if already cloned)
4. Creates Python venv, installs 12 dependencies
5. Downloads whisper-tiny-mlx model (~75MB) from HuggingFace
6. Optionally builds KenLM domain model (if `lmplz` available)
7. Installs `murmur` CLI wrapper to `/usr/local/bin/`
8. Installs `/voice` command for Claude Code

**Q: How does the CLI wrapper work?**

The wrapper at `/usr/local/bin/murmur` activates the venv and runs `python3 -m murmur.cli`. This means `murmur start` works from any directory without manually activating the venv.

**Q: How does `murmur update` work?**

Stops daemon if running → `git pull` in install dir → `pip install -r requirements.txt` → restarts daemon if it was running. Simple but effective.

**Q: What about reinstalling over an existing non-git install?**

install.sh detects if `~/.apple-murmur/` exists but isn't a git repo (manual install). It preserves `config.toml`, removes the old directory, and clones fresh.

---

## 10. Testing

**Q: How are tests structured?**

One test file per module, 12 total. Test files mirror source structure: `tests/test_normalizer.py` tests `murmur/normalizer.py`.

**Q: How does CI work without mlx_whisper?**

`tests/conftest.py` uses `sys.modules.setdefault("mlx_whisper", MagicMock())` to pre-mock MLX before any imports. Tests run on standard Python without Apple Silicon hardware.

**Q: Which module has the most tests?**

`test_normalizer.py` at 451 lines — it covers all 140+ symbol rules, de-abbreviation patterns, joined flag fixes, and profile-specific behaviour.

---

## 11. Known Issues & Limitations

**Q: Why can't the newline rule work end-to-end?**

`vocabulary.correct()` uses `str.split()` which collapses newlines. Fix would require line-delimited processing in `correct()`. Low priority — newlines aren't useful in current workflows.

**Q: Why can't 2-letter commands be fuzzy-corrected?**

Words < 3 chars have too many fuzzy matches at threshold 88. False positive rate is unacceptable. De-abbreviation handles the main failure mode (R.M. → rm).

**Q: Is browser text injection reliable?**

Not fully. Chrome and some browsers have security restrictions on paste events. Clipboard timing issues cause occasional failures. No consistent reproduction steps identified.

**Q: Does it work with non-English speech?**

Whisper tiny supports multilingual transcription but accuracy drops significantly for non-English. The vocabulary correction and initial_prompt are English-only. Not recommended for non-English use.

---

## 12. Development History

| Phase | Key Changes | Commits |
|-------|-------------|---------|
| **v1: Core daemon** | Audio capture, Whisper engine, hotkey, injection, CLI | `7148884` – `fda01e2` |
| **v2: Preprocessing** | Noise reduction, VAD, vocabulary correction, KenLM | `c5c5146` – `066c029` |
| **v3: Terminal optimisation** | Symbol normalizer (140+ rules), CLI vocab, Indian names, profile system | `153cdc6` – `50de935` |

### Key Design Decisions (Chronological)

1. **fn → alt_r → ctrl_l** — Three hotkey iterations before settling on Left Control
2. **Silence auto-stop removed** — Added in v2, removed in v3. Unreliable for terminal dictation where pauses between words are intentional
3. **Profile system** — Introduced to resolve the conflict between prose and terminal dictation requirements
4. **Prefix collapse with space protection** — Solving `/compact` vs `/ compact` required a marker-based protection scheme
5. **KenLM optional** — Made non-blocking after discovering `lmplz` isn't commonly installed on developer machines

---

## 13. Comparison with murmur (Cross-Platform)

| Aspect | apple-murmur | murmur |
|--------|-------------|--------|
| Engine | MLX Whisper (ANE) | PyTorch Whisper (MPS/CUDA/CPU) |
| Platform | Apple Silicon only | macOS, Linux, Windows |
| Latency | ~150ms / 10s audio | ~500ms / 10s audio |
| Memory | ~120MB | ~300MB |
| Model load | ~300ms | ~800ms |
| Power draw | Low (ANE) | Medium (GPU) |
| Repo | `amateur-ai-dev/apple-murmur` | `amateur-ai-dev/murmur` |

Both share the same normalizer rules, vocabulary list, and profile concepts. apple-murmur is the performance-optimised fork for Apple Silicon users.
