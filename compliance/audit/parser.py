"""Parsing des résultats XCCDF et calcul du score.

Format d'entrée (confirmé sur les rapports jour 4 / jour 6, et sur
compliance/reports/baseline/web-baseline-results.xml, même namespace que
la fixture de test) :
un <TestResult> XCCDF contenant des <rule-result idref="..." severity="..."
weight="..."><result>pass|fail|notselected|notapplicable|notchecked|error
|unknown</result></rule-result>.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

# Namespace XCCDF 1.2 des rapports OpenSCAP (SCAP Security Guide, profil
# ANSSI BP28 high). Vérifié identique entre la fixture et les vrais
# rapports.
XCCDF_NS = "http://checklists.nist.gov/xccdf/1.2"
_NSMAP = {"x": XCCDF_NS}

# Résultats qui comptent dans le calcul du score (les autres sont ignorés
# du dénominateur : une règle non sélectionnée ou non applicable à l'hôte
# ne doit pas pénaliser le score).
SCORABLE_RESULTS = {"pass", "fail"}


@dataclass(frozen=True)
class RuleResult:
    """Résultat d'une règle de durcissement pour un hôte donné."""

    rule_id: str
    result: str  # pass, fail, notselected, notapplicable, notchecked, error, unknown
    severity: str
    weight: float


def parse_xccdf(xml_path: Path) -> list[RuleResult]:
    """Parse un fichier `*-results.xml` et retourne la liste des rule-result.

    1. Charge le XML avec lxml.etree.parse. Les vrais rapports embarquent
       le catalogue complet des règles (description, OVAL, ...) avant le
       <TestResult> : on utilise huge_tree=True car ces fichiers dépassent
       largement la profondeur/complexité par défaut de libxml2.
    2. Itère sur les noeuds <rule-result> du namespace XCCDF.
    3. Construit un RuleResult par noeud.
    """
    parser = etree.XMLParser(huge_tree=True)
    tree = etree.parse(str(xml_path), parser=parser)

    results: list[RuleResult] = []
    for node in tree.getroot().iter(f"{{{XCCDF_NS}}}rule-result"):
        result_node = node.find("x:result", namespaces=_NSMAP)
        result_value = (
            result_node.text.strip()
            if result_node is not None and result_node.text
            else "unknown"
        )
        results.append(
            RuleResult(
                rule_id=node.get("idref", ""),
                result=result_value,
                severity=node.get("severity", "unknown"),
                weight=float(node.get("weight", "1.0")),
            )
        )
    return results


def compute_score(results: list[RuleResult]) -> float:
    """Calcule le pourcentage de conformité (0.0 à 100.0).

    Règle : score = 100 * nb(pass) / nb(pass + fail).
    Les résultats hors SCORABLE_RESULTS (notselected, notapplicable,
    notchecked, error, unknown) sont exclus du dénominateur pour ne pas
    fausser le score.

    Cas nb(pass + fail) == 0 (aucune règle scorable) : on retourne 0.0
    plutôt que de lever une exception, pour que l'appelant (cli.py,
    exporter.py jour 9) puisse traiter ce cas sans bloc try/except dédié.
    """
    scorable = [r for r in results if r.result in SCORABLE_RESULTS]
    if not scorable:
        return 0.0

    passed = sum(1 for r in scorable if r.result == "pass")
    return 100.0 * passed / len(scorable)