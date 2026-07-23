# Déploiement reproductible et durcissement automatisé d'une infrastructure


## Objectif

Décrire une infrastructure en code (Terraform), la durcir automatiquement
(Ansible selon les benchmarks CIS), puis mesurer et superviser en continu son
niveau de conformité (audit OpenSCAP + outil Python + Prometheus/Grafana).

Message clé : le score de conformité passe de ~40 % à ~90 % en direct, de façon
reproductible et redéployable sur une vraie infrastructure.

## Architecture

| Couche | Outil | Rôle |
|--------|-------|------|
| Provisioning | Terraform + libvirt (KVM) | 3 VM sur réseau privé : bastion, web, db |
| Configuration | Ansible | Rôles idempotents de config et durcissement |
| Audit | OpenSCAP + Python | Scan CIS, calcul de score, rapport PDF |
| Supervision | Prometheus + Grafana | Score de conformité + métriques système |
| CI/CD (bonus) | GitLab CI | Casse le build sous un seuil de conformité |

## Topologie

    [ bastion ] --- seul point d'entrée SSH
         |
    -----+-----  réseau privé (192.168.100.0/24)
    |         |
  [ web ]   [ db ]
  Nginx+TLS  PostgreSQL

## Prérequis

- Hôte Linux avec KVM (`egrep -c '(vmx|svm)' /proc/cpuinfo` > 0)
- terraform, ansible, oscap installés
- 6 à 8 Go de RAM libres

## Utilisation

    make up          # terraform apply : provisionne les VM
    make configure   # ansible : configuration + durcissement
    make audit       # scan OpenSCAP + score de conformité
    make monitoring  # lance la stack Prometheus/Grafana
    make down        # détruit les VM
    make clean       # nettoyage complet

## Structure du dépôt

    terraform/     Provisioning des VM et du réseau
    ansible/       Rôles de configuration et durcissement
    compliance/    Outil Python d'audit (OpenSCAP -> score -> PDF)
    monitoring/    Stack Prometheus + Grafana (docker-compose)
    ci/            Pipeline GitLab CI
    docs/          Documentation de soutenance

## Suivi d'avancement

- [x] Jour 1 : environnement, dépôt, image cloud-init
- [x] Jour 2 : Terraform (réseau + 3 VM)
- [x] Jour 3 : Ansible de base (common, ssh, firewall)
- [ ] Jour 4 : scan OpenSCAP de référence (avant durcissement)
- [ ] Jour 5 : rôle cis_hardening
- [ ] Jour 6 : rôles web + db, scan après durcissement
- [ ] Jour 7 : marge / ébauche outil Python
- [ ] Jour 8 : scanner.py + parser.py
- [ ] Jour 9 : stack de supervision
- [ ] Jour 10 : dashboard Grafana
- [ ] Jour 11 : rapport PDF + CI
- [ ] Jour 12 : répétition démo
- [ ] Jour 13 : gel du code, README final
- [ ] Jour 14 : marge
