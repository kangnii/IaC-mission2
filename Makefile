# Makefile - orchestration du projet
# Usage : make <cible>

.PHONY: help up configure audit monitoring down clean

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

up:  ## Provisionne les VM (terraform apply)
	cd terraform && terraform init && terraform apply -auto-approve

configure:  ## Configure et durcit les VM (ansible)
	cd ansible && ansible-playbook -i inventory/hosts.ini site.yml

audit:  ## Lance l'audit de conformité OpenSCAP
	cd compliance && python -m audit.cli scan --all

monitoring:  ## Démarre la stack Prometheus + Grafana
	cd monitoring && docker compose up -d

down:  ## Détruit les VM
	cd terraform && terraform destroy -auto-approve

clean: down  ## Nettoyage complet
	cd monitoring && docker compose down -v || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
