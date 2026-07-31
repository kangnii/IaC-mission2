"""Tests du câblage CLI (scan -> parse -> score), sans réseau réel.

`run_remote_scan` est mocké : on ne teste pas SSH ici (déjà validé
manuellement contre les VM réelles), seulement que cli.py appelle bien
scanner + parser dans le bon ordre et gère les erreurs hôte par hôte.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from audit import cli

FIXTURE = Path(__file__).parent / "fixtures" / "sample-xccdf-results.xml"


def test_scan_requires_all_or_host() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["scan"])
    assert result.exit_code != 0
    assert "--all ou --host" in result.output


def test_scan_all_and_host_are_mutually_exclusive() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["scan", "--all", "--host", "web"])
    assert result.exit_code != 0
    assert "mutuellement exclusifs" in result.output


def test_scan_unknown_host_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["scan", "--host", "inconnu"])
    assert result.exit_code != 0
    assert "hôte inconnu" in result.output


def test_scan_single_host_prints_score(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "run_remote_scan", lambda host, output_dir, profile: FIXTURE)

    runner = CliRunner()
    result = runner.invoke(
        cli.main, ["scan", "--host", "bastion", "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "[bastion] score de conformité : 50.0% (7 règles)" in result.output


def test_scan_all_continues_after_one_host_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_scan(host: str, output_dir: Path, profile: str) -> Path:
        if host == "web":
            raise RuntimeError("hôte injoignable")
        return FIXTURE

    monkeypatch.setattr(cli, "run_remote_scan", fake_scan)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["scan", "--all", "--output-dir", str(tmp_path)])

    assert result.exit_code != 0  # au moins un hôte a échoué
    assert "[web] échec du scan : hôte injoignable" in result.output
    assert "[bastion] score de conformité" in result.output
    assert "[db] score de conformité" in result.output