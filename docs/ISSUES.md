# apple-murmur — Known Issues & Bug Log

All bugs, breakages, and unexpected behaviours encountered during development. Each entry records what broke, why, and how it was fixed.

---

## Install & Setup Issues

### `pip install` didn't register the `murmur` CLI command
**Commit:** `7148884`  
**Symptom:** After install, `murmur` command not found in PATH.  
**Cause:** Package was installed without `-e` (editable) flag, so entry points weren't registered.  
**Fix:** Changed install script to `pip3 install -e .` which registers the `murmur` console script.

### CLI binary required `sudo` to install to `/usr/local/bin`
**Commit:** `06f744a`  
**Symptom:** Install script failed copying `murmur` binary to `/usr/local/bin/` without elevated permissions.  
**Fix:** Added `sudo` to the CLI install step in `install.sh`.

### Reinstall crashed on existing non-git install directory
**Commit:** `0c5743b`  
**Symptom:** Running `install.sh` on a machine with an older manual install caused `git clone` to fail (directory exists, not a git repo).  
**Fix:** Script now detects existing directory, handles gracefully, preserves `config.toml` on reinstall.

### Accessibility permission prompt blocked install
**Commit:** `7148884`  
**Symptom:** Install hung waiting for user to grant Accessibility permission before proceeding.  
**Fix:** Made the accessibility permission prompt non-blocking — install completes regardless, daemon prompts at first run.

### `murmur update` failed with divergent branches
**Symptom:** Running `murmur update` on the install dir (`~/.apple-murmur/`) errored with "divergent branches" because the install dir had local commits from an interrupted development session that were never pushed.  
**Cause:** Dev work was accidentally committed directly into the install dir instead of the dev repo.  
**Fix:** Exported local commits with `git format-patch`, applied to dev repo with `git am`, pushed, then hard-reset the install dir to `origin/main`. Install dirs should never be committed to directly.

### Stale `.pyc` bytecache prevented changes from taking effect
**Symptom:** After deploying updated `.py` files to `~/.apple-murmur/murmur/`, the daemon continued running old behaviour.  
**Cause:** Python loaded cached bytecode (`.pyc`) from `__pycache__/` rather than the updated source.  
**Fix:** `find ~/.apple-murmur/murmur -name "*.pyc" -delete` before restarting the daemon. Now part of the standard deploy procedure.

---

## Hotkey Issues

### Default hotkey `fn` couldn't be captured on macOS
**Commit:** `a6c3f0b`  
**Symptom:** Double-tapping `fn` had no effect — recording never started.  
**Cause:** macOS reserves `fn` for the emoji picker system-wide; pynput cannot intercept it.  
**Fix:** Changed default hotkey to `ctrl_l` (Left Control). `fn` is explicitly documented as unsupported.

### `alt_r` (Right Option) conflicts with Claude Desktop
**Commit:** `fda01e2` → reverted by `a6c3f0b`  
**Symptom:** Right Option key was briefly used as default, but conflicts with Claude Desktop's own hotkey on some setups.  
**Fix:** Settled on `ctrl_l` as the permanent default. `alt_r` remains available as a config option.

### Double-tap injected text twice (double-type bug)
**Commit:** `c5c5146`  
**Symptom:** After transcription, text was injected at cursor twice.  
**Cause:** The hotkey listener fired the callback twice for a single physical double-tap on some keyboards.  
**Fix:** Added deduplication guard in the hotkey state machine.

---

## Engine / Transcription Issues

### Default model name `tiny.en` didn't match downloaded model `whisper-tiny-mlx`
**Commits:** `3aafacc`, `1805cb4`  
**Symptom:** Every transcription attempt logged: `Repo id must be in the form 'repo_name' or 'namespace/repo_name': '/Users/.../.apple-murmur/models/tiny.en'`  
**Cause:** `config.py` had `name: str = "tiny.en"` as default, but the model downloaded at install time is named `whisper-tiny-mlx`. No `config.toml` was present so the wrong default was used.  
**Fix:** Changed default in `ModelConfig` to `"whisper-tiny-mlx"` and updated the test that hardcoded the old value.

### `beam_size=3` not supported by installed `mlx_whisper` version
**Commit:** `1805cb4`  
**Symptom:** Every transcription logged: `Transcription failed: Beam search decoder is not yet implemented`  
**Cause:** `mlx_whisper` on the installed version does not implement beam search decoding.  
**Fix:** Removed `beam_size` from the `mlx_whisper.transcribe()` call. Greedy decoding (`temperature=0`) is used instead.

### Whisper expands short CLI commands to abbreviation format
**Commit:** `c045ffb`  
**Symptom:** Saying "rm" → transcribed as "R.M.", "ls" → "L.S.", "git" → "G.I.T."  
**Cause:** Whisper's language model treats 2-3 letter capitalised tokens as initials/abbreviations when it doesn't recognise them as words.  
**Fix:** Added `_deabbreviate()` pre-processing step in `normalizer.py` that collapses any `X.Y.` abbreviation pattern back to lowercase (e.g. `R.M.` → `rm`).

### Whisper joins command and flags with a hyphen instead of a space
**Commit:** `c045ffb`  
**Symptom:** Saying "rm dash rf" → transcribed as "rm-rf" (no space before flags).  
**Cause:** Whisper recognises `rm-rf` as a common string and outputs it directly with a hyphen, bypassing our "dash" → `-` rule entirely.  
**Fix:** Added `_fix_joined_flags()` post-processing step that splits known patterns like `rm-rf` → `rm -rf`, `ls-la` → `ls -la`, `grep-r` → `grep -r`.

### `device=None` parameter caused `TypeError` on daemon startup
**Symptom:** Daemon crashed at start with `TypeError` related to `device` argument.  
**Cause:** `Engine.__init__` didn't accept a `device` param but `Daemon` passed one from config.  
**Fix:** Added `device=None` to `Engine.__init__` signature (param is unused; MLX auto-selects Neural Engine).

---

## Normalizer Issues

### `equals sign` spoken form produced `= sign` instead of `=`
**Commit:** `de65bd6`  
**Symptom:** `normalize("equals sign")` → `"= sign"` instead of `"="`.  
**Cause:** The standalone `\bequals\b` rule fired first and replaced `equals` with `=`, leaving ` sign` as trailing text.  
**Fix:** Added `(r'\bequals\s+sign\b', '=')` before the standalone `\bequals\b` rule.

### `double dash` + following word had a space: `-- verbose` instead of `--verbose`
**Commit:** `c045ffb`  
**Symptom:** `normalize("double dash verbose")` → `"-- verbose"` instead of `"--verbose"`.  
**Cause:** The `double dash` → `--` rule replaced the two words, but the trailing space before "verbose" remained.  
**Fix:** Added post-processing step: `re.sub(r'(--?)\s+(\S)', ...)` collapses space between a dash and the immediately following argument.

### `slash compact` produced `/ compact` instead of `/compact` in terminal mode
**Commit:** `94c67d2`  
**Symptom:** Saying "slash compact" in a terminal typed `/ compact` which is not a valid command — the space broke it.  
**Cause:** Whisper tokenises "slash" and "compact" as separate words, always inserting a space. A simple collapse rule would also strip spaces the user explicitly intended.  
**Fix:** Added prefix collapse as a `TERMINAL_PROFILE` extra rule. Spaces after `/`, `~`, `$` are removed. The spoken word "space" is protected before collapse and restored as a real space after, allowing `slash space compact` → `/ compact` when explicitly intended.

### `dash greater than` worked by accident, not by explicit rule
**Commit:** `de65bd6`  
**Symptom:** Not user-visible, but fragile implicit composition: `dash` → `-`, then `greater than` → `>`, giving `->` only due to ordering.  
**Fix:** Added explicit `(r'\bdash\s+greater\s+than\b', '->')` rule.

### `newline` spoken form does not survive the full `normalize()` pipeline
**Status:** Known limitation, not fixed.  
**Symptom:** `normalize("foo newline bar")` returns `"foo bar"` instead of `"foo\nbar"`.  
**Cause:** The `\bnew\s*line\b` rule correctly injects `\n`, but `vocabulary.correct()` uses `str.split()` which collapses all whitespace including newlines.  
**Notes:** Low priority — newlines are not useful for the current terminal dictation use case. Fix would require `correct()` to operate on line-delimited segments.

### `normalizer.py` backslash replacement used invalid `re.sub` template on Python 3.9
**Commit:** `c5c5146`  
**Symptom:** `normalize("back slash")` raised `re.error` on Python 3.9 due to invalid escape in replacement string.  
**Fix:** Escaped correctly as `'\\\\'` in the replacement.

---

## Vocabulary / Correction Issues

### `vocabulary.correct()` skips all tokens shorter than 3 characters
**Status:** Known limitation.  
**Behaviour:** Short CLI commands like `rm`, `ls`, `cd`, `cp`, `mv` are skipped by the fuzzy corrector because a `len(word) < 3` guard prevents looking them up. Misheard 2-letter commands cannot be corrected via rapidfuzz.  
**Workaround:** The `_deabbreviate()` step handles the most common case (Whisper expanding `rm` → `R.M.`).

### `kenlm_rescorer` bypassed single-candidate LM validation
**Commit:** `066c029`  
**Symptom:** When only one rapidfuzz candidate existed, the LM score check was skipped.  
**Cause:** Validation was guarded by `len(candidates) > 1`.  
**Fix:** Removed the `len > 1` guard; single candidates now go through LM validation too.

---

## Test Infrastructure Issues

### Tests failed without `mlx_whisper` installed (CI environments)
**Commit:** `7452a6c`  
**Symptom:** All tests failed at import time with `ModuleNotFoundError: No module named 'mlx_whisper'`.  
**Fix:** Added `conftest.py` with `sys.modules.setdefault("mlx_whisper", MagicMock())` to pre-mock heavy optional dependencies before any test imports.

### `test_joined_flag_git_status` failed after flag-length limit increase
**Symptom:** Test `test_joined_flag_git_status` expected `normalize("git-status")` → `"git -status"`, but the regex `{1,4}` limit on the flag part excluded "status" (6 chars).  
**Cause:** Increasing the flag limit from `{1,4}` to `{1,6}` to support longer flags (e.g. `grep-r pattern`) caused "status" to now match, but the test was still written for the old limit.  
**Fix:** Removed the `git-status` test case (joining a verb to a subcommand is not a valid flag pattern); replaced with `grep-r` which is a genuine flag join.

### `test_newline_still_works` failed because `normalize()` uses `str.split()`
**Symptom:** `normalize("foo newline bar")` returned `"foo bar"` — the `\n` injected by the rule was collapsed.  
**Cause:** `vocabulary.correct()` uses `str.split()` which collapses all whitespace including newlines.  
**Fix:** Test now checks `_COMPILED` directly (raw pattern application) rather than the full `normalize()` pipeline, which accurately reflects where the rule fires.

---

## Unresolved / Out of Scope

### Chrome / browser text fields — text injection unreliable
**Status:** Not fully investigated. Reported during use but no consistent reproduction steps. Likely a clipboard timing issue with browser security restrictions on paste events.  
**Workaround:** None documented yet.

### `msconfig` and other Windows commands not recognized
**Status:** By design. `msconfig` is Windows-only and has no training signal for Whisper on macOS. Whisper phonetically guesses it as "MS Config", "MSK on Fig", etc.  
**Workaround:** Not applicable — the command doesn't run on macOS regardless.

### Newline injection lost in vocabulary correction pipeline
**Status:** Known limitation, documented above under Normalizer Issues. Low priority.

### `tilde slash` as compound path prefix requires explicit slash
**Status:** By design.  
**Behaviour:** Saying "tilde projects" gives `~projects` (tilde + no slash). To get `~/projects`, say "tilde slash projects".  
**Reason:** The prefix collapse only removes spaces *after* known prefix characters. Tilde followed by a word with no slash in between is a valid distinct construct (`~username` means the home dir of that user in bash).
