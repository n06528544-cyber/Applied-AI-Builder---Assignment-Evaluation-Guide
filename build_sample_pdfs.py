"""Generate the bundled sample PDF reports (text + embedded images).

Running this lets you exercise the *PDF* ingestion path (not just Markdown).
Requires reportlab:  pip install reportlab

Usage:
    python -m samples.build_sample_pdfs
"""
from __future__ import annotations

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "inputs", "images")


def _build(path: str, title: str, blocks):
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Heading2"], spaceBefore=10)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=15)
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 0.4 * cm)]
    for kind, content in blocks:
        if kind == "h":
            story.append(Paragraph(content, h))
        elif kind == "p":
            story.append(Paragraph(content, body))
        elif kind == "img":
            img_path = os.path.join(IMG, content)
            if os.path.exists(img_path):
                story.append(Spacer(1, 0.2 * cm))
                story.append(RLImage(img_path, width=11 * cm, height=7.3 * cm))
                story.append(Spacer(1, 0.3 * cm))
    doc.build(story)


def build():
    _build(
        os.path.join(HERE, "inputs", "inspection_report.pdf"),
        "Site Inspection Report",
        [
            ("p", "<b>Property:</b> Maple Court Commercial Unit 4 &nbsp; <b>Date:</b> 2026-07-08 &nbsp; <b>Inspector:</b> R. Menon"),
            ("h", "Main Electrical Room"),
            ("p", "Visual inspection of the main distribution panel showed one breaker with discolouration and a faint burning odour. The panel surface was warm to the touch near the top-left breaker. No active sparking was observed at the time of visit."),
            ("h", "First Floor Ceiling (Above Reception)"),
            ("p", "A large brown water stain was noted on the ceiling with bubbling and peeling paint around the recessed light fitting. The substrate felt damp to touch."),
            ("img", "inspection_ceiling.png"),
            ("h", "Ground Floor East Wall (Office)"),
            ("p", "A diagonal crack was observed running from the window corner toward the floor, approximately 300 mm in length. Minor paint separation along the crack line."),
            ("img", "inspection_wall.png"),
            ("h", "Roof Membrane (Plant Room)"),
            ("p", "Walkthrough inspection of the roof membrane and plant-room envelope found no defect observed on the roof surface. No visible ponding or penetration noted."),
        ],
    )
    _build(
        os.path.join(HERE, "inputs", "thermal_report.pdf"),
        "Thermal Imaging Report",
        [
            ("p", "<b>Property:</b> Maple Court Commercial Unit 4 &nbsp; <b>Date:</b> 2026-07-08 &nbsp; <b>Operator:</b> Thermal Survey (FLIR E8)"),
            ("h", "Main Electrical Room"),
            ("p", "Thermal scan of the distribution panel identified a concentrated hotspot at the top-left breaker reading 71&deg;C against a reference temperature of 28&deg;C. The surrounding breakers measured within normal range (30-34&deg;C)."),
            ("img", "thermal_panel.png"),
            ("h", "Roof / Plant Room"),
            ("p", "Thermal image of the roof deck shows a distinct cooler patch measuring approximately 19&deg;C compared with an ambient roof temperature of 27&deg;C. The temperature depression is consistent with elevated moisture content / wet insulation in that zone."),
            ("img", "thermal_roof.png"),
            ("h", "First Floor Ceiling (Above Reception)"),
            ("p", "No dedicated thermal scan was performed for this area during the survey."),
        ],
    )


if __name__ == "__main__":
    build()
