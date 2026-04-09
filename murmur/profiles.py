"""
Application profiles that shape the preprocessing and normalisation pipeline.

Each Profile declares which pipeline steps run and any extra post-normalisation
rules specific to that context. Adding a new app profile requires only a new
Profile() declaration here — no changes to the pipeline code.
"""
import re
from dataclasses import dataclass, field

# Internal placeholder used to protect explicit "space" tokens across
# prefix-collapse so they survive as real spaces in the final output.
_SPACE_MARKER = "\x01"

# Characters that act as prefixes in terminal commands — never have a trailing
# space in valid syntax (e.g. /compact, ~/projects, $HOME).
_PREFIX_CHARS = r'[/~$]'


@dataclass
class Profile:
    name: str
    skip_vad: bool                  # skip WebRTC VAD silence stripping
    extra_rules: list = field(default_factory=list)   # (compiled_re, replacement)


# Terminal extra rules — applied in order after base normalisation:
#   1. Protect explicit spoken "space" before collapse so it survives
#   2. Collapse whitespace immediately after a prefix character (/, ~, $)
#   3. Restore protected spaces as real spaces
_TERMINAL_EXTRA = [
    (re.compile(r'\bspace\b', re.IGNORECASE),   _SPACE_MARKER),
    (re.compile(r'(?<=' + _PREFIX_CHARS + r')[ \t]+'), ''),
    (re.compile(re.escape(_SPACE_MARKER)),       ' '),
]

DEFAULT_PROFILE = Profile(name="default", skip_vad=False)
TERMINAL_PROFILE = Profile(name="terminal", skip_vad=True, extra_rules=_TERMINAL_EXTRA)
