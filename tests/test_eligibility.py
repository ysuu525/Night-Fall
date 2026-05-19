from __future__ import annotations

from night_fall.surfacing import is_eligible_breath


def test_session_start_alone_is_eligible():
    assert is_eligible_breath("", -1, -1, is_session_start=True)


def test_query_alone_is_eligible():
    assert is_eligible_breath("walking home alone", -1, -1, is_session_start=False)


def test_affect_alone_is_eligible():
    assert is_eligible_breath("", 0.3, 0.6, is_session_start=False)


def test_nothing_is_not_eligible():
    assert not is_eligible_breath("", -1, -1, is_session_start=False)


def test_whitespace_query_does_not_count_as_query():
    assert not is_eligible_breath("   ", -1, -1, is_session_start=False)


def test_partial_affect_not_eligible():
    # Only valence provided, arousal missing
    assert not is_eligible_breath("", 0.5, -1, is_session_start=False)
