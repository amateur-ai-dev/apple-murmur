# apple-murmur

Apple Silicon-native system-wide voice-to-text. Double-tap `fn`, speak, text appears wherever your cursor is — in any app, any text field. Uses Apple's Neural Engine via MLX for near-instant transcription (~150ms).

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

**Recording:** Double-tap `fn` to start, double-tap again to stop. Text injects at cursor.

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13 Ventura or later
- Python 3.9+
- Accessibility permission (prompted at install)

## How it works

- **Engine** — OpenAI Whisper tiny model, runs on Apple Neural Engine via MLX framework
- **Daemon** — background process, listens for fn double-tap globally via pynput
- **CLI** — `murmur start/stop/status/update`

No data leaves your machine. No API keys. No subscriptions.

## Performance vs murmur

| | apple-murmur (MLX) | murmur (PyTorch) |
|---|---|---|
| 10s audio latency | ~150ms | ~500ms |
| Memory | ~120MB | ~300MB |
| Power draw | Low | Medium |
| Platform | Apple Silicon only | Cross-platform |

## Update

```bash
murmur update
```

## License

MIT
