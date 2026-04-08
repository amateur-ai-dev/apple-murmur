# apple-murmur v3 — Terminal, Names & Symbols Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove silence auto-stop, add comprehensive CLI vocabulary and Indian names to prompt/vocab, and expand the normalizer with spoken-symbol rules for terminal use.

**Architecture:** Five existing files modified, one new test file created. No new modules, no new dependencies. Changes are additive except for the silence auto-stop removal in `audio.py` and `daemon.py`.

**Tech Stack:** Python 3.9+, mlx-whisper, rapidfuzz, webrtcvad (preprocessor only after this change), pytest

---

## Task 1: Remove Silence Auto-Stop

**Files:**
- Modify: `murmur/audio.py`
- Modify: `murmur/daemon.py`
- Test: `tests/test_audio.py` (verify no regression)
- Test: `tests/test_daemon.py` (verify no regression)

- [ ] **Step 1: Run existing tests to confirm baseline**

```bash
cd /Users/nithingowda/apple-murmur
python -m pytest tests/test_audio.py tests/test_daemon.py -v
```
Expected: all pass.

- [ ] **Step 2: Rewrite `murmur/audio.py` — strip all silence-detection code**

Replace the entire file with:

```python
import logging
import threading

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# 480 samples = exactly 30ms at 16kHz — required by webrtcvad for frame processing.
# Also used by preprocessor._strip_silence_vad; both must stay in sync.
_BLOCK_SIZE = 480


class AudioCapture:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        with self._lock:
            self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._frames:
                return np.concatenate(self._frames, axis=0).flatten()
        return np.zeros(self.sample_rate, dtype=np.float32)
```

- [ ] **Step 3: Update `murmur/daemon.py` — remove `on_silence` wiring and `_on_silence` method**

In `Daemon.__init__`, change:
```python
        self.audio = AudioCapture(
            sample_rate=config.audio.sample_rate,
            on_silence=self._on_silence,
        )
```
To:
```python
        self.audio = AudioCapture(
            sample_rate=config.audio.sample_rate,
        )
```

Delete the entire `_on_silence` method (lines 69–78):
```python
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
```

- [ ] **Step 4: Run tests to verify no regression**

```bash
python -m pytest tests/test_audio.py tests/test_daemon.py -v
```
Expected: all tests pass. No test references `on_silence` or `_on_silence`.

- [ ] **Step 5: Commit and push**

```bash
git add murmur/audio.py murmur/daemon.py
git commit -m "feat: remove silence auto-stop — double-tap start/stop only"
git push
```

---

## Task 2: Spoken-Symbol Normalizer Rules

**Files:**
- Create: `tests/test_normalizer.py`
- Modify: `murmur/normalizer.py`

- [ ] **Step 1: Write failing tests for new symbol rules**

Create `tests/test_normalizer.py`:

```python
"""
Tests for normalizer spoken-symbol rules.
All new rules are tested with exact spoken forms and expected output.
"""
import pytest
from murmur.normalizer import normalize


# ---------------------------------------------------------------------------
# Multi-character symbols (must match before their shorter counterparts)
# ---------------------------------------------------------------------------

def test_triple_dot():
    assert normalize("triple dot") == "..."

def test_ellipsis():
    assert normalize("ellipsis") == "..."

def test_double_dot():
    assert normalize("double dot") == ".."

def test_dot_dot():
    assert normalize("dot dot") == ".."

def test_double_dash():
    assert normalize("double dash verbose") == "--verbose"

def test_double_equals():
    assert normalize("double equals") == "=="

def test_double_colon():
    assert normalize("double colon") == "::"

def test_double_pipe():
    assert normalize("double pipe") == "||"

def test_pipe_pipe():
    assert normalize("pipe pipe") == "||"

def test_double_greater_than():
    assert normalize("double greater than") == ">>"

def test_greater_greater():
    assert normalize("greater greater") == ">>"

def test_double_less_than():
    assert normalize("double less than") == "<<"

def test_less_less():
    assert normalize("less less") == "<<"

def test_double_ampersand():
    assert normalize("double ampersand") == "&&"

def test_ampersand_ampersand():
    assert normalize("ampersand ampersand") == "&&"

def test_fat_arrow():
    assert normalize("fat arrow") == "=>"

def test_equals_greater_than():
    assert normalize("equals greater than") == "=>"

def test_right_arrow():
    assert normalize("right arrow") == "->"

def test_at_the_rate():
    assert normalize("at the rate") == "@"


# ---------------------------------------------------------------------------
# Single-character symbols
# ---------------------------------------------------------------------------

def test_pipe():
    assert normalize("pipe") == "|"

def test_greater_than():
    assert normalize("greater than") == ">"

def test_less_than():
    assert normalize("less than") == "<"

def test_semicolon():
    assert normalize("semicolon") == ";"

def test_tilde():
    assert normalize("tilde") == "~"

def test_asterisk():
    assert normalize("asterisk") == "*"

def test_star():
    assert normalize("star") == "*"

def test_dollar_sign():
    assert normalize("dollar sign") == "$"

def test_dollar():
    assert normalize("dollar") == "$"

def test_dash():
    assert normalize("dash f") == "-f"

def test_equals():
    assert normalize("equals") == "="

def test_equal_sign():
    assert normalize("equal sign") == "="

def test_bang():
    assert normalize("bang") == "!"

def test_exclamation_mark():
    assert normalize("exclamation mark") == "!"

def test_caret():
    assert normalize("caret") == "^"

def test_hat():
    assert normalize("hat") == "^"

def test_backtick():
    assert normalize("backtick") == "`"

def test_back_tick():
    assert normalize("back tick") == "`"

def test_grave():
    assert normalize("grave") == "`"

def test_colon():
    assert normalize("colon") == ":"

def test_question_mark():
    assert normalize("question mark") == "?"

def test_single_quote():
    assert normalize("single quote") == "'"

def test_double_quote():
    assert normalize("double quote") == '"'

def test_plus_sign():
    assert normalize("plus sign") == "+"

def test_plus():
    assert normalize("plus") == "+"

def test_comma():
    assert normalize("comma") == ","

def test_period():
    assert normalize("period") == "."

def test_full_stop():
    assert normalize("full stop") == "."


# ---------------------------------------------------------------------------
# Existing rules still work (regression)
# ---------------------------------------------------------------------------

def test_at_sign_still_works():
    assert normalize("at sign") == "@"

def test_forward_slash_still_works():
    assert normalize("forward slash") == "/"

def test_underscore_still_works():
    assert normalize("underscore") == "_"

def test_hashtag_still_works():
    assert normalize("hashtag") == "#"

def test_newline_still_works():
    assert normalize("newline") == "\n"


# ---------------------------------------------------------------------------
# Composition: real CLI command spoken aloud
# ---------------------------------------------------------------------------

def test_composed_flag():
    # "git double dash verbose" -> "git --verbose"
    assert normalize("git double dash verbose") == "git --verbose"

def test_composed_pipe_redirect():
    # "ls pipe grep foo greater than out dot txt"
    assert normalize("ls pipe grep foo greater than out period txt") == "ls | grep foo > out.txt"

def test_composed_and():
    # "make double ampersand make install"
    assert normalize("make double ampersand make install") == "make && make install"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_normalizer.py -v 2>&1 | head -40
```
Expected: most symbol tests fail (rules not yet added).

- [ ] **Step 3: Add new rules to `murmur/normalizer.py`**

Replace the `_RULES` list in `murmur/normalizer.py` with the expanded version below. Order is critical — longer/more-specific patterns must appear before shorter ones.

```python
# Order matters — longer/more-specific patterns before shorter ones
_RULES = [
    # URLs / domains (existing)
    (r'\bdot\s+com\b',  '.com'),
    (r'\bdot\s+net\b',  '.net'),
    (r'\bdot\s+org\b',  '.org'),
    (r'\bdot\s+io\b',   '.io'),
    (r'\bdot\s+ai\b',   '.ai'),
    (r'\bdot\s+edu\b',  '.edu'),
    (r'\bdot\s+gov\b',  '.gov'),
    (r'\bdot\s+co\b',   '.co'),

    # Multi-character operators — must come before their single-char components
    (r'\btriple\s+dot\b',                '...'),
    (r'\bellipsis\b',                    '...'),
    (r'\bdouble\s+dot\b',               '..'),
    (r'\bdot\s+dot\b',                  '..'),
    (r'\bdouble\s+dash\b',              '--'),
    (r'\bdouble\s+equals\b',            '=='),
    (r'\bdouble\s+colon\b',             '::'),
    (r'\bdouble\s+pipe\b',              '||'),
    (r'\bpipe\s+pipe\b',                '||'),
    (r'\bdouble\s+greater\s+than\b',    '>>'),
    (r'\bgreater\s+greater\b',          '>>'),
    (r'\bdouble\s+less\s+than\b',       '<<'),
    (r'\bless\s+less\b',                '<<'),
    (r'\bdouble\s+ampersand\b',         '&&'),
    (r'\bampersand\s+ampersand\b',      '&&'),
    (r'\bfat\s+arrow\b',                '=>'),
    (r'\bequals\s+greater\s+than\b',    '=>'),
    (r'\bright\s+arrow\b',              '->'),
    (r'\bat\s+the\s+rate\b',            '@'),

    # Punctuation names (existing)
    (r'\bat\s+sign\b',                  '@'),
    (r'\bhash\s*tag\b',                 '#'),
    (r'\bopen\s+paren(?:thesis)?\b',    '('),
    (r'\bclose\s+paren(?:thesis)?\b',   ')'),
    (r'\bopen\s+bracket\b',             '['),
    (r'\bclose\s+bracket\b',            ']'),
    (r'\bopen\s+brace\b',               '{'),
    (r'\bclose\s+brace\b',              '}'),
    (r'\bforward\s+slash\b',            '/'),
    (r'\bback\s+slash\b',               '\\\\'),
    (r'\bunderscore\b',                  '_'),
    (r'\bampersand\b',                   '&'),
    (r'\bpercent\s+sign\b',             '%'),
    (r'\bnew\s*line\b',                  '\n'),

    # New single-character symbols
    (r'\bpipe\b',                        '|'),
    (r'\bgreater\s+than\b',              '>'),
    (r'\bless\s+than\b',                 '<'),
    (r'\bsemicolon\b',                   ';'),
    (r'\btilde\b',                       '~'),
    (r'\basterisk\b',                    '*'),
    (r'\bstar\b',                        '*'),
    (r'\bdollar\s+sign\b',              '$'),
    (r'\bdollar\b',                      '$'),
    (r'\bdash\b',                        '-'),
    (r'\bequal\s+sign\b',               '='),
    (r'\bequals\b',                      '='),
    (r'\bbang\b',                        '!'),
    (r'\bexclamation\s+mark\b',         '!'),
    (r'\bcaret\b',                       '^'),
    (r'\bhat\b',                         '^'),
    (r'\bback\s*tick\b',                '`'),
    (r'\bgrave\b',                       '`'),
    (r'\bcolon\b',                       ':'),
    (r'\bquestion\s+mark\b',            '?'),
    (r'\bsingle\s+quote\b',             "'"),
    (r'\bdouble\s+quote\b',             '"'),
    (r'\bplus\s+sign\b',                '+'),
    (r'\bplus\b',                        '+'),
    (r'\bcomma\b',                       ','),
    (r'\bfull\s+stop\b',               '.'),
    (r'\bperiod\b',                      '.'),
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_normalizer.py -v
```
Expected: all pass.

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
python -m pytest -v
```
Expected: all 48 existing tests + new normalizer tests pass.

- [ ] **Step 6: Commit and push**

```bash
git add murmur/normalizer.py tests/test_normalizer.py
git commit -m "feat: expand normalizer with spoken CLI symbol rules"
git push
```

---

## Task 3: Comprehensive CLI Vocabulary in Engine Prompt

**Files:**
- Modify: `murmur/engine.py`
- Test: `tests/test_engine.py` (add smoke test for prompt content)

- [ ] **Step 1: Add a failing test verifying prompt contains key CLI terms**

Append to `tests/test_engine.py`:

```python
def test_initial_prompt_contains_key_cli_terms():
    from murmur.engine import _INITIAL_PROMPT
    required = ["git", "docker", "kubectl", "npm", "pip", "brew", "ssh", "curl",
                "terraform", "python", "bash", "sudo", "grep", "awk", "sed"]
    for term in required:
        assert term in _INITIAL_PROMPT, f"Missing CLI term in prompt: {term}"


def test_initial_prompt_contains_indian_names():
    from murmur.engine import _INITIAL_PROMPT
    required = ["Sharma", "Patel", "Reddy", "Nair", "Rahul", "Priya", "Arjun"]
    for term in required:
        assert term in _INITIAL_PROMPT, f"Missing Indian name in prompt: {term}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_engine.py::test_initial_prompt_contains_key_cli_terms tests/test_engine.py::test_initial_prompt_contains_indian_names -v
```
Expected: FAIL — current prompt is IT-only.

- [ ] **Step 3: Replace `_INITIAL_PROMPT` in `murmur/engine.py`**

Replace the `_INITIAL_PROMPT` constant with:

```python
_INITIAL_PROMPT = (
    # Shell built-ins and file ops
    "bash zsh sh fish chmod chown chgrp sudo su export source alias env printenv "
    "which whereis type echo printf read exec eval trap set unset kill jobs bg fg "
    "nohup disown ulimit umask xargs tee watch ls ll la cd pwd mkdir rmdir rm cp mv "
    "touch ln find locate stat file du df lsof "
    # Text tools
    "cat less more head tail grep egrep fgrep ripgrep rg awk sed cut sort uniq wc "
    "tr diff patch strings hexdump "
    # Version control
    "git gh svn hg git-flow clone commit push pull rebase merge stash diff log "
    "checkout branch tag GitHub GitLab Bitbucket "
    # Package managers
    "npm npx pip pip3 brew apt apt-get yum dnf pacman snap flatpak yarn pnpm cargo "
    "gem poetry conda mamba composer nuget "
    # Containers and infra
    "docker docker-compose kubectl helm k9s kind minikube terraform ansible pulumi "
    "packer vagrant podman buildah skopeo "
    # Languages and runtimes
    "python python3 node nodejs ruby rust java javac golang swift kotlin scala php "
    "perl lua elixir erlang haskell clojure dotnet "
    # Databases
    "psql postgres mysql mysqldump redis-cli mongo mongodump sqlite3 influx clickhouse "
    # Networking
    "ssh scp sftp rsync curl wget httpie nc netcat nmap dig nslookup traceroute ping "
    "ip ifconfig netstat ss tcpdump mtr "
    # Process and system
    "ps top htop btop pkill pgrep strace vmstat iostat sar free uptime uname hostname "
    "dmesg journalctl systemctl launchctl crontab "
    # Editors
    "vim nvim nano emacs vscode helix micro "
    # Build tools
    "make cmake ninja bazel gradle maven ant rake gulp grunt webpack vite rollup esbuild "
    # Cloud CLIs
    "aws gcloud az doctl flyctl vercel netlify heroku railway "
    # Other common tools
    "jq yq fzf bat eza zoxide starship tmux screen direnv dotenv "
    # ITSM and IT ops (retained from v2)
    "ITIL ITSM ServiceNow Jira Confluence incident escalation SLA MTTR CMDB "
    "Kubernetes Azure AWS GCP DevOps CI/CD LDAP SSO MFA VPN Datadog Grafana "
    # Indian first names
    "Nithin Nikhil Naveen Naresh Nandish Rahul Rajesh Ramesh Rakesh Ravi Rohan Rohit "
    "Priya Priyanka Pooja Arjun Arun Anand Ankit Anirudh Akshay Abhishek Aditya "
    "Suresh Sanjay Santosh Satish Sunil Deepak Dinesh Devesh Dhruv Kiran Kavita "
    "Kartik Kamal Mahesh Manish Mukesh Mohan Vijay Vinay Vishal Vivek Shankar Shyam "
    "Shreya Shweta Shubham Ganesh Girish Gaurav Amit Harish Hari Hemant Jayesh "
    "Jayant Lakshmi Laxman Pranav Prasad Prashanth Sachin Samir Teja Tejas Uday "
    "Usha Vaishnavi Varun Vasanth Yogesh Yashwant Pavan "
    # Indian surnames
    "Sharma Verma Gupta Singh Kumar Patel Nair Menon Pillai Rao Reddy Iyer Iyengar "
    "Agarwal Joshi Mishra Tiwari Pandey Dwivedi Chatterjee Banerjee Mukherjee Ghosh "
    "Bose Das Sen Naidu Gowda Hegde Shetty Kamath Bhat Pai Shah Mehta Modi Desai "
    "Bhatt Trivedi Malhotra Kapoor Khanna Arora Bhatia Krishnan Subramaniam Balakrishnan"
)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_engine.py -v
```
Expected: all pass including the two new tests.

- [ ] **Step 5: Run full suite**

```bash
python -m pytest -v
```
Expected: all pass.

- [ ] **Step 6: Commit and push**

```bash
git add murmur/engine.py tests/test_engine.py
git commit -m "feat: comprehensive CLI + Indian names in Whisper initial_prompt"
git push
```

---

## Task 4: CLI Tools and Indian Names in Vocabulary

**Files:**
- Modify: `murmur/vocabulary.py`
- Test: `tests/test_vocabulary.py` (add smoke test for new terms)

- [ ] **Step 1: Add a failing test for new vocab terms**

Append to `tests/test_vocabulary.py`:

```python
def test_vocab_contains_cli_tools():
    from murmur.vocabulary import _VOCAB
    required = ["git", "docker", "kubectl", "npm", "pip", "brew", "ssh", "curl",
                "terraform", "vim", "tmux", "GitHub", "GitLab"]
    for term in required:
        assert term in _VOCAB, f"Missing CLI tool in _VOCAB: {term}"


def test_vocab_contains_indian_names():
    from murmur.vocabulary import _VOCAB
    required = ["Sharma", "Patel", "Reddy", "Nair", "Rahul", "Priya", "Arjun",
                "Krishnan", "Balakrishnan"]
    for term in required:
        assert term in _VOCAB, f"Missing Indian name in _VOCAB: {term}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_vocabulary.py::test_vocab_contains_cli_tools tests/test_vocabulary.py::test_vocab_contains_indian_names -v
```
Expected: FAIL.

- [ ] **Step 3: Add CLI tools and Indian names to `_VOCAB` in `murmur/vocabulary.py`**

Append the following to the `_VOCAB` list (after the existing entries, before the closing `]`):

```python
    # CLI tools and shell
    "git", "gh", "npm", "npx", "pip", "pip3", "brew", "apt", "yarn", "pnpm",
    "cargo", "gem", "poetry", "conda", "docker", "kubectl", "helm", "terraform",
    "ansible", "pulumi", "python", "python3", "node", "ruby", "rust", "golang",
    "java", "swift", "psql", "mysql", "redis", "mongo", "sqlite", "nginx",
    "systemctl", "journalctl", "ssh", "scp", "curl", "wget", "rsync", "grep",
    "awk", "sed", "vim", "nvim", "tmux", "screen", "jq", "yq", "fzf",
    "GitHub", "GitLab", "Bitbucket", "Homebrew", "PyPI", "crontab",
    "chmod", "chown", "sudo", "bash", "zsh", "fish", "vscode", "heroku",
    "vercel", "netlify", "webpack", "vite", "gcloud", "kubectl",
    # Indian first names
    "Nithin", "Nikhil", "Naveen", "Naresh", "Nandish", "Rahul", "Rajesh",
    "Ramesh", "Rakesh", "Ravi", "Rohan", "Rohit", "Priya", "Priyanka", "Pooja",
    "Arjun", "Arun", "Anand", "Ankit", "Anirudh", "Akshay", "Abhishek", "Aditya",
    "Suresh", "Sanjay", "Santosh", "Satish", "Sunil", "Deepak", "Dinesh",
    "Devesh", "Dhruv", "Kiran", "Kavita", "Kartik", "Kamal", "Mahesh", "Manish",
    "Mukesh", "Mohan", "Vijay", "Vinay", "Vishal", "Vivek", "Shankar", "Shyam",
    "Shreya", "Shweta", "Shubham", "Ganesh", "Girish", "Gaurav", "Amit",
    "Harish", "Hari", "Hemant", "Jayesh", "Jayant", "Lakshmi", "Laxman",
    "Pranav", "Prasad", "Prashanth", "Sachin", "Samir", "Teja", "Tejas",
    "Uday", "Usha", "Vaishnavi", "Varun", "Vasanth", "Yogesh", "Yashwant", "Pavan",
    # Indian surnames
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Nair", "Menon",
    "Pillai", "Rao", "Reddy", "Iyer", "Iyengar", "Agarwal", "Joshi", "Mishra",
    "Tiwari", "Pandey", "Dwivedi", "Chatterjee", "Banerjee", "Mukherjee", "Ghosh",
    "Bose", "Das", "Sen", "Naidu", "Gowda", "Hegde", "Shetty", "Kamath", "Bhat",
    "Pai", "Shah", "Mehta", "Modi", "Desai", "Bhatt", "Trivedi", "Malhotra",
    "Kapoor", "Khanna", "Arora", "Bhatia", "Krishnan", "Subramaniam", "Balakrishnan",
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_vocabulary.py -v
```
Expected: all pass.

- [ ] **Step 5: Run full suite**

```bash
python -m pytest -v
```
Expected: all pass.

- [ ] **Step 6: Commit and push**

```bash
git add murmur/vocabulary.py tests/test_vocabulary.py
git commit -m "feat: add CLI tools and Indian names to fuzzy vocabulary"
git push
```

---

## Self-Review

**Spec coverage:**
- ✅ Remove silence auto-stop — Task 1
- ✅ Double-tap start/stop only — Task 1 (state machine unchanged, silence path removed)
- ✅ Terminal CLI vocabulary — Tasks 3 and 4
- ✅ Natural language in terminal (option A — accurate transcription) — Tasks 3 and 4
- ✅ Indian names everywhere — Tasks 3 and 4
- ✅ All spoken symbols — Task 2

**Placeholder scan:** None. All steps contain full code.

**Type consistency:** `_INITIAL_PROMPT` is a `str` constant throughout. `_VOCAB` is a `list[str]` throughout. `_RULES` is a `list[tuple[str, str]]` throughout. No naming mismatches across tasks.
