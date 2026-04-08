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

Or from Claude Code: `/voice`

**Recording:** Double-tap **Left Control** (`ctrl_l`) to start. Double-tap again to stop and transcribe. There is no silence-based auto-stop — recording continues until you explicitly tap again.

> **Hotkey note:** `fn` is not used — macOS reserves it for the emoji picker. The default is Left Control. Override in `~/.apple-murmur/config.toml` if needed:
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
    → Preprocessing (noisereduce → volume normalise → VAD silence strip)
    → Whisper tiny (MLX, Apple Neural Engine, beam=3, temperature=0)
    → Normalizer (spoken symbols → characters)
    → Vocabulary correction (CLI, IT, Indian names via rapidfuzz + optional KenLM)
    → Text injection (clipboard paste, any app)
```

- **Engine** — Whisper tiny on the Neural Engine via MLX; initial prompt biases toward CLI tools, IT terms, and Indian names
- **Preprocessing** — noise reduction, volume normalisation, and VAD-based silence stripping before inference
- **Normalizer** — converts spoken symbols to characters (`dash dash` → `--`, `pipe` → `|`, `greater than` → `>`, `at the rate` → `@`, and 30+ more)
- **Vocabulary correction** — fuzzy-matches against CLI tools, IT managed services terms, and Indian names (rapidfuzz threshold 88); optionally validated by a KenLM domain language model
- **Hotkey** — Left Control double-tap, global capture via pynput
- **Injection** — clipboard paste into any focused text field, system-wide

No data leaves your machine. No API keys. No subscriptions.

## Spoken Symbols

Speak CLI symbols by name — they are converted automatically:

| Say | Gets | Say | Gets |
|---|---|---|---|
| `dash dash verbose` | `--verbose` | `pipe` | `\|` |
| `dash f` | `-f` | `greater than` | `>` |
| `double pipe` | `\|\|` | `less than` | `<` |
| `double ampersand` | `&&` | `semicolon` | `;` |
| `fat arrow` | `=>` | `tilde` | `~` |
| `right arrow` | `->` | `dollar sign` | `$` |
| `double colon` | `::` | `backtick` | `` ` `` |
| `double equals` | `==` | `bang` | `!` |
| `at the rate` | `@` | `caret` | `^` |
| `double greater than` | `>>` | `asterisk` | `*` |
| `single quote` | `'` | `double quote` | `"` |
| `triple dot` | `...` | `ellipsis` | `...` |

Existing spoken-punctuation rules (`at sign`, `open paren`, `forward slash`, `hashtag`, `underscore`, `ampersand`, …) are also supported.

## Vocabulary Correction

The transcription pipeline corrects misheard words in three domains:

**CLI tools and shell** — git, docker, kubectl, npm, pip, brew, ssh, terraform, ansible, kubectl, helm, vim, tmux, GitHub, GitLab, and 60+ more. Common mishearings (e.g. "cud get curl" → `kubectl`) are caught by rapidfuzz at threshold 88.

**IT managed services** — ITSM, ITIL, ServiceNow, Jira, SLA, MTTR, Kubernetes, Azure, AWS, Datadog, and the full IT ops vocabulary from v2.

**Indian names** — ~70 common first names (Rahul, Priya, Arjun, Nithin, Sharma, …) and ~50 surnames (Sharma, Patel, Reddy, Nair, Krishnan, …) for accurate transcription of Indian names in any context.

An optional KenLM domain language model (built at install time when `lmplz` is available) improves multi-candidate selection using sentence-level log-probability.

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
