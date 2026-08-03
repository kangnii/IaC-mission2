"""Export du score vers Prometheus (Pushgateway).

L'outil d'audit tourne à la demande (`make audit`, un scan SSH ponctuel,
jour 8), il n'expose donc pas de endpoint HTTP que Prometheus pourrait
scraper en continu. Le Pushgateway comble cet écart : cli.py pousse ici
une gauge `compliance_score{job="compliance_audit", host="..."}` après
chaque scan, que Prometheus scrape ensuite à intervalle régulier (voir
monitoring/prometheus/prometheus.yml).
"""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Pushgateway exposé par monitoring/docker-compose.yml (jour 9), sur la
# même machine que celle qui exécute ce CLI (l'hôte libvirt, cf.
# monitoring_prometheus_source_ip dans group_vars/all/vars.yml).
DEFAULT_PUSHGATEWAY_ADDRESS = "localhost:9091"

# Un seul job pour toutes les séries compliance_score : le label "host"
# (grouping_key) distingue bastion/web/db entre eux dans le Pushgateway.
JOB_NAME = "compliance_audit"


def push_compliance_score(
    host: str,
    score: float,
    pushgateway_address: str = DEFAULT_PUSHGATEWAY_ADDRESS,
) -> None:
    """Pousse le score de conformité de `host` vers le Pushgateway.

    Une CollectorRegistry neuve à chaque appel : on ne pousse qu'une seule
    métrique par appel (pas d'accumulation entre hôtes dans un même
    registre), le grouping_key={"host": host} isole la série de chaque
    hôte côté Pushgateway sans écraser celle des autres.

    Lève l'exception telle quelle si le Pushgateway est injoignable
    (ConnectionError, etc.) : c'est à l'appelant (cli.py) de décider si
    un échec d'envoi doit interrompre l'audit ou seulement être signalé,
    le calcul et l'affichage du score (jour 8) ne doivent pas en dépendre.
    """
    registry = CollectorRegistry()
    gauge = Gauge(
        "compliance_score",
        "Score de conformité CIS (%) du dernier scan OpenSCAP",
        registry=registry,
    )
    gauge.set(score)
    push_to_gateway(
        pushgateway_address,
        job=JOB_NAME,
        registry=registry,
        grouping_key={"host": host},
    )