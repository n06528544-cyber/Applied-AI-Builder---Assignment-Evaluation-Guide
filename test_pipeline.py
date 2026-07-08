"""Tests for the reconciliation pipeline (merge, dedupe, conflict, missing)."""
from ddr.models import DocType, Observation, Severity, SourceDocument
from ddr.pipeline import build_report


def _doc(doc_type, observations):
    return SourceDocument(
        doc_type=doc_type, title=doc_type.value, raw_text="", observations=observations
    )


def test_thermal_anomaly_escalates_severity():
    thermal = _doc(DocType.THERMAL, [
        Observation(area="Main Electrical Room", description="Hotspot at breaker",
                    source="thermal", temperature_c=71.0, reference_temp_c=28.0, anomaly=True),
    ])
    inspection = _doc(DocType.INSPECTION, [])
    rep = build_report(inspection, thermal, {})
    area = next(a for a in rep.areas if a.area == "Main Electrical Room")
    assert area.severity in (Severity.HIGH, Severity.CRITICAL)
    assert "71" in area.severity_reasoning


def test_conflict_when_inspection_says_ok_but_thermal_anomalous():
    inspection = _doc(DocType.INSPECTION, [
        Observation(area="Roof", description="No defect observed on the roof surface.", source="inspection"),
    ])
    thermal = _doc(DocType.THERMAL, [
        Observation(area="Roof", description="Cooler patch 19°C vs ambient 27°C.",
                    source="thermal", temperature_c=19.0, reference_temp_c=27.0, anomaly=True),
    ])
    rep = build_report(inspection, thermal, {})
    all_conflicts = [c for a in rep.areas for c in a.conflicts] + rep.metadata.get("__x", [])
    flat = " ".join(c for a in rep.areas for c in a.conflicts)
    assert "conflict" in flat.lower() or any("disagree" in c.lower() for c in flat.split(". "))


def test_missing_thermal_data_is_flagged():
    inspection = _doc(DocType.INSPECTION, [
        Observation(area="Ceiling", description="Brown water stain on ceiling.", source="inspection"),
    ])
    thermal = _doc(DocType.THERMAL, [])  # no thermal at all
    rep = build_report(inspection, thermal, {})
    assert any("Thermal data" in m and "Ceiling" in m for m in rep.missing_info)


def test_root_cause_and_actions_inferred():
    thermal = _doc(DocType.THERMAL, [
        Observation(area="Main Electrical Room", description="Overheating breaker hotspot",
                    source="thermal", temperature_c=71.0, reference_temp_c=28.0, anomaly=True),
    ])
    inspection = _doc(DocType.INSPECTION, [
        Observation(area="Main Electrical Room", description="Breaker discolouration and burning odour.",
                    source="inspection"),
    ])
    rep = build_report(inspection, thermal, {})
    area = next(a for a in rep.areas if a.area == "Main Electrical Room")
    assert "resistive heating" in area.probable_root_cause.lower()
    assert area.recommended_actions and "electrician" in area.recommended_actions[0].lower()


def test_dedupe_removes_duplicate_observation():
    # same sentence appears in both docs for the same area
    inspection = _doc(DocType.INSPECTION, [
        Observation(area="Wall", description="Diagonal crack near window.", source="inspection"),
    ])
    thermal = _doc(DocType.THERMAL, [
        Observation(area="Wall", description="Diagonal crack near window.", source="thermal"),
    ])
    rep = build_report(inspection, thermal, {"extraction": {"dedupe_threshold": 0.82}})
    area = next(a for a in rep.areas if a.area == "Wall")
    # only one combined note for the duplicated sentence
    assert sum(1 for n in area.combined_notes if "Diagonal crack" in n) == 1
