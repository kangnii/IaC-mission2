# Modèle de menace

Menaces adressées par le durcissement :

- SSH exposé avec authentification par mot de passe -> clés + fail2ban
- Comptes et services par défaut -> désactivation, suppression
- Absence de traçabilité -> auditd
- Pile réseau permissive -> sysctl (anti-spoofing, ICMP)

TODO jour 13 : compléter avec la matrice menace / contrôle / règle CIS.
