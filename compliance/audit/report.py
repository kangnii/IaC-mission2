"""Génération du rapport PDF (ReportLab), un rapport par hôte.

Réutilise directement `parse_xccdf` / `compute_score` de parser.py (jour 8)
pour lire les trois étapes de scan disponibles pour un hôte :
  - baseline (jour 4, avant durcissement)   : compliance/reports/baseline/
  - hardened (jour 6, après durcissement)   : compliance/reports/hardened/
  - live     (scan du jour, cli.py `scan`)  : passé directement en argument

Aucune logique de parsing n'est dupliquée ici : ce module ne fait que
mettre en forme des scores et des RuleResult déjà calculés.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle

from audit.parser import RuleResult, compute_score, parse_xccdf

# Emplacements par défaut des artefacts figés (jours 4/6). Le live n'a pas
# de dossier par défaut : il vient toujours de l'appelant (cli.py), fraîchement
# rapatrié par scanner.py au moment du scan.
DEFAULT_BASELINE_DIR = Path(__file__).resolve().parent.parent / "reports" / "baseline"
DEFAULT_HARDENED_DIR = Path(__file__).resolve().parent.parent / "reports" / "hardened"

ACCENT_COLOR = colors.HexColor("#2360A5")
PROFILE_LABEL = "ANSSI-BP-028 (high)"

# Ordre d'affichage des sévérités dans le tableau des échecs. Les sévérités
# absentes du XCCDF (rare, mais parser.py retombe sur "unknown") sont
# ajoutées à la fin, dans l'ordre où elles apparaissent.
SEVERITY_ORDER = ["high", "medium", "low"]

_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


def _register_dejavu() -> None:
    """Enregistre DejaVu Serif si disponible, sinon reste sur Helvetica.

    Convention alignée sur le pipeline ReportLab des CV (police DejaVu
    Serif, accent #2360A5). Pas de police vendorée dans le repo : on
    cherche l'emplacement standard Debian/Ubuntu. Si absente, on ne casse
    pas la génération du rapport, on retombe sur la police interne
    Helvetica de ReportLab.
    """
    global _FONT_REGULAR, _FONT_BOLD

    candidates = Path("/usr/share/fonts/truetype/dejavu")
    regular = candidates / "DejaVuSerif.ttf"
    bold = candidates / "DejaVuSerif-Bold.ttf"

    if not (regular.exists() and bold.exists()):
        return

    pdfmetrics.registerFont(TTFont("DejaVuSerif", str(regular)))
    pdfmetrics.registerFont(TTFont("DejaVuSerif-Bold", str(bold)))
    _FONT_REGULAR = "DejaVuSerif"
    _FONT_BOLD = "DejaVuSerif-Bold"


_register_dejavu()


@dataclass(frozen=True)
class StageScore:
    """Score d'une étape (baseline / hardened / live) pour un hôte.

    `available=False` quand le fichier XML de l'étape n'existe pas : le
    rapport doit rester générable pour un hôte dont, par exemple, le
    hardened n'a pas encore été rejoué, plutôt que de lever une exception.
    """

    label: str
    score: float | None
    rule_count: int
    available: bool


def _stage_score(label: str, xml_path: Path) -> StageScore:
    if not xml_path.exists():
        return StageScore(label=label, score=None, rule_count=0, available=False)

    results = parse_xccdf(xml_path)
    return StageScore(
        label=label,
        score=compute_score(results),
        rule_count=len(results),
        available=True,
    )


def _failures_by_severity(results: list[RuleResult]) -> dict[str, list[RuleResult]]:
    grouped: dict[str, list[RuleResult]] = {}
    for r in results:
        if r.result != "fail":
            continue
        grouped.setdefault(r.severity, []).append(r)

    ordered: dict[str, list[RuleResult]] = {}
    for sev in SEVERITY_ORDER:
        if sev in grouped:
            ordered[sev] = grouped.pop(sev)
    # Sévérités inattendues (ex. "unknown") : ajoutées après les connues,
    # sans faire échouer le rapport sur un XCCDF inhabituel.
    ordered.update(grouped)
    return ordered


def generate_host_report(
    host: str,
    live_xml_path: Path,
    output_path: Path,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
    hardened_dir: Path = DEFAULT_HARDENED_DIR,
) -> Path:
    """Génère le rapport PDF de conformité CIS pour `host`.

    Lit les trois étapes disponibles (baseline/hardened/live), affiche leur
    progression, puis détaille les règles en échec du scan live groupées
    par sévérité. Retourne le chemin du PDF généré.
    """
    baseline = _stage_score("Baseline (jour 4)", baseline_dir / f"{host}-baseline-results.xml")
    hardened = _stage_score("Hardened (jour 6)", hardened_dir / f"{host}-hardened-results.xml")
    live_results = parse_xccdf(live_xml_path)
    live = StageScore(
        label="Live (aujourd'hui)",
        score=compute_score(live_results),
        rule_count=len(live_results),
        available=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_styles()
    story: list = []

    story.append(Paragraph("Rapport de conformité CIS", styles["title"]))
    story.append(Paragraph(f"Hôte : {host}", styles["subtitle"]))
    story.append(
        Paragraph(
            f"Profil : {PROFILE_LABEL} · Généré le "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["meta"],
        )
    )
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Progression du score de conformité", styles["h2"]))
    story.append(_progression_table(baseline, hardened, live, styles))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Règles en échec (scan live)", styles["h2"]))
    story.extend(_failures_section(live_results, styles))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Rapport de conformité CIS - {host}",
    )
    doc.build(story)
    return output_path


def _build_styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "title", fontName=_FONT_BOLD, fontSize=20, textColor=ACCENT_COLOR,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=_FONT_BOLD, fontSize=13, textColor=colors.black,
            spaceAfter=1 * mm,
        ),
        "meta": ParagraphStyle(
            "meta", fontName=_FONT_REGULAR, fontSize=9, textColor=colors.grey,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=_FONT_BOLD, fontSize=12, textColor=ACCENT_COLOR,
            spaceBefore=2 * mm, spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "body", fontName=_FONT_REGULAR, fontSize=9,
        ),
    }


def _progression_table(
    baseline: StageScore, hardened: StageScore, live: StageScore, styles: dict
) -> Table:
    def cell(stage: StageScore) -> str:
        if not stage.available:
            return "non disponible"
        return f"{stage.score:.1f}%\n({stage.rule_count} règles)"

    data = [
        [baseline.label, hardened.label, live.label],
        [cell(baseline), cell(hardened), cell(live)],
    ]
    table = Table(data, colWidths=[56 * mm, 56 * mm, 56 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, 1), _FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT_COLOR),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ]
        )
    )
    return table


def _failures_section(live_results: list[RuleResult], styles: dict) -> list:
    grouped = _failures_by_severity(live_results)

    if not grouped:
        return [Paragraph("Aucune règle en échec sur ce scan.", styles["body"])]

    story: list = []
    for severity, rules in grouped.items():
        story.append(
            Paragraph(f"{severity.capitalize()} ({len(rules)})", styles["subtitle"])
        )
        data = [["Règle", "Sévérité"]] + [[r.rule_id, r.severity] for r in rules]
        table = Table(data, colWidths=[140 * mm, 28 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f9")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 5 * mm))

    return story