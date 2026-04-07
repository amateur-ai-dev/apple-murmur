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

**Recording:** Double-tap **Left Control** (`ctrl_l`) to start. Stop either by double-tapping again, or just pause — the daemon auto-stops after ~1s of silence.

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
Hotkey (ctrl_l ×2)
    → Audio capture (sounddevice, 16kHz, webrtcvad auto-stop)
    → Preprocessing (noisereduce → volume normalise → VAD silence strip)
    → Whisper tiny (MLX, Apple Neural Engine, beam=3, temperature=0)
    → Normalizer (spoken punctuation → symbols)
    → Vocabulary correction (IT domain terms via rapidfuzz + optional KenLM)
    → Text injection (clipboard paste, any app)
```

- **Engine** — Whisper tiny on the Neural Engine via MLX; IT-biased initial prompt improves jargon accuracy
- **Preprocessing** — noise reduction, volume normalisation, and VAD-based silence stripping before inference
- **Vocabulary correction** — fuzzy-matches against an IT managed services vocabulary (ITSM, Kubernetes, SLA, MTTR, …); optionally validated by a KenLM domain language model
- **Hotkey** — Left Control double-tap, global capture via pynput
- **Injection** — clipboard paste into any focused text field, system-wide

No data leaves your machine. No API keys. No subscriptions.

## IT Domain Vocabulary

The transcription pipeline is tuned for IT managed services speech. Common terms that Whisper may mishear are corrected post-transcription:

> "servise now" → **ServiceNow** · "kubernetes" → **Kubernetes** · "MTBR" → **MTBF** · "itsim" → **ITSM**

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
