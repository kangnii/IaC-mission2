"""Lancement des scans OpenSCAP à distance via SSH.

Rejoue à la demande, sans repasser par Ansible, le scan déjà effectué par
le rôle ansible/roles/oscap_scan (jours 4 et 6) : le contenu SCAP
(``ssg-debian12-ds.xml``) est déjà déployé sur chaque VM par ce rôle,
cet outil se contente de déclencher `oscap xccdf eval` à distance et de
rapatrier le résultat, pour permettre un audit continu indépendant du
playbook de durcissement.
"""
from __future__ import annotations

import shlex
from pathlib import Path

import paramiko

# Profil réellement utilisé (voir compliance/reports/*/*-results.xml et
# ansible/roles/oscap_scan/defaults/main.yml).
DEFAULT_PROFILE = "xccdf_org.ssgproject.content_profile_anssi_bp28_high"

# Topologie réseau (terraform/variables.tf, ansible/inventory/hosts.ini.example) :
# bastion est le seul point d'entrée SSH, web et db se joignent en rebond
# (cf. ansible/ansible.cfg : "rebond SSH par le bastion pour joindre web et db").
BASTION = "bastion"
HOST_IPS = {
    "bastion": "192.168.100.10",
    "web": "192.168.100.20",
    "db": "192.168.100.30",
}

# ansible.cfg : remote_user = debian.
REMOTE_USER = "debian"

# Chemins déployés par ansible/roles/oscap_scan/defaults/main.yml.
REMOTE_CONTENT_DIR = "/opt/oscap-content"
REMOTE_CONTENT_FILENAME = "ssg-debian12-ds.xml"
REMOTE_REPORT_DIR = "/tmp/oscap-reports"


def _ssh_connect(ip: str, sock: paramiko.Channel | None = None) -> paramiko.SSHClient:
    """Ouvre une connexion SSH par clé, via l'agent SSH uniquement.

    Pas de chemin de clé privée en dur : allow_agent=True + look_for_keys=True
    laissent paramiko utiliser ssh-agent (ou ~/.ssh/id_* en repli standard),
    comme le ferait un `ssh` en ligne de commande sans -i.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=ip,
        username=REMOTE_USER,
        sock=sock,
        allow_agent=True,
        look_for_keys=True,
    )
    return client


def run_remote_scan(host: str, output_dir: Path, profile: str = DEFAULT_PROFILE) -> Path:
    """Lance un scan OpenSCAP sur `host` et rapatrie le XML de résultats.

    1. Connexion SSH via l'agent SSH : directe pour le bastion, en rebond
       par le bastion (canal direct-tcpip) pour web/db, puisque seul le
       bastion est joignable depuis le poste de contrôle.
    2. Exécution distante, en sudo (équivalent du `become: true` du rôle
       Ansible, on suppose donc `debian` en sudo NOPASSWD comme Ansible
       l'exige déjà) de :
         oscap xccdf eval --profile {profile} --results <remote>.xml <ds.xml>
    3. Rapatriement du fichier via SFTP vers output_dir / f"{host}-results.xml".

    Retourne le chemin local du fichier XML récupéré.
    """
    if host not in HOST_IPS:
        raise ValueError(f"Hôte inconnu : {host!r} (attendu : {sorted(HOST_IPS)})")

    target_ip = HOST_IPS[host]
    bastion_client: paramiko.SSHClient | None = None
    target_client: paramiko.SSHClient | None = None

    try:
        if host == BASTION:
            target_client = _ssh_connect(target_ip)
        else:
            bastion_client = _ssh_connect(HOST_IPS[BASTION])
            jump_channel = bastion_client.get_transport().open_channel(
                "direct-tcpip", (target_ip, 22), ("127.0.0.1", 0)
            )
            target_client = _ssh_connect(target_ip, sock=jump_channel)

        remote_content_path = f"{REMOTE_CONTENT_DIR}/{REMOTE_CONTENT_FILENAME}"
        remote_results_path = f"{REMOTE_REPORT_DIR}/{host}-results.xml"

        # Le rôle cis_hardening (jour 5) impose `Defaults umask=027` dans
        # sudoers : tout ce que crée `sudo` (dossier ET fichier) hérite d'un
        # mode restrictif (750 / 640, root:root), illisible/non traversable
        # par l'utilisateur `debian` qui se connecte en SFTP sans sudo.
        # On corrige le dossier ET le fichier, sans écraser le vrai code
        # retour d'oscap (capturé dans $oscap_rc avant les chmod, puisque
        # rc=2 est un résultat normal à ne pas perdre).
        cmd = (
            f"sudo mkdir -p {shlex.quote(REMOTE_REPORT_DIR)} && "
            f"sudo chmod 755 {shlex.quote(REMOTE_REPORT_DIR)} && "
            f"sudo oscap xccdf eval "
            f"--profile {shlex.quote(profile)} "
            f"--results {shlex.quote(remote_results_path)} "
            f"{shlex.quote(remote_content_path)}; "
            f"oscap_rc=$?; "
            f"sudo chmod 644 {shlex.quote(remote_results_path)} 2>/dev/null; "
            f"exit $oscap_rc"
        )
        _, stdout, stderr = target_client.exec_command(cmd)
        rc = stdout.channel.recv_exit_status()

        if rc > 2:
            err = stderr.read().decode(errors="replace").strip()
            raise RuntimeError(f"Échec du scan OpenSCAP sur {host} (rc={rc}) : {err}")

        output_dir.mkdir(parents=True, exist_ok=True)
        local_path = output_dir / f"{host}-results.xml"
        sftp = target_client.open_sftp()
        try:
            sftp.get(remote_results_path, str(local_path))
        finally:
            sftp.close()

        return local_path
    finally:
        if target_client is not None:
            target_client.close()
        if bastion_client is not None:
            bastion_client.close()