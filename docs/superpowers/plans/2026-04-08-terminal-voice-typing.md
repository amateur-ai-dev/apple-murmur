# Terminal Voice Typing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add profile-based normalisation so spoken terminal symbols and commands are converted correctly when a terminal emulator is the active window, while leaving all other apps unchanged.

**Architecture:** A new `platform.py` module detects the active app at recording start and returns `"terminal"` or `"default"`. This profile is threaded through `engine.transcribe()` (selects initial prompt) and `normalize()` → `correct()` (selects symbol rules and vocabulary). The daemon captures the profile once on double-tap and stores it as `self._profile`.

**Tech Stack:** Python 3.9, `subprocess`/`osascript` for app detection, `rapidfuzz` for fuzzy vocab matching, `mlx_whisper`, `pytest`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `murmur/platform.py` | Create | Active app detection via AppleScript; `get_profile() -> str` |
| `murmur/vocabulary.py` | Modify | Add `_TERMINAL_VOCAB`; add `profile` param to `correct()` |
| `murmur/engine.py` | Modify | `_INITIAL_PROMPTS` dict; add `profile` param to `transcribe()` |
| `murmur/normalizer.py` | Modify | Add `_TERMINAL_RULES`; add `profile` param to `normalize()` |
| `murmur/daemon.py` | Modify | Capture `_profile` at recording start; pass to engine + normalize |
| `tests/test_platform.py` | Create | Unit tests for bundle detection and profile logic |
| `tests/test_normalizer.py` | Create | Parametrised tests for every terminal symbol mapping |
| `tests/test_vocabulary.py` | Extend | Terminal profile tests alongside existing IT vocab tests |
| `tests/test_daemon.py` | Extend | Verify `_profile` is captured and passed through |

---

## Task 1: `platform.py` — Active App Detection

**Files:**
- Create: `murmur/platform.py`
- Create: `tests/test_platform.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_platform.py`:

```python
import subprocess
from unittest.mock import patch, MagicMock


def _mock_run(bundle_id: str):
    """Return a mock subprocess.run result with the given bundle ID."""
    result = MagicMock()
    result.stdout = f"{bundle_id}\n"
    return result


def test_get_active_bundle_returns_stripped_bundle_id():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run", return_value=_mock_run("com.googlecode.iterm2")):
        assert get_active_bundle() == "com.googlecode.iterm2"


def test_get_active_bundle_returns_empty_on_timeout():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run",
               side_effect=subprocess.TimeoutExpired("osascript", 0.5)):
        assert get_active_bundle() == ""


def test_get_active_bundle_returns_empty_on_any_exception():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run", side_effect=OSError("no osascript")):
        assert get_active_bundle() == ""


def test_is_terminal_true_for_iterm2():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.googlecode.iterm2"):
        assert is_terminal() is True


def test_is_terminal_true_for_terminal_app():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.apple.Terminal"):
        assert is_terminal() is True


def test_is_terminal_false_for_chrome():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.google.Chrome"):
        assert is_terminal() is False


def test_is_terminal_false_for_empty_bundle():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value=""):
        assert is_terminal() is False


def test_get_profile_returns_terminal_when_in_terminal():
    from murmur.platform import get_profile
    with patch("murmur.platform.is_terminal", return_value=True):
        assert get_profile() == "terminal"


def test_get_profile_returns_default_when_not_in_terminal():
    from murmur.platform import get_profile
    with patch("murmur.platform.is_terminal", return_value=False):
        assert get_profile() == "default"
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_platform.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'murmur.platform'`

- [ ] **Step 3: Create `murmur/platform.py`**

```python
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
    return get_active_bundle() in TERMINAL_BUNDLES


def get_profile() -> str:
    """Return 'terminal' if the frontmost app is a known terminal emulator, else 'default'."""
    return "terminal" if is_terminal() else "default"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_platform.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
cd ~/.apple-murmur
git add murmur/platform.py tests/test_platform.py
git commit -m "feat: platform module for active app detection and profile selection"
```

---

## Task 2: Terminal Vocabulary in `vocabulary.py`

**Files:**
- Modify: `murmur/vocabulary.py`
- Modify: `tests/test_vocabulary.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_vocabulary.py`:

```python
# ---------------------------------------------------------------------------
# Terminal profile
# ---------------------------------------------------------------------------

def test_correct_terminal_profile_matches_kubectl():
    """'kubctl' is close enough to 'kubectl' — should be corrected in terminal mode."""
    from murmur.vocabulary import correct
    # Use the real fuzzy matcher; kubectl is in _TERMINAL_VOCAB
    with patch("murmur.kenlm_rescorer.has_model", return_value=False):
        result = correct("kubctl", profile="terminal")
    assert result == "kubectl"


def test_correct_terminal_profile_matches_chmod():
    from murmur.vocabulary import correct
    with patch("murmur.kenlm_rescorer.has_model", return_value=False):
        result = correct("cmod", profile="terminal")
    assert result == "chmod"


def test_correct_default_profile_does_not_use_terminal_vocab():
    """In default mode, 'kubectl' is not in _VOCAB so 'kubctl' stays uncorrected."""
    from murmur.vocabulary import correct
    with patch("murmur.kenlm_rescorer.has_model", return_value=False):
        result = correct("kubctl", profile="default")
    assert result == "kubctl"


def test_correct_default_profile_still_corrects_it_terms():
    """Existing IT vocab correction must be unaffected by the profile addition."""
    from murmur.vocabulary import _correct  # re-use existing helper via direct import
    result = _correct("incedent", candidates=[("incident", 95)])
    assert result == "incident"
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_vocabulary.py::test_correct_terminal_profile_matches_kubectl -v
```

Expected: `FAILED` — `TypeError: correct() got an unexpected keyword argument 'profile'`

- [ ] **Step 3: Update `murmur/vocabulary.py`**

Replace the entire file:

```python
"""
IT managed services and terminal domain vocabulary correction.
Uses rapidfuzz for fuzzy matching; KenLM (when available) validates candidates
in context before committing a substitution.
"""
from rapidfuzz import process, fuzz

# Single-word domain terms only — multi-word phrases handled by normalizer regex
_VOCAB = [
    # ITSM frameworks & tools
    "ITIL", "ITSM", "ServiceNow", "Jira", "Confluence", "Remedy", "Zendesk",
    # Incident & change management
    "incident", "escalation", "triage", "workaround", "hotfix", "rollback",
    "SLA", "SLO", "SLI", "MTTR", "MTBF", "CMDB", "runbook",
    # Support tiers
    "helpdesk", "L1", "L2", "L3",
    # Infrastructure & virtualisation
    "hypervisor", "VMware", "vSphere", "vCenter", "Hyper-V", "KVM",
    "Kubernetes", "Docker", "container", "microservice",
    "Azure", "AWS", "GCP", "EC2", "S3",
    # Security
    "LDAP", "SSO", "MFA", "VPN", "endpoint", "firewall", "WAF",
    "SIEM", "SOC", "CVE", "pentest",
    # Monitoring & observability
    "Datadog", "Grafana", "Prometheus", "PagerDuty", "OpsGenie", "APM",
    # Backup & DR
    "failover", "failback", "RTO", "RPO",
    # Networking
    "VLAN", "subnet", "BGP", "OSPF", "latency", "throughput", "bandwidth",
    # Auth & integration
    "OAuth", "SAML", "webhook", "middleware",
    # DevOps & CI/CD
    "deployment", "DevOps", "DevSecOps", "pipeline",
    "Harness", "Terraform", "Ansible", "Jenkins", "GitLab",
    # General
    "authentication", "authorization", "monitoring", "alerting", "observability",
    "virtualization", "containerization", "orchestration",
]

_TERMINAL_VOCAB = [
    # Shells & runtimes
    "bash", "zsh", "fish", "python3", "rustc", "swift", "perl",
    # Core unix — include terms Whisper is likely to mishear
    "chmod", "chown", "rsync", "xargs", "lsof", "grep", "awk", "sed",
    "curl", "wget", "ssh", "tar", "diff",
    # Git
    "git", "rebase", "stash", "bisect", "reflog",
    # Docker / Kubernetes
    "docker", "kubectl", "helm", "Dockerfile", "configmap", "ingress",
    # Package managers
    "npm", "yarn", "pnpm", "pip3", "brew", "cargo", "gradle", "maven",
    # Tools
    "nvim", "tmux", "jq", "fzf", "cmake", "clang",
]

# Only substitute if similarity is at or above this threshold
_THRESHOLD = 88

# Case-insensitive lookup: lowercase → canonical cased form (e.g. "harness" → "Harness")
_VOCAB_LOWER = [v.lower() for v in _VOCAB]
_VOCAB_CANONICAL = {v.lower(): v for v in _VOCAB}

_TERMINAL_VOCAB_LOWER = [v.lower() for v in _TERMINAL_VOCAB]
_TERMINAL_VOCAB_CANONICAL = {v.lower(): v for v in _TERMINAL_VOCAB}


def correct(text: str, profile: str = "default") -> str:
    """
    Correct domain terminology in text.
    profile="terminal" uses terminal command vocabulary instead of IT vocabulary.
    Matching is case-insensitive so that e.g. "hardness" matches "Harness".
    When KenLM is available, a candidate is only applied if it improves the
    sentence-level log-probability; otherwise the best rapidfuzz match wins.
    """
    from murmur import kenlm_rescorer  # lazy to avoid circular import at module load

    if profile == "terminal":
        vocab = _TERMINAL_VOCAB
        vocab_lower = _TERMINAL_VOCAB_LOWER
        vocab_canonical = _TERMINAL_VOCAB_CANONICAL
    else:
        vocab = _VOCAB
        vocab_lower = _VOCAB_LOWER
        vocab_canonical = _VOCAB_CANONICAL

    words = text.split()
    use_lm = kenlm_rescorer.has_model()
    current_score = kenlm_rescorer.score(text) if use_lm else 0.0

    result = list(words)
    for i, word in enumerate(words):
        # Skip short tokens and already-matching terms
        if len(word) < 3 or word in vocab:
            continue

        candidates = process.extract(word.lower(), vocab_lower, scorer=fuzz.ratio, limit=3)
        eligible = [
            (vocab_canonical[w], s)
            for w, s, _ in candidates
            if s >= _THRESHOLD and vocab_canonical[w] != word
        ]
        if not eligible:
            continue

        if use_lm:
            best_word, best_delta = word, 0.0
            for candidate, _ in eligible:
                trial = result[:i] + [candidate] + result[i + 1:]
                trial_score = kenlm_rescorer.score(" ".join(trial))
                delta = trial_score - current_score
                if delta > best_delta:
                    best_delta, best_word = delta, candidate
            if best_word != word:
                result[i] = best_word
                current_score += best_delta
        else:
            result[i] = eligible[0][0]

    return " ".join(result)
```

- [ ] **Step 4: Run all vocabulary tests**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_vocabulary.py -v
```

Expected: all tests pass including the 4 new terminal profile tests.

- [ ] **Step 5: Commit**

```bash
cd ~/.apple-murmur
git add murmur/vocabulary.py tests/test_vocabulary.py
git commit -m "feat: terminal vocabulary profile in vocabulary corrector"
```

---

## Task 3: Profile-Aware Initial Prompts in `engine.py`

**Files:**
- Modify: `murmur/engine.py`
- Modify: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

Read `tests/test_engine.py` first, then append:

```python
def test_transcribe_uses_terminal_prompt_for_terminal_profile():
    """engine.transcribe() must pass the terminal initial_prompt when profile='terminal'."""
    from murmur.engine import Engine, _INITIAL_PROMPTS
    import numpy as np
    engine = Engine(model_name="whisper-tiny-mlx")
    silence = np.zeros(16000, dtype=np.float32)
    with patch("murmur.engine.mlx_whisper.transcribe", return_value={"text": ""}) as mock_t:
        engine.transcribe(silence, profile="terminal")
    _, kwargs = mock_t.call_args
    assert kwargs["initial_prompt"] == _INITIAL_PROMPTS["terminal"]


def test_transcribe_uses_default_prompt_when_no_profile_given():
    from murmur.engine import Engine, _INITIAL_PROMPTS
    import numpy as np
    engine = Engine(model_name="whisper-tiny-mlx")
    silence = np.zeros(16000, dtype=np.float32)
    with patch("murmur.engine.mlx_whisper.transcribe", return_value={"text": ""}) as mock_t:
        engine.transcribe(silence)
    _, kwargs = mock_t.call_args
    assert kwargs["initial_prompt"] == _INITIAL_PROMPTS["default"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_engine.py::test_transcribe_uses_terminal_prompt_for_terminal_profile -v
```

Expected: `FAILED` — `TypeError: transcribe() got an unexpected keyword argument 'profile'`

- [ ] **Step 3: Update `murmur/engine.py`**

Replace the entire file:

```python
import logging
from pathlib import Path

import mlx_whisper
import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = Path.home() / ".apple-murmur" / "models"

_INITIAL_PROMPTS = {
    "default": (
        "IT managed services, ITSM, ITIL, ServiceNow, incident management, "
        "change request, SLA, MTTR, infrastructure, Azure, AWS, Active Directory, "
        "VPN, endpoint, helpdesk, L1 L2 L3 support, Kubernetes, CI/CD, DevOps, "
        "Harness, Terraform, Ansible, Jenkins, GitLab, GitHub Actions"
    ),
    "terminal": (
        "terminal commands: git commit -m, grep -r, kubectl apply -f, "
        "docker run --rm, pip install, npm install, ls -la, chmod 755, "
        "ssh user@host, curl --header, find . -name, awk '{print $1}', "
        "bash zsh python3 node ruby go rustc"
    ),
}


class Engine:
    def __init__(self, model_name: str = "whisper-tiny-mlx", device=None):
        self.model_name = model_name
        self._model_path = str(_MODEL_DIR / model_name)
        logger.info("Engine initialised: model=%s path=%s", model_name, self._model_path)

    def load(self) -> None:
        logger.info("MLX engine ready (model loads lazily on first transcribe)")

    def transcribe(self, audio: np.ndarray, profile: str = "default") -> str:
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._model_path,
            temperature=0.0,
            condition_on_previous_text=True,
            initial_prompt=_INITIAL_PROMPTS.get(profile, _INITIAL_PROMPTS["default"]),
        )
        return result["text"].strip()
```

- [ ] **Step 4: Run engine tests**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_engine.py -v
```

Expected: all tests pass including the 2 new prompt tests.

- [ ] **Step 5: Commit**

```bash
cd ~/.apple-murmur
git add murmur/engine.py tests/test_engine.py
git commit -m "feat: profile-aware initial prompts in engine"
```

---

## Task 4: Terminal Symbol Rules in `normalizer.py`

**Files:**
- Modify: `murmur/normalizer.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_normalizer.py`:

```python
"""
Tests for normalize() — both default and terminal profiles.
correct() is patched to a no-op so we isolate the symbol rules.
"""
import pytest
from unittest.mock import patch


def _normalize(text: str, profile: str = "default") -> str:
    """Call normalize() with correct() neutralised."""
    from murmur.normalizer import normalize
    with patch("murmur.vocabulary.correct", side_effect=lambda t, profile="default": t):
        return normalize(text, profile=profile)


# ---------------------------------------------------------------------------
# Terminal symbol rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spoken,expected", [
    # Dashes
    ("double dash recursive",      "--recursive"),
    ("dash r",                     "-r"),
    ("dash dash verbose",          "--verbose"),
    # Pipe and redirection
    ("pipe grep foo",              "| grep foo"),
    ("greater than output.txt",    "> output.txt"),
    ("double greater than log",    ">> log"),
    ("append log",                 ">> log"),
    ("less than input.txt",        "< input.txt"),
    # Logical operators
    ("make build and and make test", "make build && make test"),
    ("true or or false",           "true || false"),
    ("true double pipe false",     "true || false"),
    # Paths
    ("tilde slash projects",       "~/projects"),
    ("dot dot slash src",          "../src"),
    ("dot gitignore",              ".gitignore"),
    # Glob / shell specials
    ("star dot py",                "*.py"),
    ("asterisk dot txt",           "*.txt"),
    ("dollar HOME",                "$HOME"),
    ("semicolon",                  ";"),
    ("bang",                       "!"),
    ("exclamation",                "!"),
    ("backtick",                   "`"),
    ("caret",                      "^"),
    ("percent",                    "%"),
    # Quotes — paired
    ("quote fix the bug quote",    '"fix the bug"'),
    ("single quote hello single quote", "'hello'"),
    # Quotes — unmatched fallback
    ("dash m quote",               '-m "'),
    # @ symbol
    ("at the rate gmail dot com",  "@gmail.com"),
    ("at sign gmail dot com",      "@gmail.com"),
    # Misc
    ("equals",                     "="),
    ("ampersand",                  "&"),
    ("backslash n",                "\\n"),
    ("slash usr slash local",      "/usr/local"),
])
def test_terminal_symbol(spoken, expected):
    assert _normalize(spoken, profile="terminal") == expected


# ---------------------------------------------------------------------------
# Default profile — terminal rules must NOT apply
# ---------------------------------------------------------------------------

def test_default_profile_does_not_convert_dash():
    assert _normalize("dash r f", profile="default") == "dash r f"


def test_default_profile_does_not_convert_pipe():
    assert _normalize("pipe grep", profile="default") == "pipe grep"


def test_default_profile_does_not_convert_tilde():
    assert _normalize("tilde slash home", profile="default") == "tilde slash home"


# ---------------------------------------------------------------------------
# URL rules work in both profiles
# ---------------------------------------------------------------------------

def test_url_dot_com_works_in_default():
    assert _normalize("github dot com", profile="default") == "github.com"


def test_url_dot_com_works_in_terminal():
    assert _normalize("github dot com", profile="terminal") == "github.com"
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_normalizer.py -v
```

Expected: `FAILED` — `TypeError: normalize() takes 1 positional argument but 2 were given` (or similar).

- [ ] **Step 3: Update `murmur/normalizer.py`**

Replace the entire file:

```python
"""
Post-processes Whisper transcriptions to handle spoken punctuation,
URLs, colloquial speech patterns, and terminal command syntax.
"""
import re

# Order matters — longer patterns before shorter ones.
# These rules apply in both profiles.
_RULES = [
    # URLs / domains
    (r'\bdot\s+com\b',  '.com'),
    (r'\bdot\s+net\b',  '.net'),
    (r'\bdot\s+org\b',  '.org'),
    (r'\bdot\s+io\b',   '.io'),
    (r'\bdot\s+ai\b',   '.ai'),
    (r'\bdot\s+edu\b',  '.edu'),
    (r'\bdot\s+gov\b',  '.gov'),
    (r'\bdot\s+co\b',   '.co'),

    # Punctuation names (spoken explicitly) — shared across all profiles
    (r'\bat sign\b',                '@'),
    (r'\bhash tag\b',               '#'),
    (r'\bhashtag\b',                '#'),
    (r'\bopen paren(?:thesis)?\b',  '('),
    (r'\bclose paren(?:thesis)?\b', ')'),
    (r'\bopen bracket\b',           '['),
    (r'\bclose bracket\b',          ']'),
    (r'\bopen brace\b',             '{'),
    (r'\bclose brace\b',            '}'),
    (r'\bforward slash\b',          '/'),
    (r'\bback slash\b',             '\\\\'),
    (r'\bunderscore\b',             '_'),
    (r'\bampersand\b',              '&'),
    (r'\bpercent sign\b',           '%'),
    (r'\bnew line\b',               '\n'),
    (r'\bnewline\b',                '\n'),
]

# Terminal-only rules — applied in addition to _RULES when profile="terminal".
# Longer / paired patterns must come before their shorter counterparts.
_TERMINAL_RULES = [
    # Paired quotes (before unmatched fallbacks)
    (r'\bquote\s+(.+?)\s+quote\b',               '"\\1"'),
    (r'\bsingle quote\s+(.+?)\s+single quote\b',  "'\\1'"),
    # Unmatched quote fallbacks
    (r'\bquote\b',         '"'),
    (r'\bsingle quote\b',  "'"),
    # Dashes — double before single
    (r'\bdouble dash\b',   '--'),
    (r'\bdash\b',          '-'),
    # Logical operators
    (r'\band and\b',        '&&'),
    (r'\bor or\b',          '||'),
    (r'\bdouble pipe\b',    '||'),
    # Redirection — longer patterns first
    (r'\bdouble greater than\b',  '>>'),
    (r'\bappend\b',               '>>'),
    (r'\bgreater than\b',         '>'),
    (r'\bless than\b',            '<'),
    # Pipe
    (r'\bpipe\b',  '|'),
    # Paths
    (r'\btilde\b',      '~'),
    (r'\bslash\b',      '/'),
    (r'\bbackslash\b',  '\\\\'),
    # Dots — double before single
    (r'\bdot dot\b',  '..'),
    (r'\bdot\b',      '.'),
    # Glob / regex
    (r'\bstar\b',      '*'),
    (r'\basterisk\b',  '*'),
    # Shell specials
    (r'\bdollar\b',       '$'),
    (r'\bequals\b',       '='),
    (r'\bsemicolon\b',    ';'),
    (r'\bbang\b',         '!'),
    (r'\bexclamation\b',  '!'),
    (r'\bbacktick\b',     '`'),
    (r'\bcaret\b',        '^'),
    (r'\bpercent\b',      '%'),
    # @ — longer phrases first
    (r'\bat the rate\b',  '@'),
    (r'\bat sign\b',      '@'),
    # Misc
    (r'\bampersand\b',  '&'),
    (r'\bnew line\b',   '\n'),
    (r'\bnewline\b',    '\n'),
]

_COMPILED_DEFAULT  = [(re.compile(p, re.IGNORECASE), r) for p, r in _RULES]
_COMPILED_TERMINAL = [(re.compile(p, re.IGNORECASE), r) for p, r in _TERMINAL_RULES + _RULES]


def normalize(text: str, profile: str = "default") -> str:
    rules = _COMPILED_TERMINAL if profile == "terminal" else _COMPILED_DEFAULT
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    from murmur.vocabulary import correct  # lazy to avoid circular import at module load
    return correct(text, profile=profile)
```

- [ ] **Step 4: Run normalizer tests**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_normalizer.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run full suite to check nothing regressed**

```bash
~/.apple-murmur/venv/bin/pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd ~/.apple-murmur
git add murmur/normalizer.py tests/test_normalizer.py
git commit -m "feat: terminal symbol rules in normalizer"
```

---

## Task 5: Wire Profile Through `daemon.py`

**Files:**
- Modify: `murmur/daemon.py`
- Modify: `tests/test_daemon.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_daemon.py`:

```python
def test_double_tap_captures_terminal_profile_when_in_terminal():
    """When a terminal is active at recording start, _profile is set to 'terminal'."""
    daemon, engine, audio, injector = _make_daemon()
    with patch("murmur.daemon.get_profile", return_value="terminal"):
        daemon.on_double_tap()
    assert daemon._profile == "terminal"


def test_double_tap_captures_default_profile_when_not_in_terminal():
    daemon, engine, audio, injector = _make_daemon()
    with patch("murmur.daemon.get_profile", return_value="default"):
        daemon.on_double_tap()
    assert daemon._profile == "default"


def test_transcribe_passes_profile_to_engine_and_normalize():
    """_transcribe must forward self._profile to both engine.transcribe and normalize."""
    import numpy as np
    daemon, engine, audio, injector = _make_daemon()
    daemon._profile = "terminal"
    daemon.state = "idle"
    audio_data = np.zeros(16000, dtype="float32")
    engine.transcribe.return_value = "dash r"

    with patch("murmur.daemon.normalize", return_value="-r") as mock_norm:
        daemon._transcribe(audio_data)

    engine.transcribe.assert_called_once_with(audio_data, profile="terminal")
    mock_norm.assert_called_once_with("dash r", profile="terminal")
    injector.inject.assert_called_once_with("-r")
```

- [ ] **Step 2: Run to verify they fail**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_daemon.py::test_double_tap_captures_terminal_profile_when_in_terminal -v
```

Expected: `FAILED` — `AttributeError: 'Daemon' object has no attribute '_profile'`

- [ ] **Step 3: Update `murmur/daemon.py`**

Replace the entire file:

```python
import logging
import signal
import sys
import threading
from pathlib import Path

from murmur.audio import AudioCapture
from murmur.config import load_config
from murmur.engine import Engine
from murmur.hotkey import HotkeyListener
from murmur.injector import Injector
from murmur.normalizer import normalize
from murmur.platform import get_profile
from murmur.preprocessor import preprocess

LOG_FILE = Path.home() / ".apple-murmur" / "murmur.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class Daemon:
    def __init__(self):
        config = load_config()
        self.engine = Engine(model_name=config.model.name, device=config.model.device)
        self.audio = AudioCapture(
            sample_rate=config.audio.sample_rate,
            on_silence=self._on_silence,
        )
        self.injector = Injector()
        self.hotkey = HotkeyListener(
            on_double_tap=self.on_double_tap,
            interval_ms=config.hotkey.double_tap_interval_ms,
            key=config.hotkey.key,
        )
        self.state = "idle"
        self._profile: str = "default"
        self._lock = threading.Lock()

    def start(self) -> None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Starting murmur daemon")
        self.engine.load()
        self.hotkey.start()
        logger.info("murmur ready — double-tap fn to record")
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self.hotkey._listener.join()

    def on_double_tap(self) -> None:
        audio_to_transcribe = None
        with self._lock:
            if self.state == "idle":
                self._profile = get_profile()
                self.state = "recording"
                self.audio.start()
                logger.info("Recording started (profile=%s)", self._profile)
            elif self.state == "recording":
                self.state = "transcribing"
                audio_to_transcribe = self.audio.stop()
                logger.info("Recording stopped (%.1fs)", len(audio_to_transcribe) / 16000)
            # state == "transcribing": ignore double-tap

        if audio_to_transcribe is not None:
            self._transcribe(audio_to_transcribe)

    def _on_silence(self) -> None:
        """Auto-stop triggered by silence detection — same transition as second double-tap."""
        audio_to_transcribe = None
        with self._lock:
            if self.state == "recording":
                self.state = "transcribing"
                audio_to_transcribe = self.audio.stop()
                logger.info("Auto-stopped on silence (%.1fs)", len(audio_to_transcribe) / 16000)
        if audio_to_transcribe is not None:
            self._transcribe(audio_to_transcribe)

    def _transcribe(self, audio_data) -> None:
        try:
            audio_data = preprocess(audio_data, self.audio.sample_rate)
            text = self.engine.transcribe(audio_data, profile=self._profile)
            text = normalize(text, profile=self._profile)
            logger.info("Transcribed: %r", text)
            if text:
                self.injector.inject(text)
        except Exception as e:
            logger.error("Transcription failed: %s", e)
        finally:
            with self._lock:
                self.state = "idle"

    def _handle_sigterm(self, signum, frame) -> None:
        logger.info("SIGTERM received, shutting down")
        self.hotkey.stop()
        sys.exit(0)


if __name__ == "__main__":
    Daemon().start()
```

- [ ] **Step 4: Update `_make_daemon()` in `tests/test_daemon.py` to initialise `_profile`**

Find the `_make_daemon` function at the top of `tests/test_daemon.py` and add `daemon._profile = "default"` after `daemon._lock = threading.Lock()`:

```python
def _make_daemon():
    from murmur.daemon import Daemon
    mock_engine = MagicMock()
    mock_audio = MagicMock()
    mock_injector = MagicMock()
    mock_hotkey = MagicMock()
    daemon = Daemon.__new__(Daemon)
    daemon.engine = mock_engine
    daemon.audio = mock_audio
    daemon.injector = mock_injector
    daemon.hotkey = mock_hotkey
    daemon.state = "idle"
    daemon._profile = "default"
    daemon._lock = threading.Lock()
    return daemon, mock_engine, mock_audio, mock_injector
```

- [ ] **Step 5: Run all daemon tests**

```bash
~/.apple-murmur/venv/bin/pytest tests/test_daemon.py -v
```

Expected: all tests pass including the 3 new profile tests.

- [ ] **Step 6: Run the full test suite**

```bash
~/.apple-murmur/venv/bin/pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Restart daemon and verify**

```bash
murmur stop && sleep 1 && murmur start && sleep 2 && tail -5 ~/.apple-murmur/murmur.log
```

Expected log lines include `murmur ready` with no errors.

- [ ] **Step 8: Commit**

```bash
cd ~/.apple-murmur
git add murmur/daemon.py tests/test_daemon.py
git commit -m "feat: wire profile through daemon — terminal voice typing complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ `platform.py` with `get_profile()` — Task 1
- ✅ `_TERMINAL_VOCAB` + `correct(text, profile)` — Task 2
- ✅ `_INITIAL_PROMPTS` + `transcribe(audio, profile)` — Task 3
- ✅ `_TERMINAL_RULES` + `normalize(text, profile)` — Task 4
- ✅ Daemon captures profile at recording start, passes to engine + normalize — Task 5
- ✅ Error handling: `osascript` failure → `""` → `"default"` — covered in `platform.py` + tests
- ✅ All three test files specified in spec — `test_platform.py`, `test_normalizer.py`, `test_vocabulary.py`

**No placeholders found.**

**Type consistency:** `profile: str = "default"` is the signature used consistently across `correct()`, `transcribe()`, `normalize()`, and stored as `self._profile: str = "default"` in daemon. All call sites pass `profile=self._profile` as a keyword argument.
