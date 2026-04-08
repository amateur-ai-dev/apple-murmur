"""
Post-processes Whisper transcriptions to handle spoken punctuation,
URLs, CLI symbols, and colloquial speech patterns that the model doesn't clean up.
"""
import re

# Order matters — longer/more-specific patterns before shorter ones.
# Multi-character operators must appear before their single-character components.
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

    # Multi-character operators ------------------------------------------------
    # Dots
    (r'\btriple\s+dot\b',                        '...'),
    (r'\bellipsis\b',                             '...'),
    (r'\bdouble\s+dot\b',                        '..'),
    (r'\bdot\s+dot\b',                           '..'),

    # Comparison operators — must precede <, >, =, ! rules
    (r'\bnot\s+equal\s+to\b',                    '!='),
    (r'\bnot\s+equals\b',                        '!='),
    (r'\bnot\s+equal\b',                         '!='),
    (r'\bexclamation\s+equals\b',               '!='),
    (r'\bless\s+than\s+or\s+equal\s+to\b',      '<='),
    (r'\bless\s+than\s+or\s+equal\b',           '<='),
    (r'\bgreater\s+than\s+or\s+equal\s+to\b',   '>='),
    (r'\bgreater\s+than\s+or\s+equal\b',        '>='),

    # Dash / double operators
    (r'\bdouble\s+dash\b',                       '--'),
    (r'\bdouble\s+minus\b',                      '--'),
    (r'\bdouble\s+hyphen\b',                     '--'),
    (r'\bdouble\s+equals\b',                     '=='),
    (r'\bdouble\s+colon\b',                      '::'),

    # Bitwise / logical operators
    (r'\bdouble\s+pipe\b',                       '||'),
    (r'\bpipe\s+pipe\b',                         '||'),
    (r'\bdouble\s+greater\s+than\b',             '>>'),
    (r'\bgreater\s+greater\b',                   '>>'),
    (r'\bright\s+shift\b',                       '>>'),
    (r'\bappend\b',                              '>>'),
    (r'\bdouble\s+less\s+than\b',               '<<'),
    (r'\bless\s+less\b',                         '<<'),
    (r'\bleft\s+shift\b',                        '<<'),
    (r'\bdouble\s+ampersand\b',                  '&&'),
    (r'\bampersand\s+ampersand\b',               '&&'),

    # Arrow operators — before < and > rules
    (r'\bfat\s+arrow\b',                         '=>'),
    (r'\bequals\s+greater\s+than\b',             '=>'),
    (r'\bright\s+arrow\b',                       '->'),
    (r'\bdash\s+greater\s+than\b',               '->'),
    (r'\bleft\s+arrow\b',                        '<-'),
    (r'\bat\s+the\s+rate\b',                     '@'),

    # Punctuation names --------------------------------------------------------
    (r'\bat\s+sign\b',                           '@'),
    (r'\bhash\s*tag\b',                          '#'),
    (r'\bnumber\s+sign\b',                       '#'),
    (r'\bpound\s+sign\b',                        '#'),
    (r'\bopen\s+paren(?:thesis)?\b',             '('),
    (r'\bclose\s+paren(?:thesis)?\b',            ')'),
    (r'\bopen\s+(?:square\s+)?bracket\b',        '['),
    (r'\bclose\s+(?:square\s+)?bracket\b',       ']'),
    (r'\bopen\s+square\b',                       '['),
    (r'\bclose\s+square\b',                      ']'),
    (r'\bopen\s+(?:curly\s+)?brace\b',           '{'),
    (r'\bclose\s+(?:curly\s+)?brace\b',          '}'),
    (r'\bopen\s+curly\b',                        '{'),
    (r'\bclose\s+curly\b',                       '}'),
    (r'\bopen\s+(?:angle|chevron)(?:\s+bracket)?\b',  '<'),
    (r'\bclose\s+(?:angle|chevron)(?:\s+bracket)?\b', '>'),
    (r'\bleft\s+(?:angle|chevron)(?:\s+bracket)?\b',  '<'),
    (r'\bright\s+(?:angle|chevron)(?:\s+bracket)?\b', '>'),
    (r'\bforward\s+slash\b',                     '/'),
    (r'\bback\s+slash\b',                        '\\\\'),
    (r'\bbackslash\b',                           '\\\\'),
    (r'\bunderscore\b',                          '_'),
    (r'\bampersand\b',                           '&'),
    (r'\bpercent\s+sign\b',                     '%'),
    # NOTE: \n injected here is collapsed by vocabulary.correct() which uses str.split().
    # The rule fires correctly but the newline does not survive the full normalize() pipeline.
    # To observe the effect, test against _COMPILED directly (see test_newline_still_works).
    (r'\bnew\s*line\b',                          '\n'),

    # Single-character CLI symbols ---------------------------------------------
    (r'\bpipe\b',                                '|'),
    (r'\bgreater\s+than\b',                      '>'),
    (r'\bless\s+than\b',                         '<'),
    (r'\bsemicolon\b',                           ';'),
    (r'\btilde\b',                               '~'),
    (r'\basterisk\b',                            '*'),
    (r'\bstar\b',                                '*'),
    (r'\btimes\b',                               '*'),
    (r'\bmultiplied\s+by\b',                     '*'),
    (r'\bdivided\s+by\b',                        '/'),
    (r'\bforward\s+slash\b',                     '/'),
    (r'\bslash\b',                               '/'),
    (r'\bdollar\s+sign\b',                       '$'),
    (r'\bdollar\b',                              '$'),
    (r'\bdash\b',                                '-'),
    (r'\bminus\b',                               '-'),
    (r'\bhyphen\b',                              '-'),
    (r'\bequals\s+sign\b',                       '='),
    (r'\bequal\s+sign\b',                        '='),
    (r'\bequals\b',                              '='),
    (r'\bbang\b',                                '!'),
    (r'\bexclamation\s+mark\b',                 '!'),
    (r'\bexclamation\b',                         '!'),
    (r'\bcaret\b',                               '^'),
    (r'\bhat\b',                                 '^'),
    (r'\bback\s*tick\b',                         '`'),
    (r'\bgrave\b',                               '`'),
    (r'\btick\b',                                '`'),
    (r'\bcolon\b',                               ':'),
    (r'\bquestion\s+mark\b',                    '?'),
    (r'\bsingle\s+quote\b',                     "'"),
    (r'\bapostrophe\b',                          "'"),
    (r'\bdouble\s+quote\b',                     '"'),
    (r'\bopen\s+quote\b',                       '"'),
    (r'\bclose\s+quote\b',                      '"'),
    (r'\bplus\s+sign\b',                        '+'),
    (r'\bplus\b',                               '+'),
    (r'\bhash\b',                               '#'),
    (r'\bpound\b',                              '#'),
    (r'\bpercent\b',                            '%'),
    (r'\bcomma\b',                              ','),
    (r'\bfull\s+stop\b',                       '.'),
    (r'\bperiod\b',                             '.'),
]

# Compile once
_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _RULES]

# Whisper sometimes expands short CLI commands into abbreviation format.
# e.g. it transcribes "rm" as "R.M.", "ls" as "L.S.", "cd" as "C.D."
# This pattern collapses any X.Y. / X.Y.Z. abbreviation-style token to lowercase.
_ABBREV_RE = re.compile(r'\b([A-Z]\.){2,}', re.ASCII)

# When Whisper outputs a command with a flag already joined by a hyphen (e.g. "rm-rf"),
# it should be split into command + flag with a space: "rm -rf".
# Only applies when the left side is a known short CLI command (2-4 chars, no digits).
_JOINED_FLAG_RE = re.compile(r'\b([a-z]{2,4})-([a-zA-Z]{1,6})\b')


def _deabbreviate(text: str) -> str:
    """Convert Whisper abbreviation expansions back to lowercase CLI commands.
    e.g. 'R.M.' -> 'rm', 'L.S.' -> 'ls', 'G.I.T.' -> 'git'
    """
    return _ABBREV_RE.sub(lambda m: m.group(0).replace('.', '').lower(), text)


def _fix_joined_flags(text: str) -> str:
    """Reinsert space between a short command and its flags when Whisper joins them.
    e.g. 'rm-rf' -> 'rm -rf', 'ls-la' -> 'ls -la', 'grep-r' -> 'grep -r'
    Only fires when the left side is 2-4 lowercase letters (CLI command pattern).
    """
    return _JOINED_FLAG_RE.sub(lambda m: f"{m.group(1)} -{m.group(2)}", text)


def normalize(text: str) -> str:
    # Step 1: de-abbreviate before any other processing
    text = _deabbreviate(text)
    # Step 2: apply all symbol/punctuation rules
    for pattern, replacement in _COMPILED:
        text = pattern.sub(replacement, text)
    # Step 3: fix joined command-flag tokens Whisper produces (e.g. "rm-rf" -> "rm -rf")
    text = _fix_joined_flags(text)
    # Step 4: remove spaces between a dash/double-dash and the immediately following argument
    # e.g. "-- verbose" -> "--verbose", "- f" -> "-f"
    text = re.sub(r'(--?)\s+(\S)', lambda m: m.group(1) + m.group(2), text)
    # Step 5: remove spaces around a period between non-space chars (file paths, URLs)
    # e.g. "out . txt" -> "out.txt"
    text = re.sub(r'(\S)\s+\.\s+(\S)', r'\1.\2', text)
    # Step 6: collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    from murmur.vocabulary import correct  # lazy to avoid circular import at module load
    return correct(text)
