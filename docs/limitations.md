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
