# Limitations et décisions techniques

## Jour 4 : contenu SCAP pour Debian 12

Le paquet `ssg-debian` des dépôts Debian 12 (bookworm) n'embarque que du contenu
jusqu'à Debian 11 (`ssg-debian11-*`). Un premier scan avec ce contenu donnait un
score de 0.000000 sur les 3 VM : les vérifications d'applicabilité, basées sur le
CPE `cpe:/o:debian:debian_linux:11`, échouaient systématiquement contre nos VM
Debian 12, classant 100 % des règles du profil en `notapplicable` plutôt que de
les évaluer réellement.

Solution retenue : téléchargement du datastream `ssg-debian12-ds.xml` depuis les
releases officielles de ComplianceAsCode/content (v0.1.81), qui supporte
nativement Debian 12. Le fichier est vendoré dans
`ansible/roles/oscap_scan/files/` plutôt que réinstallé à chaque exécution, pour
garantir la reproductibilité du scan sans dépendance réseau pendant la démo.

Profil retenu : `ANSSI-BP-028 (high)` — référentiel de l'agence nationale de la
sécurité des systèmes d'information, niveau renforcé.

## Score de référence (Jour 4, avant durcissement)

44.6 % de conformité sur les 3 VM (bastion, web, db), avant application du rôle
`cis_hardening` prévu au Jour 5.
## Jour 5 : rôle cis_hardening — périmètre couvert et exclusions assumées

Score baseline (Jour 4) : 44,6 %. Le rôle `cis_hardening` couvre sysctl,
comptes/PAM, sudo, AIDE, auditd et rsyslog/logrotate.

Exclusions assumées (non corrigées volontairement, avec justification) :

- **`kernel_config_*`** (~25 règles) : flags de compilation du noyau
  (structleak, module signing, etc.). Nécessitent un noyau recompilé,
  hors périmètre d'un rôle Ansible sur un système déjà installé.
- **`partition_for_*`** (~9 règles) : partitions séparées (/var, /home,
  /var/log...). Décision prise au Jour 2 (Terraform/cloud-init) avec un
  disque unique ; non rattrapable sans redéploiement complet de l'infra.
- **`sudo_add_requiretty`** : désactivé volontairement. `requiretty` casse
  `ansible become` sans allocation de TTY (pipelining actif dans
  `ansible.cfg`), ce qui bloquerait toute exécution future d'Ansible
  (y compris le rôle web/db du Jour 6).
- **`sudo_add_noexec`** : désactivé volontairement (`!noexec`). Risque de
  casser des sous-process légitimes utilisés plus tard (apt, outil Python
  de compliance).
- **`rsyslog_remote_loghost` / `rsyslog_remote_tls*`** : nécessitent un
  récepteur syslog central, absent de la topologie actuelle (le Jour 9
  prévoit Prometheus/Grafana, pas un syslog centralisé).
- **`grub2_*` (arguments noyau de mitigation CPU)** : partiellement hors
  périmètre sur une VM KVM (paravirtualisée, pas de microcode physique à
  ajuster de la même façon qu'un bare-metal).

Notification AIDE : relais SMTP Gmail configuré (postfix satellite,
authentification via mot de passe d'application, secret stocké dans
`group_vars/all/vault.yml` chiffré Ansible Vault — jamais en clair dans
le dépôt public).