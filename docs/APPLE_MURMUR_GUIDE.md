# apple-murmur — Complete Guide

Everything about apple-murmur in plain English. Start here.

---

## What It Is

apple-murmur is a voice-to-text tool for Apple Silicon Macs. Double-tap a key, speak, and your words appear wherever your cursor is — in any app, any text field. No cloud, no API keys, no subscriptions. Everything runs locally on your Mac's Neural Engine.

It's built for two use cases:
1. **General dictation** — prose, emails, documents, chat messages
2. **Terminal command dictation** — speak CLI commands with symbols, and they appear correctly formatted

---

## How It Works (The Short Version)

```
You double-tap Left Control
    → Microphone starts recording
You double-tap Left Control again
    → Recording stops
    → Audio is cleaned up (noise removal, volume normalisation)
    → Whisper AI transcribes speech to text (~150ms)
    → Text is cleaned up (symbols converted, terminology corrected)
    → Text is pasted at your cursor via clipboard
```

The whole process takes about 150-300ms after you stop recording.

---

## Installation

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/apple-murmur/main/install.sh | bash
```

This will:
- Check you're on Apple Silicon (M1/M2/M3/M4)
- Clone the repo to `~/.apple-murmur/`
- Create a Python virtual environment
- Install dependencies
- Download the Whisper tiny model (~75MB, one-time)
- Optionally build a language model for better IT terminology correction
- Install the `murmur` command to your PATH

### Requirements

- Apple Silicon Mac (M1, M2, M3, or M4)
- macOS 13 Ventura or later
- Python 3.9 or later
- Accessibility permission (you'll be prompted)

### Accessibility Permission

macOS requires you to grant Accessibility permission for the hotkey to work system-wide. Go to:

**System Settings → Privacy & Security → Accessibility**

Add your terminal app (Terminal.app, iTerm2, etc.) and enable it. You only need to do this once.

---

## Usage

### Starting and Stopping

```bash
murmur start     # Start the daemon (runs in background)
murmur stop      # Stop the daemon
murmur status    # Check if it's running
murmur update    # Pull latest code and restart
```

### Recording

1. **Start recording:** Double-tap **Left Control** (`ctrl_l`)
2. **Speak** your text
3. **Stop recording:** Double-tap **Left Control** again
4. Text appears at your cursor

There is no silence-based auto-stop. Recording continues until you explicitly tap again. This is intentional — for terminal commands, pauses between words help Whisper produce better results.

### Changing the Hotkey

Edit `~/.apple-murmur/config.toml`:

```toml
[hotkey]
key = "ctrl_l"   # Options: ctrl_l, ctrl_r, alt_r, cmd_r, cmd_l, shift_r, caps_lock
double_tap_interval_ms = 300  # How fast you need to tap (milliseconds)
```

Note: `fn` is not supported — macOS reserves it for the emoji picker.

---

## App Profiles

apple-murmur detects which app you're using and adjusts its behaviour automatically.

### Default Profile (Non-Terminal Apps)

Used in browsers, email clients, documents, chat apps — anything that isn't a terminal.

- Silent gaps in your speech are removed, producing clean flowing text
- Symbols are converted but no prefix collapsing happens
- Best for: natural prose dictation

### Terminal Profile

Automatically activated when the frontmost app is a known terminal emulator: Terminal.app, iTerm2, Warp, Alacritty, Kitty, Ghostty, VS Code integrated terminal, or Cursor editor terminal.

- Silent gaps are preserved — Whisper uses them to space words correctly for CLI commands
- Prefix characters (`/`, `~`, `$`) collapse with the following word: `slash compact` → `/compact`
- The spoken word "space" inserts a literal space that survives prefix collapse

### Examples

In a terminal:
- Say `slash compact` → get `/compact`
- Say `tilde slash projects` → get `~/projects`
- Say `dollar HOME` → get `$HOME`
- Say `slash space compact` → get `/ compact` (explicit space preserved)

In any other app, these spoken words produce their symbol equivalents with normal spacing.

---

## Speaking Symbols

You can speak CLI symbols by name. apple-murmur converts them automatically.

### Operators

| Say this | Get this |
|----------|----------|
| `double dash verbose` | `--verbose` |
| `double equals` | `==` |
| `double ampersand` | `&&` |
| `double pipe` | `\|\|` |
| `not equal` or `not equal to` | `!=` |
| `less than or equal` | `<=` |
| `greater than or equal` | `>=` |
| `right arrow` | `->` |
| `fat arrow` | `=>` |
| `left arrow` | `<-` |
| `append` | `>>` |
| `double colon` | `::` |
| `triple dot` or `ellipsis` | `...` |

### Common Symbols

| Say this | Get this |
|----------|----------|
| `pipe` | `\|` |
| `slash` | `/` |
| `backslash` | `\` |
| `dash` / `minus` / `hyphen` | `-` |
| `asterisk` / `star` / `times` | `*` |
| `dollar` | `$` |
| `bang` / `exclamation` | `!` |
| `hash` / `pound` | `#` |
| `at sign` | `@` |
| `tilde` | `~` |
| `underscore` | `_` |
| `equals` | `=` |
| `caret` / `hat` | `^` |
| `backtick` / `tick` | `` ` `` |
| `semicolon` | `;` |
| `colon` | `:` |
| `percent` | `%` |
| `ampersand` | `&` |
| `plus` | `+` |

### Brackets

| Say this | Get this |
|----------|----------|
| `open paren` | `(` |
| `close paren` | `)` |
| `open bracket` / `open square` | `[` |
| `close bracket` / `close square` | `]` |
| `open brace` / `open curly` | `{` |
| `close brace` / `close curly` | `}` |
| `open angle` / `open chevron` | `<` |
| `close angle` / `close chevron` | `>` |

### URL Domains

| Say this | Get this |
|----------|----------|
| `dot com` | `.com` |
| `dot org` | `.org` |
| `dot io` | `.io` |
| `dot ai` | `.ai` |

---

## Vocabulary Correction

apple-murmur automatically corrects commonly misheard technical terms. It uses fuzzy matching (rapidfuzz) to catch misspellings that Whisper produces.

### What Gets Corrected

**CLI tools** — git, docker, kubectl, npm, pip, brew, ssh, terraform, ansible, helm, vim, tmux, curl, wget, rsync, and 60+ more.

**IT managed services** — ITSM, ITIL, ServiceNow, Jira, SLA, MTTR, Kubernetes, Azure, AWS, GCP, Datadog, and related terms.

**Indian names** — ~70 first names (Rahul, Priya, Arjun, Nithin, ...) and ~50 surnames (Sharma, Patel, Reddy, Nair, Krishnan, ...).

### How It Works

Each word in the transcription is checked against the vocabulary list. If the fuzzy match score is ≥ 88 (out of 100), the correction is applied. If a KenLM language model is installed, corrections are validated against sentence-level probability — a correction is only applied if it improves the overall sentence likelihood.

### Limitations

- Words shorter than 3 characters (like `rm`, `ls`, `cd`) are not fuzzy-matched — they're too short for reliable matching. The de-abbreviation step handles the main failure mode.
- The vocabulary is English-only.

---

## Whisper Quirk Fixes

Whisper has two well-known behaviours with short technical commands that apple-murmur automatically corrects:

### Abbreviation Expansion

Whisper sometimes transcribes short commands as initials:
- `rm` → `R.M.`
- `ls` → `L.S.`
- `git` → `G.I.T.`

apple-murmur detects this pattern and collapses it back: `R.M.` → `rm`.

### Flag Joining

Whisper sometimes joins commands with their flags:
- `rm -rf` → `rm-rf`
- `ls -la` → `ls-la`

apple-murmur detects this and reinserts the space.

---

## Configuration

All configuration lives in `~/.apple-murmur/config.toml`. The file is optional — sensible defaults are used if it doesn't exist.

```toml
[hotkey]
key = "ctrl_l"                    # Which key to double-tap
double_tap_interval_ms = 300      # Max time between taps (ms)

[model]
name = "whisper-tiny-mlx"         # Model name (matches directory in models/)
device = "auto"                   # Unused — MLX auto-selects

[audio]
sample_rate = 16000               # Audio sample rate (Hz)
channels = 1                      # Mono recording
```

---

## Files and Directories

### Install Directory (`~/.apple-murmur/`)

| Path | Purpose |
|------|---------|
| `murmur/` | Source code (copied from repo) |
| `models/whisper-tiny-mlx/` | Whisper model files (~75MB) |
| `models/domain.klm` | KenLM language model (optional) |
| `config.toml` | User configuration (optional) |
| `murmur.pid` | PID of running daemon |
| `murmur.log` | Daemon log file |
| `venv/` | Python virtual environment |

### Log File

The daemon logs to `~/.apple-murmur/murmur.log`. Useful for debugging:

```bash
tail -f ~/.apple-murmur/murmur.log
```

You'll see entries like:
```
2024-01-15 10:30:45 INFO murmur.daemon: Recording started
2024-01-15 10:30:48 INFO murmur.daemon: Recording stopped (3.2s)
2024-01-15 10:30:48 INFO murmur.daemon: Transcribed [terminal]: 'git status'
```

---

## Troubleshooting

### murmur won't start

- Check `murmur status` — it might already be running
- Check the log: `tail -20 ~/.apple-murmur/murmur.log`
- Make sure you're on Apple Silicon: `uname -m` should say `arm64`

### Hotkey doesn't work

- Grant Accessibility permission: System Settings → Privacy & Security → Accessibility
- Add your terminal app and enable it
- Restart murmur after granting permission

### Transcription is inaccurate

- Speak clearly at a normal pace
- In terminal mode, pause briefly between words — this helps Whisper
- Check if the word is in the vocabulary list (`murmur/vocabulary.py`)
- Background noise? The noise reduction step handles moderate noise, but very noisy environments will reduce accuracy

### Text appears in wrong place

- The text is pasted at wherever your cursor currently is
- If you switch apps between starting and stopping recording, the text goes to the new app
- Profile selection happens at transcription time, not recording start

### Clipboard contents lost

- apple-murmur saves and restores your clipboard. If restoration fails, the last transcribed text will be in your clipboard instead of your previous content. This is rare.

---

## Performance

| What | How Fast |
|------|----------|
| 10 seconds of speech | ~150ms to transcribe |
| First model load | ~300ms (one-time per daemon start) |
| Memory usage | ~120MB |
| Power draw | Low — uses Neural Engine, not GPU |

Compared to the cross-platform `murmur` (PyTorch): ~3x faster transcription, ~2.5x less memory, lower power draw.

---

## Privacy

- **No network calls.** All transcription happens on-device using the Neural Engine.
- **No data stored.** Audio is discarded immediately after transcription.
- **No API keys.** No cloud accounts, no subscriptions.
- **Clipboard restored.** Previous clipboard contents are put back after injection.
- **Open source.** Every line of code is on GitHub.

---

## Updating

```bash
murmur update
```

This stops the daemon, pulls the latest code, reinstalls dependencies, and restarts the daemon.

Or manually:
```bash
murmur stop
cd ~/.apple-murmur && git pull
murmur start
```

---

## Claude Code Integration

If you have Claude Code installed, the installer adds a `/voice` command. Type `/voice` in Claude Code to start the murmur daemon and begin dictating.

---

## Project Links

- **apple-murmur (this project):** [github.com/amateur-ai-dev/apple-murmur](https://github.com/amateur-ai-dev/apple-murmur)
- **murmur (cross-platform):** [github.com/amateur-ai-dev/murmur](https://github.com/amateur-ai-dev/murmur)
