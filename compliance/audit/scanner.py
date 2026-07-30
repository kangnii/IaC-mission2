"""Lancement des scans OpenSCAP à distance via SSH.

TODO jour 8 : se connecter en SSH (paramiko), exécuter `oscap xccdf eval`
avec le profil utilisé en jour 4/jour 6, rapatrier le rapport XML.
"""
from __future__ import annotations

from pathlib import Path

# Profil réellement utilisé (voir compliance/reports/*/*-results.xml)
DEFAULT_PROFILE = "xccdf_org.ssgproject.content_profile_anssi_bp28_high"


def run_remote_scan(host: str, output_dir: Path, profile: str = DEFAULT_PROFILE) -> Path:
    """Lance un scan OpenSCAP sur `host` et rapatrie le XML de résultats.

    TODO jour 8 :
      1. Connexion SSH via paramiko (authentification par clé)
      2. Exécution distante de :
         oscap xccdf eval --profile {profile} --results <tmp>.xml <ds.xml>
      3. Rapatriement du fichier via SFTP vers output_dir / f"{host}-results.xml"

    Retourne le chemin local du fichier XML récupéré.
    """
    raise NotImplementedError
