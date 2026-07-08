"""Typed data models used across the DDR pipeline.

Everything that flows through the system is a plain dataclass so the pipeline
is easy to test, serialise (JSON), and reason about. We deliberately avoid
heavy framework types here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


def clean_area(name: str) -> str:
    """Normalise an area heading, stripping a leading 'Area:' / 'Zone -' prefix."""
    if not name:
        return name
    name = re.sub(r"^(area|zone|location|section)\s*[:\-]\s*", "", name.strip(), flags=re.I)
    return name.strip(" :.-")


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

    @classmethod
    def from_text(cls, value: str) -> "Severity":
        v = (value or "").strip().lower()
        mapping = {
            "low": cls.LOW,
            "minor": cls.LOW,
            "medium": cls.MEDIUM,
            "moderate": cls.MEDIUM,
            "high": cls.HIGH,
            "severe": cls.HIGH,
            "critical": cls.CRITICAL,
            "urgent": cls.CRITICAL,
        }
        return mapping.get(v, cls.LOW)


class DocType(str, Enum):
    INSPECTION = "inspection"
    THERMAL = "thermal"


@dataclass
class ImageRef:
    """A single image extracted from a source document."""

    path: str                     # workspace-relative path or URL
    caption: str = ""
    area: Optional[str] = None    # which area it belongs to
    source: str = ""              # "inspection" | "thermal" | ""
    alt: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "caption": self.caption,
            "area": self.area,
            "source": self.source,
            "alt": self.alt,
        }


@dataclass
class Observation:
    """One atomic finding extracted from a source document."""

    area: str
    description: str
    source: str                              # inspection | thermal
    severity: Severity = Severity.LOW
    temperature_c: Optional[float] = None
    reference_temp_c: Optional[float] = None
    anomaly: bool = False
    image: Optional[ImageRef] = None
    confidence: float = 1.0
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "description": self.description,
            "source": self.source,
            "severity": self.severity.value,
            "temperature_c": self.temperature_c,
            "reference_temp_c": self.reference_temp_c,
            "anomaly": self.anomaly,
            "image": self.image.to_dict() if self.image else None,
            "confidence": self.confidence,
        }


@dataclass
class SourceDocument:
    doc_type: DocType
    title: str
    raw_text: str
    observations: List[Observation] = field(default_factory=list)
    images: List[ImageRef] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type.value,
            "title": self.title,
            "observations": [o.to_dict() for o in self.observations],
            "images": [i.to_dict() for i in self.images],
            "metadata": self.metadata,
        }


@dataclass
class AreaFinding:
    """Reconciled findings for one property area."""

    area: str
    inspection_notes: List[str] = field(default_factory=list)
    thermal_notes: List[str] = field(default_factory=list)
    combined_notes: List[str] = field(default_factory=list)
    images: List[ImageRef] = field(default_factory=list)
    probable_root_cause: str = "Not Available"
    severity: Severity = Severity.LOW
    severity_reasoning: str = "Not Available"
    recommended_actions: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "inspection_notes": self.inspection_notes,
            "thermal_notes": self.thermal_notes,
            "combined_notes": self.combined_notes,
            "images": [i.to_dict() for i in self.images],
            "probable_root_cause": self.probable_root_cause,
            "severity": self.severity.value,
            "severity_reasoning": self.severity_reasoning,
            "recommended_actions": self.recommended_actions,
            "conflicts": self.conflicts,
        }


@dataclass
class DDRReport:
    property_name: str
    report_date: str
    prepared_by: str = "Automated DDR System"
    summary: str = ""
    areas: List[AreaFinding] = field(default_factory=list)
    additional_notes: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "property_name": self.property_name,
            "report_date": self.report_date,
            "prepared_by": self.prepared_by,
            "summary": self.summary,
            "areas": [a.to_dict() for a in self.areas],
            "additional_notes": self.additional_notes,
            "missing_info": self.missing_info,
            "metadata": self.metadata,
        }
