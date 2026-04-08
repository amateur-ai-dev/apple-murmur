# apple-murmur v3 — Terminal, Names & Symbol Design Spec

**Date:** 2026-04-09
**Status:** Approved

---

## Overview

Four targeted changes to apple-murmur:

1. Remove silence auto-stop — explicit double-tap start/stop only
2. Comprehensive terminal/CLI vocabulary for accurate transcription
3. Indian names recognition in prompt and vocabulary
4. Full spoken-symbol normalizer for CLI usage

No architecture changes. No new files. Four existing files modified.

---

## 1. Remove Silence Auto-Stop

### `murmur/audio.py`

Remove all silence-detection code. The following are deleted:

- `_make_vad()` function
- `_is_speech()` method
- `on_silence` constructor parameter
- Five tracking vars: `_silence_threshold`, `_silence_chunks_needed`, `_silence_chunks`, `_has_spoken`, `_silence_triggered`
- `_vad` attribute
- The silence-detection branch in `_callback`
- Import of `_VAD_AGGRESSIVENESS` from preprocessor

`_BLOCK_SIZE = 480` stays — still used as the stream blocksize.

`_callback` becomes: append frame, nothing else.

`AudioCapture.__init__` signature becomes:
```python
def __init__(self, sample_rate: int = 16000):
```

### `murmur/daemon.py`

- Remove `on_silence=self._on_silence` from `AudioCapture(...)` constructor call
- Delete `_on_silence` method entirely

The state machine is unchanged: double-tap while idle → recording; double-tap while recording → transcribing → idle.

---

## 2. Terminal/CLI Vocabulary

### `murmur/engine.py` — `_INITIAL_PROMPT`

Replace current IT-only prompt with a comprehensive seed covering:

- **Shell built-ins:** bash, zsh, sh, fish, chmod, chown, chgrp, sudo, su, export, source, alias, env, printenv, which, whereis, type, echo, printf, read, exec, eval, trap, set, unset, kill, jobs, bg, fg, nohup, disown, ulimit, umask, xargs, tee, watch, yes
- **File ops:** ls, ll, la, cd, pwd, mkdir, rmdir, rm, cp, mv, touch, ln, find, locate, stat, file, du, df, lsof
- **Text tools:** cat, less, more, head, tail, grep, egrep, fgrep, ripgrep, rg, awk, sed, cut, sort, uniq, wc, tr, diff, patch, strings, hexdump
- **Version control:** git, gh, svn, hg, git-flow, git clone, git commit, git push, git pull, git rebase, git merge, git stash, git diff, git log, git checkout, git branch, git tag
- **Package managers:** npm, npx, pip, pip3, brew, apt, apt-get, yum, dnf, pacman, snap, flatpak, yarn, pnpm, cargo, gem, go get, composer, nuget, poetry, conda, mamba
- **Containers/infra:** docker, docker-compose, kubectl, helm, k9s, kind, minikube, terraform, ansible, pulumi, packer, vagrant, podman, buildah, skopeo
- **Languages/runtimes:** python, python3, node, nodejs, ruby, rust, java, javac, go, swift, kotlin, scala, php, perl, lua, elixir, erlang, haskell, clojure, dotnet
- **Databases:** psql, postgres, mysql, mysqldump, redis-cli, mongo, mongodump, sqlite3, influx, clickhouse
- **Networking:** ssh, scp, sftp, rsync, curl, wget, httpie, nc, netcat, nmap, dig, nslookup, traceroute, ping, ip, ifconfig, netstat, ss, tcpdump, mtr
- **Process/system:** ps, top, htop, btop, kill, pkill, pgrep, lsof, strace, ltrace, vmstat, iostat, sar, free, uptime, uname, hostname, dmesg, journalctl, systemctl, launchctl, crontab
- **Editors:** vim, nvim, nano, emacs, code, vscode, helix, micro
- **Build tools:** make, cmake, ninja, bazel, gradle, maven, ant, rake, gulp, grunt, webpack, vite, rollup, esbuild
- **Cloud CLIs:** aws, gcloud, az, doctl, flyctl, vercel, netlify, heroku, railway
- **Other common:** jq, yq, fzf, bat, eza, zoxide, starship, tmux, screen, mux, direnv, dotenv

### `murmur/vocabulary.py` — `_VOCAB`

Add the same CLI tool names as single-word entries for fuzzy correction. Key additions (rapidfuzz catches typos/mishearing):

```
git, npm, pip, brew, apt, yarn, pnpm, cargo, gem, docker, kubectl, helm,
terraform, ansible, pulumi, python, node, ruby, rust, golang, java, swift,
psql, mysql, redis, mongo, sqlite, nginx, systemctl, journalctl, ssh, curl,
wget, rsync, grep, awk, sed, vim, nvim, tmux, screen, jq, yq, fzf,
GitHub, GitLab, Bitbucket, Homebrew, PyPI, crontab, chmod, chown, sudo,
bash, zsh, fish, sh, vscode, heroku, vercel, netlify, webpack, vite
```

---

## 3. Indian Names

### `murmur/engine.py` — append to `_INITIAL_PROMPT`

Add a names seed line:

```
First names: Nithin, Nikhil, Naveen, Naresh, Nandish, Rahul, Rajesh, Ramesh,
Rakesh, Ravi, Rohan, Rohit, Priya, Priyanka, Pooja, Arjun, Arun, Anand,
Ankit, Anirudh, Akshay, Abhishek, Aditya, Suresh, Sanjay, Santosh, Satish,
Sunil, Deepak, Dinesh, Devesh, Dhruv, Kiran, Kavita, Kartik, Kamal, Mahesh,
Manish, Mukesh, Mohan, Vijay, Vinay, Vishal, Vivek, Shankar, Shyam, Shreya,
Shweta, Shubham, Ganesh, Girish, Gaurav, Amit, Harish, Hari, Hemant,
Jayesh, Jayant, Lakshmi, Laxman, Pranav, Prasad, Prashanth, Sachin, Samir,
Teja, Tejas, Uday, Usha, Vaishnavi, Varun, Vasanth, Yogesh, Yashwant, Pavan.
Surnames: Sharma, Verma, Gupta, Singh, Kumar, Patel, Nair, Menon, Pillai,
Rao, Reddy, Iyer, Iyengar, Agarwal, Joshi, Mishra, Tiwari, Pandey, Dwivedi,
Chatterjee, Banerjee, Mukherjee, Ghosh, Bose, Das, Sen, Naidu, Gowda, Hegde,
Shetty, Kamath, Bhat, Pai, Shah, Mehta, Modi, Desai, Bhatt, Trivedi,
Malhotra, Kapoor, Khanna, Arora, Bhatia, Krishnan, Subramaniam, Balakrishnan.
```

### `murmur/vocabulary.py` — append to `_VOCAB`

Add the same names for fuzzy correction of misheard Indian names.

---

## 4. Symbol Normalizer

### `murmur/normalizer.py` — `_RULES`

Existing rules kept. New rules added in correct order (longer/more-specific patterns before shorter ones):

| Spoken form(s) | Output |
|---|---|
| `triple dot`, `ellipsis` | `...` |
| `double dot`, `dot dot` | `..` |
| `double dash` | `--` |
| `double equals` | `==` |
| `double colon` | `::` |
| `double pipe`, `pipe pipe` | `\|\|` |
| `double greater than`, `greater greater` | `>>` |
| `double less than`, `less less` | `<<` |
| `double ampersand`, `ampersand ampersand` | `&&` |
| `fat arrow`, `equals greater than` | `=>` |
| `right arrow`, `dash greater than` | `->` |
| `at the rate` | `@` |
| `pipe` | `\|` |
| `greater than` | `>` |
| `less than` | `<` |
| `semicolon` | `;` |
| `tilde` | `~` |
| `asterisk`, `star` | `*` |
| `dollar sign`, `dollar` | `$` |
| `dash` | `-` |
| `equals sign`, `equal sign`, `equals` | `=` |
| `bang`, `exclamation mark` | `!` |
| `caret`, `hat` | `^` |
| `backtick`, `back tick`, `grave` | `` ` `` |
| `colon` | `:` |
| `question mark` | `?` |
| `single quote` | `'` |
| `double quote` | `"` |
| `plus sign`, `plus` | `+` |
| `comma` | `,` |
| `period`, `full stop` | `.` |

All patterns use `re.IGNORECASE` and `\b` word boundaries where applicable.

---

## Files Changed

| File | Change |
|---|---|
| `murmur/audio.py` | Remove silence auto-stop logic |
| `murmur/daemon.py` | Remove `on_silence` wiring + `_on_silence` method |
| `murmur/engine.py` | Replace `_INITIAL_PROMPT` with comprehensive CLI + names seed |
| `murmur/vocabulary.py` | Add CLI tools + Indian names to `_VOCAB` |
| `murmur/normalizer.py` | Add spoken-symbol rules to `_RULES` |

## Files NOT Changed

- `hotkey.py` — double-tap logic unchanged
- `preprocessor.py` — post-recording VAD pipeline unchanged
- `injector.py` — unchanged
- `config.py` — unchanged
- `cli.py` — unchanged
- `kenlm_rescorer.py` — unchanged

---

## Testing

Existing 48 tests must still pass. Update tests that mock `AudioCapture` with `on_silence` param — remove that param from mock constructors. No new test files needed; the normalizer rules and vocabulary are best verified by running the daemon and dictating.
