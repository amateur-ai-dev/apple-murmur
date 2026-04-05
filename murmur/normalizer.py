"""
Post-processes Whisper transcriptions to handle spoken punctuation,
URLs, and colloquial speech patterns that the model doesn't clean up.
"""
import re

# Order matters — longer patterns before shorter ones
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

    # Punctuation names (spoken explicitly)
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
    (r'\bback slash\b',             '\\'),
    (r'\bunderscore\b',             '_'),
    (r'\bampersand\b',              '&'),
    (r'\bpercent sign\b',           '%'),
    (r'\bnew line\b',               '\n'),
    (r'\bnewline\b',                '\n'),

    # Colloquial / informal contractions whisper sometimes expands
    (r'\bgoing to\b',   'gonna'),
    (r'\bwant to\b',    'wanna'),
    (r'\bgot to\b',     'gotta'),
    (r'\bhave to\b',    'hafta'),
    (r'\bout of\b',     'outta'),
    (r'\ba lot of\b',   'alotta'),
    (r'\bkind of\b',    'kinda'),
    (r'\bsort of\b',    'sorta'),
    (r'\bused to\b',    'usta'),
]

# Compile once
_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _RULES]


def normalize(text: str) -> str:
    for pattern, replacement in _COMPILED:
        text = pattern.sub(replacement, text)
    # Collapse multiple spaces introduced by substitutions
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()
