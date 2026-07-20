"""Point d'entrée CLI de l'outil d'audit.

TODO jour 8+ : câbler scan -> parse -> export -> report.
"""
import click


@click.group()
def main() -> None:
    """Audit de conformité CIS de l'infrastructure."""


@main.command()
@click.option("--all", "scan_all", is_flag=True, help="Scanner tous les hôtes.")
@click.option("--host", help="Scanner un hôte précis.")
def scan(scan_all: bool, host: str | None) -> None:
    """Lance un scan OpenSCAP et calcule le score de conformité."""
    click.echo("TODO jour 8 : implémentation du scan")


if __name__ == "__main__":
    main()
