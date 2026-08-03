"""Tests de l'export du score vers le Pushgateway.

`push_to_gateway` est mocké : on ne teste pas ici un vrai Pushgateway
(déployé par monitoring/docker-compose.yml, jour 9), seulement que
push_compliance_score construit la bonne métrique et le bon grouping_key.
"""
from __future__ import annotations

import pytest

from audit import exporter


def test_push_compliance_score_uses_expected_job_and_grouping_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def fake_push_to_gateway(address, *, job, registry, grouping_key):
        calls.append(
            {
                "address": address,
                "job": job,
                "grouping_key": grouping_key,
                "sample_value": registry.get_sample_value("compliance_score"),
            }
        )

    monkeypatch.setattr(exporter, "push_to_gateway", fake_push_to_gateway)

    exporter.push_compliance_score("web", 74.5)

    assert len(calls) == 1
    call = calls[0]
    assert call["address"] == exporter.DEFAULT_PUSHGATEWAY_ADDRESS
    assert call["job"] == "compliance_audit"
    assert call["grouping_key"] == {"host": "web"}
    assert call["sample_value"] == 74.5


def test_push_compliance_score_uses_custom_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        exporter,
        "push_to_gateway",
        lambda address, **kwargs: calls.append(address),
    )

    exporter.push_compliance_score("db", 60.0, pushgateway_address="pushgw:9091")

    assert calls == ["pushgw:9091"]


def test_push_compliance_score_propagates_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_connection_error(*args, **kwargs):
        raise ConnectionError("Pushgateway injoignable")

    monkeypatch.setattr(exporter, "push_to_gateway", raise_connection_error)

    with pytest.raises(ConnectionError):
        exporter.push_compliance_score("bastion", 42.0)