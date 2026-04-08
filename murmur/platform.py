import logging
import subprocess

logger = logging.getLogger(__name__)

TERMINAL_BUNDLES = {
    "com.apple.Terminal",
    "com.googlecode.iterm2",
    "dev.warp.desktop",
    "io.alacritty",
    "net.kovidgoyal.kitty",
    "com.mitchellh.ghostty",
}

_OSASCRIPT = (
    'tell application "System Events" to bundle identifier of '
    '(first application process whose frontmost is true)'
)


def get_active_bundle() -> str:
    """Return bundle ID of frontmost app, or '' on any failure."""
    try:
        result = subprocess.run(
            ["osascript", "-e", _OSASCRIPT],
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        return result.stdout.strip()
    except Exception as exc:
        logger.debug("get_active_bundle failed: %s", exc)
        return ""


def is_terminal() -> bool:
    """Return True if the frontmost app is a known terminal emulator."""
    return get_active_bundle() in TERMINAL_BUNDLES


def get_profile() -> str:
    """Return 'terminal' if the frontmost app is a known terminal emulator, else 'default'."""
    return "terminal" if is_terminal() else "default"
