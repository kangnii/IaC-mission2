"""Point d'entrée CLI de l'outil d'audit.

Câble scan -> parse -> affichage du score pour un ou plusieurs hôtes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from audit.exporter import DEFAULT_PUSHGATEWAY_ADDRESS, push_compliance_score
from audit.parser import compute_score, parse_xccdf
from audit.report import generate_host_report
from audit.scanner import DEFAULT_PROFILE, HOST_IPS, run_remote_scan

# compliance/reports/live/ : distinct de reports/baseline et reports/hardened
# (artefacts figés des jours 4/6), c'est ici que ce CLI dépose les scans
# à la demande. Ancré sur l'emplacement du package, indépendant du cwd
# depuis lequel on lance `python -m audit.cli` (make audit se place dans
# compliance/, mais rien n'impose de rester à cet endroit).
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "live"

# compliance/reports/pdf/ : sortie de --report, séparée de reports/live
# (XML bruts) pour ne pas mélanger artefacts machine et livrable humain.
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent.parent / "reports" / "pdf"


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
@click.option(
    "--pushgateway",
    "pushgateway_address",
    default=DEFAULT_PUSHGATEWAY_ADDRESS,
    show_default=True,
    help="Adresse du Pushgateway Prometheus.",
)
@click.option(
    "--no-push",
    "no_push",
    is_flag=True,
    help="Ne pas pousser le score vers le Pushgateway (calcul/affichage seuls).",
)
@click.option(
    "--report",
    "generate_report",
    is_flag=True,
    help="Générer un rapport PDF après le scan (compliance/reports/pdf/).",
)
@click.option(
    "--report-dir",
    "report_dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_REPORT_DIR,
    show_default=True,
    help="Dossier de sortie des rapports PDF (utilisé avec --report).",
)
def scan(
    scan_all: bool,
    host: str | None,
    output_dir: Path,
    profile: str,
    pushgateway_address: str,
    no_push: bool,
    generate_report: bool,
    report_dir: Path,
) -> None:
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

        if no_push:
            continue

        try:
            push_compliance_score(target, score, pushgateway_address)
        except Exception as exc:  # noqa: BLE001 - la supervision ne doit pas faire échouer l'audit
            click.echo(f"[{target}] échec de l'envoi au Pushgateway : {exc}", err=True)

        if not generate_report:
            continue

        try:
            pdf_path = generate_host_report(
                target, xml_path, report_dir / f"{target}-report.pdf"
            )
            click.echo(f"[{target}] rapport PDF : {pdf_path}")
        except Exception as exc:  # noqa: BLE001 - le rapport ne doit pas faire échouer l'audit
            click.echo(f"[{target}] échec de la génération du rapport : {exc}", err=True)

    sys.exit(exit_code)


@main.command()
@click.option("--all", "score_all", is_flag=True, help="Calculer le score de tous les hôtes.")
@click.option("--host", "host", help="Calculer le score d'un hôte précis (bastion, web, db).")
@click.option(
    "--results-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT_DIR,
    show_default=True,
    help="Dossier où lire les XML déjà présents (pas de scan SSH).",
)
@click.option(
    "--fail-under",
    "fail_under",
    type=float,
    default=None,
    help="Sort en erreur si le score d'un hôte est strictement inférieur à ce seuil (%).",
)
def score(
    score_all: bool,
    host: str | None,
    results_dir: Path,
    fail_under: float | None,
) -> None:
    """Recalcule le score à partir de XML déjà rapatriés, sans scan SSH.

    Contrairement à `scan`, cette commande ne touche pas aux VM : elle relit
    des résultats déjà présents sur disque (typiquement `reports/live/`,
    commités dans le repo). Pensée pour tourner sur un runner CI qui n'a
    pas accès au réseau privé libvirt (192.168.100.0/24) où vivent les VM.
    """
    if score_all and host:
        raise click.UsageError("--all et --host sont mutuellement exclusifs.")
    if not score_all and not host:
        raise click.UsageError("Précise --all ou --host <bastion|web|db>.")

    targets = list(HOST_IPS) if score_all else [host]

    exit_code = 0
    for target in targets:
        if target not in HOST_IPS:
            click.echo(
                f"[{target}] hôte inconnu (attendu : {sorted(HOST_IPS)})", err=True
            )
            exit_code = 1
            continue

        xml_path = results_dir / f"{target}-results.xml"
        if not xml_path.exists():
            click.echo(f"[{target}] aucun résultat trouvé ({xml_path})", err=True)
            exit_code = 1
            continue

        results = parse_xccdf(xml_path)
        target_score = compute_score(results)
        click.echo(f"[{target}] score de conformité : {target_score:.1f}% ({len(results)} règles)")

        if fail_under is not None and target_score < fail_under:
            click.echo(
                f"[{target}] score {target_score:.1f}% < seuil {fail_under:.1f}%", err=True
            )
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()