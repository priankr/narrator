import pytest
from pipeline.preprocessor import _compile_patterns, _expand_abbreviations, preprocess


_DEFAULTS = {
    "e.g.": "for example",
    "i.e.": "that is",
    "et al.": "and others",
    "vs.": "versus",
    "approx.": "approximately",
}


# ---------------------------------------------------------------------------
# _compile_patterns + _expand_abbreviations (unit tests, no file I/O)
# ---------------------------------------------------------------------------

def test_internal_dot_abbrev_replaced():
    patterns = _compile_patterns({"i.e.": "that is"})
    assert _expand_abbreviations("Use i.e. for clarification.", patterns) == "Use that is for clarification."


def test_trailing_dot_abbrev_replaced():
    patterns = _compile_patterns({"vs.": "versus"})
    assert _expand_abbreviations("Team A vs. Team B", patterns) == "Team A versus Team B"


def test_embedded_internal_dot_not_replaced():
    patterns = _compile_patterns({"i.e.": "that is"})
    # "i.e." preceded by a dot — must not match
    assert _expand_abbreviations("p.i.e. is a word", patterns) == "p.i.e. is a word"


def test_embedded_continuation_not_replaced():
    patterns = _compile_patterns({"i.e.": "that is"})
    # "i.e." followed by more letters — must not match
    assert _expand_abbreviations("i.e.l.t.s. score", patterns) == "i.e.l.t.s. score"


def test_case_insensitive():
    patterns = _compile_patterns({"i.e.": "that is"})
    assert _expand_abbreviations("I.e. this works.", patterns) == "that is this works."


def test_longest_key_first():
    # "et al." must not be shadowed by a hypothetical shorter "et" entry
    patterns = _compile_patterns({"et al.": "and others", "et": "and"})
    assert _expand_abbreviations("Smith et al. found", patterns) == "Smith and others found"


def test_abbrev_after_punctuation():
    patterns = _compile_patterns({"i.e.": "that is"})
    assert _expand_abbreviations("(i.e. a test)", patterns) == "(that is a test)"


def test_no_abbreviations_file_is_harmless(tmp_path, monkeypatch):
    # When abbreviations.yaml does not exist the preprocessor should not raise
    monkeypatch.chdir(tmp_path)
    # Reset the module-level cache so it re-loads from the (absent) file
    import pipeline.preprocessor as pp
    pp._ABBREVIATION_PATTERNS = None
    result = preprocess("Use i.e. here.")
    assert result == ["Use i.e. here."]
    # Restore
    pp._ABBREVIATION_PATTERNS = None


# ---------------------------------------------------------------------------
# Integration: preprocess() with the real abbreviations.yaml
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def reset_abbreviation_cache():
    import pipeline.preprocessor as pp
    pp._ABBREVIATION_PATTERNS = None
    yield
    pp._ABBREVIATION_PATTERNS = None


def test_preprocess_expands_eg(reset_abbreviation_cache):
    result = preprocess("This is a list, e.g. apples and oranges.")
    assert result == ["This is a list, for example apples and oranges."]


def test_preprocess_expands_ie(reset_abbreviation_cache):
    result = preprocess("That is correct, i.e. it works.")
    assert result == ["That is correct, that is it works."]


def test_preprocess_expands_vs(reset_abbreviation_cache):
    result = preprocess("Python vs. JavaScript is a common debate.")
    assert result == ["Python versus JavaScript is a common debate."]
