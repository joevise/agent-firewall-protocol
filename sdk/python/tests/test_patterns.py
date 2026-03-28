from afp.patterns import matches, compile_pattern


def test_matches_api_key():
    assert matches(r"api[_-]?key", "my api_key is here")


def test_no_match():
    assert not matches(r"api[_-]?key", "nothing here")


def test_case_insensitive():
    assert matches(r"api[_-]?key", "API_KEY=foo")


def test_compile_cache():
    p1 = compile_pattern(r"test")
    p2 = compile_pattern(r"test")
    assert p1 is p2


def test_empty_text():
    assert not matches(r"abc", "")
    assert not matches(r"abc", None)
