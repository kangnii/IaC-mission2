"""Parsing des résultats XCCDF et calcul du score.

Format d'entrée (confirmé sur les rapports jour 4 / jour 6) :
un <TestResult> XCCDF contenant des <rule-result idref="..." severity="..."
weight="..."><result>pass|fail|notselected|notapplicable|error|unknown</result>
</rule-result>.

TODO jour 8 : implémenter le corps de ces fonctions avec lxml.etree.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Résultats qui comptent dans le calcul du score (les autres sont ignorés
# du dénominateur : une règle non sélectionnée ou non applicable à l'hôte
# ne doit pas pénaliser le score).
SCORABLE_RESULTS = {"pass", "fail"}


@dataclass(frozen=True)
class RuleResult:
    """Résultat d'une règle de durcissement pour un hôte donné."""

    rule_id: str
    result: str  # pass, fail, notselected, notapplicable, error, unknown
    severity: str
    weight: float


def parse_xccdf(xml_path: Path) -> list[RuleResult]:
    """Parse un fichier `*-results.xml` et retourne la liste des rule-result.

    TODO jour 8 :
      1. Charger le XML avec lxml.etree.parse
      2. Itérer sur les noeuds <rule-result> (namespace XCCDF)
      3. Construire un RuleResult par noeud
    """
    raise NotImplementedError


def compute_score(results: list[RuleResult]) -> float:
    """Calcule le pourcentage de conformité (0.0 à 100.0).

    Règle : score = 100 * nb(pass) / nb(pass + fail).
    Les résultats hors SCORABLE_RESULTS (notselected, notapplicable, error,
    unknown) sont exclus du dénominateur pour ne pas fausser le score.

    TODO jour 8 : implémenter, gérer le cas nb(pass+fail) == 0.
    """
    raise NotImplementedError