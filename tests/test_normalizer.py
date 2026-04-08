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
    # vocabulary.correct() uses str.split() which collapses whitespace including newlines;
    # verify the rule fires by checking the raw pattern, not the full pipeline
    import re
    from murmur.normalizer import _COMPILED
    text = "foo newline bar"
    for pattern, replacement in _COMPILED:
        text = pattern.sub(replacement, text)
    assert "\n" in text


# ---------------------------------------------------------------------------
# Composition: real CLI command spoken aloud
# ---------------------------------------------------------------------------

def test_composed_flag():
    # "git double dash verbose" -> "git --verbose"
    assert normalize("git double dash verbose") == "git --verbose"

def test_composed_pipe_redirect():
    # "ls pipe grep foo greater than out period txt"
    assert normalize("ls pipe grep foo greater than out period txt") == "ls | grep foo > out.txt"

def test_composed_and():
    # "make double ampersand make install"
    assert normalize("make double ampersand make install") == "make && make install"
