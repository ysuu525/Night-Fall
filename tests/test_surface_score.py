from __future__ import annotations

import pytest

from night_fall.surfacing import compute_surface_score


@pytest.mark.parametrize(
    "a, c, alpha, expected",
    [
        # Single-channel strong → score equals the strong side
        (0.8, 0.0, 0.25, 0.8),
        (0.0, 0.8, 0.25, 0.8),
        # Both channels equal moderate → max + alpha*min
        (0.6, 0.6, 0.25, 0.75),
        # Mixed strong + medium
        (0.8, 0.5, 0.25, 0.925),
        # Both weak
        (0.2, 0.1, 0.25, 0.225),
        # Both zero
        (0.0, 0.0, 0.25, 0.0),
        # alpha=0 → pure max, no bonus
        (0.6, 0.6, 0.0, 0.6),
    ],
)
def test_compute_surface_score_table(a, c, alpha, expected):
    assert compute_surface_score(a, c, alpha) == pytest.approx(expected)


def test_compute_surface_score_monotonic_in_max():
    base = compute_surface_score(0.5, 0.4, 0.25)
    higher = compute_surface_score(0.7, 0.4, 0.25)
    assert higher > base


def test_compute_surface_score_symmetric_in_arguments():
    assert compute_surface_score(0.6, 0.3, 0.25) == compute_surface_score(0.3, 0.6, 0.25)
