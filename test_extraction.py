"""Tests for the deterministic observation extractor."""
from ddr.extraction import extract_observations
from ddr.models import DocType, SourceDocument


def test_extracts_temperature_and_anomaly():
    doc = SourceDocument(
        doc_type=DocType.THERMAL,
        title="thermal",
        raw_text=(
            "## Main Electrical Room\n"
            "Thermal scan shows hotspot at breaker reading 71°C, reference 28°C.\n"
        ),
    )
    obs = extract_observations(doc, {"extraction": {"thermal_anomaly_delta_c": 5.0, "default_ref_temp_c": 30.0}})
    assert obs, "expected at least one observation"
    o = obs[0]
    assert o.temperature_c == 71.0
    assert o.reference_temp_c == 28.0
    assert o.anomaly is True
    assert o.severity.value in ("High", "Critical")


def test_extracts_multiple_areas():
    doc = SourceDocument(
        doc_type=DocType.INSPECTION,
        title="insp",
        raw_text=(
            "## Roof\nNo defect observed on the roof surface.\n"
            "## Wall\nDiagonal crack near window, 300 mm.\n"
        ),
    )
    obs = extract_observations(doc, {})
    areas = {o.area for o in obs}
    assert "Roof" in areas and "Wall" in areas
