"""Point d'entrée CLI de l'outil d'audit.

Câble scan -> parse -> affichage du score pour un ou plusieurs hôtes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from audit.parser import compute_score, parse_xccdf
from audit.scanner import DEFAULT_PROFILE, HOST_IPS, run_remote_scan

# compliance/reports/live/ : distinct de reports/baseline et reports/hardened
# (artefacts figés des jours 4/6), c'est ici que ce CLI dépose les scans
# à la demande. Ancré sur l'emplacement du package, indépendant du cwd
# depuis lequel on lance `python -m audit.cli` (make audit se place dans
# compliance/, mais rien n'impose de rester à cet endroit).
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "live"


@click.group()
def main() -> None:
    """Audit de conformité CIS de l'infrastructure."""


@main.command()
@click.option("--all", "scan_all", is_flag=True, help="Scanner tous les hôtes.")
@click.option("--host", "host", help="Scanner un hôte précis (bastion, web, db).")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT_DIR,
    show_default=True,
    help="Dossier local où rapatrier les rapports XML.",
)
@click.option(
    "--profile",
    default=DEFAULT_PROFILE,
    show_default=True,
    help="Profil XCCDF à évaluer.",
)
def scan(scan_all: bool, host: str | None, output_dir: Path, profile: str) -> None:
    """Lance un scan OpenSCAP et calcule le score de conformité."""
    if scan_all and host:
        raise click.UsageError("--all et --host sont mutuellement exclusifs.")
    if not scan_all and not host:
        raise click.UsageError("Précise --all ou --host <bastion|web|db>.")

    targets = list(HOST_IPS) if scan_all else [host]

    exit_code = 0
    for target in targets:
        if target not in HOST_IPS:
            click.echo(
                f"[{target}] hôte inconnu (attendu : {sorted(HOST_IPS)})", err=True
            )
            exit_code = 1
            continue

        try:
            xml_path = run_remote_scan(target, output_dir, profile)
            results = parse_xccdf(xml_path)
            score = compute_score(results)
        except Exception as exc:  # noqa: BLE001 - un hôte en échec ne doit pas bloquer les autres
            click.echo(f"[{target}] échec du scan : {exc}", err=True)
            exit_code = 1
            continue

        click.echo(f"[{target}] score de conformité : {score:.1f}% ({len(results)} règles)")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()