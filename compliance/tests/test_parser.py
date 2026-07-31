"""Tests du parsing XCCDF."""
from pathlib import Path

import pytest

from audit.parser import compute_score, parse_xccdf

FIXTURE = Path(__file__).parent / "fixtures" / "sample-xccdf-results.xml"


def test_placeholder() -> None:
    assert True


def test_parse_xccdf_counts_rule_results() -> None:
    results = parse_xccdf(FIXTURE)
    assert len(results) == 7


def test_compute_score_excludes_non_scorable() -> None:
    results = parse_xccdf(FIXTURE)
    assert compute_score(results) == pytest.approx(50.0)


def test_compute_score_empty_returns_zero() -> None:
    assert compute_score([]) == 0.0