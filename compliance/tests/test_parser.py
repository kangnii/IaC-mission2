"""Tests du parsing XCCDF.

TODO jour 8 : lever le xfail une fois parse_xccdf/compute_score implémentés.
"""
from pathlib import Path

import pytest

from audit.parser import compute_score, parse_xccdf

FIXTURE = Path(__file__).parent / "fixtures" / "sample-xccdf-results.xml"


def test_placeholder() -> None:
    assert True


@pytest.mark.xfail(raises=NotImplementedError, reason="implémenté jour 8")
def test_parse_xccdf_counts_rule_results() -> None:
    results = parse_xccdf(FIXTURE)
    assert len(results) == 7


@pytest.mark.xfail(raises=NotImplementedError, reason="implémenté jour 8")
def test_compute_score_excludes_non_scorable() -> None:
    results = parse_xccdf(FIXTURE)
    assert compute_score(results) == pytest.approx(50.0)