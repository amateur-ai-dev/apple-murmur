# apple-murmur

Apple Silicon-native system-wide voice-to-text. Double-tap **Left Control**, speak, text appears wherever your cursor is — in any app, any text field. Uses Apple's Neural Engine via MLX for near-instant transcription (~150ms).

> For cross-platform use (Intel Mac, Linux, Windows), see [murmur](https://github.com/amateur-ai-dev/murmur).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/apple-murmur/main/install.sh | bash
```

Requires Apple Silicon (M1/M2/M3/M4). No compilation step. Downloads model (~75MB) on first install.

## Usage

```bash
murmur start     # start the daemon
murmur stop      # stop the daemon
murmur status    # check if running
murmur update    # pull latest version
```

**Recording:** Double-tap **Left Control** (`ctrl_l`) to start. Double-tap again to stop and transcribe. There is no silence-based auto-stop — recording continues until you explicitly tap again.

> **Hotkey note:** `fn` is not used — macOS reserves it for the emoji picker. The default is Left Control. Override in `~/.apple-murmur/config.toml`:
> ```toml
> [hotkey]
> key = "ctrl_l"   # ctrl_l | ctrl_r | alt_r | cmd
> ```

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13 Ventura or later
- Python 3.9+
- Accessibility permission (prompted at install)

## How it works

```
Hotkey (ctrl_l ×2 to start, ctrl_l ×2 to stop)
    → Audio capture (sounddevice, 16kHz)
    → Profile selection (terminal app? → TERMINAL_PROFILE : DEFAULT_PROFILE)
    → Preprocessing (noisereduce → volume normalise → VAD silence strip*)
    → Whisper tiny (MLX, Apple Neural Engine, temperature=0)
    → Normalizer (spoken symbols → characters + profile extra rules)
    → Vocabulary correction (CLI tools, IT terms, Indian names via rapidfuzz + optional KenLM)
    → Text injection (clipboard paste, any app)

* VAD stripping is skipped in TERMINAL_PROFILE
```

- **Profile system** — pipeline behaviour is selected per active app. Two built-in profiles: `default` (prose/dictation) and `terminal` (command-optimised). New profiles require only a `Profile()` declaration in `murmur/profiles.py`.
- **Engine** — Whisper tiny on the Neural Engine via MLX; initial prompt biases toward CLI tools, IT terms, and Indian names
- **Preprocessing** — noise reduction, volume normalisation, and (in default mode) VAD-based silence stripping before inference
- **Normalizer** — converts spoken symbols to characters (`dash dash` → `--`, `pipe` → `|`, `slash` → `/`, and 40+ more); profile extra rules applied after base normalisation
- **Vocabulary correction** — fuzzy-matches against CLI tools, IT managed services terms, and Indian names (rapidfuzz threshold 88); optionally validated by a KenLM domain language model
- **Hotkey** — Left Control double-tap, global capture via pynput
- **Injection** — clipboard paste into any focused text field, system-wide

No data leaves your machine. No API keys. No subscriptions.

## App Profiles

The pipeline automatically detects which app is in focus at the moment of transcription and selects the appropriate profile.

### default
Used in all non-terminal apps (browsers, email, documents, etc.).

- VAD silence stripping runs — removes silent gaps to produce clean flowing text
- No prefix collapsing
- Output: natural prose with standard spacing

### terminal
Used when the frontmost app is a known terminal emulator (Terminal, iTerm2, Warp, Alacritty, Kitty, Ghostty, VS Code integrated terminal, Cursor terminal).

- VAD stripping **skipped** — natural pauses between words are preserved so Whisper spaces command tokens correctly
- Prefix collapse — spaces immediately after `/`, `~`, `$` are removed (e.g. `slash compact` → `/compact`, `dollar HOME` → `$HOME`)
- Explicit **"space"** token — saying the word "space" inserts a literal space that survives prefix collapse (e.g. `slash space compact` → `/ compact`)

### Adding new profiles
To add a profile for a specific app, declare a new `Profile` in `murmur/profiles.py` and add its bundle ID to the selection logic in `daemon.py`. No changes to the pipeline code required.

## Spoken Symbols

Speak CLI symbols by name — they are converted automatically.

### Multi-character operators

| Say | Gets | Say | Gets |
|---|---|---|---|
| `dash dash verbose` | `--verbose` | `double equals` | `==` |
| `double ampersand` | `&&` | `double pipe` | `\|\|` |
| `double greater than` | `>>` | `double less than` | `<<` |
| `right shift` | `>>` | `left shift` | `<<` |
| `append` | `>>` | `double colon` | `::` |
| `fat arrow` | `=>` | `right arrow` | `->` |
| `left arrow` | `<-` | `triple dot` | `...` |
| `ellipsis` | `...` | `double dot` | `..` |

### Comparison operators

| Say | Gets | Say | Gets |
|---|---|---|---|
| `not equal` | `!=` | `not equal to` | `!=` |
| `less than or equal` | `<=` | `greater than or equal` | `>=` |
| `less than or equal to` | `<=` | `greater than or equal to` | `>=` |

### Single-character symbols

| Say | Gets | Say | Gets |
|---|---|---|---|
| `slash` | `/` | `backslash` | `\` |
| `pipe` | `\|` | `greater than` | `>` |
| `less than` | `<` | `tilde` | `~` |
| `dash` / `minus` / `hyphen` | `-` | `asterisk` / `star` / `times` | `*` |
| `dollar` / `dollar sign` | `$` | `bang` / `exclamation` | `!` |
| `caret` / `hat` | `^` | `backtick` / `tick` / `grave` | `` ` `` |
| `semicolon` | `;` | `colon` | `:` |
| `equals` / `equals sign` | `=` | `question mark` | `?` |
| `at sign` / `at the rate` | `@` | `hash` / `pound` / `hashtag` | `#` |
| `percent` | `%` | `ampersand` | `&` |
| `plus` / `plus sign` | `+` | `underscore` | `_` |
| `comma` | `,` | `period` / `full stop` | `.` |
| `single quote` / `apostrophe` | `'` | `double quote` / `open quote` | `"` |

### Brackets and braces

| Say | Gets | Say | Gets |
|---|---|---|---|
| `open paren` | `(` | `close paren` | `)` |
| `open bracket` / `open square` | `[` | `close bracket` / `close square` | `]` |
| `open brace` / `open curly` | `{` | `close brace` / `close curly` | `}` |
| `open angle` / `open chevron` | `<` | `close angle` / `close chevron` | `>` |

### Terminal-specific (TERMINAL_PROFILE only)

| Say | Gets | Notes |
|---|---|---|
| `slash compact` | `/compact` | prefix collapse |
| `tilde slash projects` | `~/projects` | tilde + slash + word |
| `dollar HOME` | `$HOME` | prefix collapse |
| `slash space compact` | `/ compact` | explicit space preserved |

### URL domains

| Say | Gets |
|---|---|
| `dot com` | `.com` |
| `dot net` / `dot org` / `dot io` / `dot ai` | `.net` / `.org` / `.io` / `.ai` |

## Vocabulary Correction

The transcription pipeline corrects misheard words in three domains:

**CLI tools and shell** — git, docker, kubectl, npm, pip, brew, ssh, terraform, ansible, helm, vim, tmux, curl, wget, rsync, ffmpeg, GitHub, GitLab, and 60+ more. Common mishearings are caught by rapidfuzz at threshold 88.

**IT managed services** — ITSM, ITIL, ServiceNow, Jira, SLA, MTTR, Kubernetes, Azure, AWS, GCP, Datadog, and the full IT ops vocabulary.

**Indian names** — ~70 common first names (Rahul, Priya, Arjun, Nithin, …) and ~50 surnames (Sharma, Patel, Reddy, Nair, Krishnan, …) for accurate transcription in any context.

An optional KenLM domain language model (built at install time when `lmplz` is available) improves multi-candidate selection using sentence-level log-probability.

## Whisper CLI Command Fixes

Whisper has two well-known quirks with terminal commands that are automatically corrected:

**Abbreviation expansion** — Whisper transcribes short commands as initials: `rm` → `R.M.`, `ls` → `L.S.`, `git` → `G.I.T.`. The `_deabbreviate()` step collapses these back to lowercase before any other processing.

**Flag joining** — Whisper sometimes outputs `rm-rf` instead of `rm -rf`. The `_fix_joined_flags()` step detects short-command + hyphen + flag patterns and reinserts the space.

## Performance vs murmur

| | apple-murmur (MLX) | murmur (PyTorch) |
|---|---|---|
| 10s audio latency | ~150ms | ~500ms |
| Model load (first run) | ~300ms | ~800ms |
| Memory | ~120MB | ~300MB |
| Power draw | Low (ANE) | Medium (MPS) |
| Platform | Apple Silicon only | Cross-platform |

## Update

```bash
murmur update
```

## License

MIT
