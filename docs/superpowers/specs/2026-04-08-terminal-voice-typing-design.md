# Terminal Voice Typing — Design Spec

**Date:** 2026-04-08
**Status:** Approved

## Overview

Enable apple-murmur to recognise spoken terminal commands and symbols when the active window is a terminal emulator. Outside a terminal, existing behaviour (IT vocabulary, punctuation normalisation) is unchanged.

The user speaks explicitly — "dash", "pipe", "quote X quote" — and the system converts these to the correct characters before injection.

---

## Architecture & Data Flow

Profile is captured once at recording start (double-tap) so both the Whisper initial prompt and post-processing rules are consistent for the entire utterance.

```
double-tap detected
      │
      ▼
platform.get_profile()  ──→  "terminal" | "default"
      │                       stored as daemon._profile
      ▼
audio recording
      │
      ▼
engine.transcribe(audio, profile)  ──→  selects initial_prompt by profile
      │
      ▼
normalize(text, profile)  ──→  applies terminal symbol rules OR default rules
      │
      ▼
vocabulary.correct(text, profile)  ──→  terminal command vocab OR IT vocab
      │
      ▼
injector.inject(text)
```

---

## Files

| File | Change |
|---|---|
| `murmur/platform.py` | New — active app detection via AppleScript |
| `murmur/daemon.py` | Capture profile at recording start; pass to engine + normalize |
| `murmur/engine.py` | Two initial prompts (`_INITIAL_PROMPTS` dict), selected by profile |
| `murmur/normalizer.py` | `normalize(text, profile="default")` — terminal symbol ruleset added |
| `murmur/vocabulary.py` | `correct(text, profile="default")` — terminal command vocab added |
| `tests/test_platform.py` | New — unit tests for bundle detection and profile logic |
| `tests/test_normalizer.py` | New — terminal rule tests |
| `tests/test_vocabulary.py` | Extend — terminal profile tests |

---

## `platform.py` — Active App Detection

Uses `osascript` (no new dependencies) to get the frontmost app's bundle ID. Failures return `""` which maps to `"default"` profile.

```python
TERMINAL_BUNDLES = {
    "com.apple.Terminal",
    "com.googlecode.iterm2",
    "dev.warp.desktop",
    "io.alacritty",
    "net.kovidgoyal.kitty",
    "com.mitchellh.ghostty",
}

def get_active_bundle() -> str: ...   # osascript, 0.5s timeout
def is_terminal() -> bool: ...        # bundle in TERMINAL_BUNDLES
def get_profile() -> str: ...         # "terminal" | "default"
```

---

## Terminal Symbol Rules (`normalizer.py`)

Applied only when `profile="terminal"`. Longer / paired patterns come first. Default URL rules (`dot com` → `.com` etc.) are also included in terminal mode.

| Say | Output | Notes |
|---|---|---|
| `double dash` | `--` | before "dash" |
| `dash` | `-` | |
| `quote X quote` | `"X"` | paired, greedy-but-lazy |
| `single quote X single quote` | `'X'` | paired |
| `quote` | `"` | unmatched fallback |
| `single quote` | `'` | unmatched fallback |
| `pipe` | `\|` | |
| `and and` | `&&` | |
| `or or` | `\|\|` | |
| `double pipe` | `\|\|` | |
| `append` | `>>` | |
| `double greater than` | `>>` | |
| `greater than` | `>` | |
| `less than` | `<` | |
| `tilde` | `~` | |
| `slash` | `/` | |
| `backslash` | `\` | |
| `dot dot` | `..` | before "dot" |
| `dot` | `.` | |
| `star` | `*` | |
| `asterisk` | `*` | |
| `dollar` | `$` | |
| `equals` | `=` | |
| `semicolon` | `;` | |
| `bang` | `!` | |
| `exclamation` | `!` | |
| `backtick` | `` ` `` | |
| `caret` | `^` | |
| `percent` | `%` | |
| `at the rate` | `@` | before "at sign" |
| `at sign` | `@` | |
| `ampersand` | `&` | |
| `new line` / `newline` | `\n` | same as default |

---

## Terminal Vocabulary (`vocabulary.py`)

`_TERMINAL_VOCAB` replaces `_IT_VOCAB` when `profile="terminal"`. Case-insensitive matching (already fixed in vocabulary corrector) applies.

Categories:

- **Shells & runtimes:** `bash`, `zsh`, `fish`, `python3`, `node`, `ruby`, `go`, `rustc`, `java`, `swift`, `perl`, `php`
- **Core unix:** `ls`, `cd`, `grep`, `find`, `awk`, `sed`, `chmod`, `chown`, `xargs`, `curl`, `wget`, `ssh`, `rsync`, `tar`, `diff`, `kill`, `ps`, `df`, `du`, `wc`, `sort`, `uniq`, `tr`, `cut`, `touch`, `mkdir`, `rmdir`, `echo`, `cat`, `less`, `head`, `tail`, `ln`, `cp`, `mv`, `rm`, `which`, `env`, `export`, `source`, `history`, `man`, `lsof`, `ping`
- **Git:** `git`, `clone`, `commit`, `rebase`, `checkout`, `stash`, `bisect`, `reflog`, `cherry-pick`, `fetch`, `merge`, `push`, `pull`, `branch`, `diff`, `log`, `tag`, `blame`
- **Docker / Kubernetes:** `docker`, `kubectl`, `helm`, `Dockerfile`, `namespace`, `configmap`, `ingress`, `compose`
- **Package managers:** `npm`, `yarn`, `pnpm`, `pip3`, `brew`, `cargo`, `gem`, `gradle`, `maven`
- **Tools:** `vim`, `nvim`, `nano`, `tmux`, `jq`, `fzf`, `make`, `cmake`, `gcc`, `clang`

---

## Engine Initial Prompts (`engine.py`)

```python
_INITIAL_PROMPTS = {
    "default": "IT managed services, ITSM, ITIL, ServiceNow, incident management, change request, SLA, MTTR, infrastructure, Azure, AWS, Active Directory, VPN, endpoint, helpdesk, L1 L2 L3 support, Kubernetes, CI/CD, DevOps, Harness, Terraform, Ansible, Jenkins, GitLab, GitHub Actions",
    "terminal": (
        "terminal commands: git commit -m, grep -r, kubectl apply -f, "
        "docker run --rm, pip install, npm install, ls -la, chmod 755, "
        "ssh user@host, curl --header, find . -name, awk '{print $1}', "
        "bash zsh python3 node ruby go rustc"
    ),
}
```

`engine.transcribe(audio, profile="default")` selects the prompt from this dict.

---

## Daemon Change (`daemon.py`)

`on_double_tap` captures the profile once at recording start:

```python
if self.state == "idle":
    self._profile = get_profile()   # single osascript call
    self.state = "recording"
    self.audio.start()
```

`_transcribe` passes `self._profile` to `engine.transcribe()` and `normalize()`. No other daemon logic changes. `_profile` defaults to `"default"` at `__init__`.

---

## Error Handling

- `osascript` failure (timeout, permission denied) → `get_active_bundle()` returns `""` → profile falls back to `"default"`. No crash, no visible effect.
- Unknown terminal emulator → add its bundle ID to `TERMINAL_BUNDLES` in `platform.py`.

---

## Testing

- `test_platform.py`: mock `subprocess.run` to return known bundle IDs; verify `is_terminal()` and `get_profile()`.
- `test_normalizer.py`: parametrised tests for every spoken→symbol mapping in both profiles; verify default profile is unaffected by terminal rules.
- `test_vocabulary.py`: verify terminal vocab matches (`grep`, `kubectl`, etc.) and IT vocab still corrects in default profile.
