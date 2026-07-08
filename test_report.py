"""Tests for the report renderers."""
from ddr.models import AreaFinding, DDRReport, DocType, ImageRef, Observation, Severity, SourceDocument
from ddr.pipeline import build_report
from ddr.report import render_html, render_markdown


def _sample_report():
    inspection = SourceDocument(doc_type=DocType.INSPECTION, title="i", raw_text="", observations=[
        Observation(area="Ceiling", description="Brown water stain noted.", source="inspection"),
    ])
    thermal = SourceDocument(doc_type=DocType.THERMAL, title="t", raw_text="", observations=[
        Observation(area="Ceiling", description="Cool patch 19°C vs 27°C.", source="thermal",
                    temperature_c=19.0, reference_temp_c=27.0, anomaly=True,
                    image=ImageRef(path="images/x.png", caption="thermal", area="Ceiling", source="thermal")),
    ])
    return build_report(inspection, thermal, {})


def test_markdown_has_all_seven_sections():
    md = render_markdown(_sample_report())
    for i in range(1, 8):
        assert f"## {i}." in md, f"missing section {i}"
    assert "Maple" not in md  # not present -> should not invent


def test_html_has_severity_badges_and_image():
    html = render_html(_sample_report())
    assert "sev-" in html
    assert "<img" in html
    for i in range(1, 8):
        assert f">{i}. " in html or f"{i}. " in html
