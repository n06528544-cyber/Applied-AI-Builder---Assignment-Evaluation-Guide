"""Observation extraction.

Two strategies are provided:

* :func:`extract_observations` - a deterministic, dependency-free heuristic
  parser that works on both PDF-extracted text and the Markdown sample format.
  This is the default engine and needs no API key.
* :func:`extract_observations_with_llm` - asks an LLM to return structured
  JSON observations; used only when an LLM is configured and falls back to the
  heuristic parser on any error.

Both return a list of :class:`Observation` objects that the pipeline reconciles.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional

from .llm import LLMClient
from .models import ImageRef, Observation, Severity, SourceDocument, clean_area

# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

_TEMP_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:°\s*)?c(?![a-z])", re.I)
_REF_RE = re.compile(r"(?:reference|ambient|baseline)\s*(?:temp(?:erature)?)?\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*(?:°\s*)?c", re.I)
# Area headings: H2/H3, optionally prefixed with Area/Zone/...; H1 titles ignored.
_AREA_RE = re.compile(
    r"^\s*(?:#{2,3}\s+(?:area|zone|location|section)?\s*[:\-]?\s*"
    r"|area\s*[:\-]?\s*)([A-Za-z0-9][^\n#]{1,60})",
    re.I,
)

_SEV_KEYWORDS = [
    ("CRITICAL", ["critical", "severe", "urgent", "fire", "spark", "burning", "collapse", "structural failure", "live"]),
    ("HIGH", ["overheat", "hot spot", "hotspot", "fault", "short", "arcing", "burst", "flood"]),
    ("MEDIUM", ["leak", "crack", "damp", "malfunction", "elevated", "anomaly", "corrosion", "loose", "migration", "moisture"]),
    ("LOW", ["minor", "cosmetic", "discolour", "stain", "suggest", "recommend", "observation"]),
]

# Words that negate a sentence ("no sparking", "not leaking") -> treat as low risk.
_NEG_RE = re.compile(r"\b(no|not|without|none|free of|absence|nor)\b", re.I)


def _detect_severity(text: str) -> Severity:
    t = text.lower()
    if _NEG_RE.search(t):
        return Severity.LOW
    for level, words in _SEV_KEYWORDS:
        if any(w in t for w in words):
            return Severity[level]
    return Severity.LOW


def _split_blocks(text: str) -> List[tuple[str, str]]:
    """Return list of (area, block_text). Without headings -> ('General', text)."""
    lines = text.splitlines()
    blocks: List[tuple[str, str]] = []
    current_area: Optional[str] = None
    buf: List[str] = []
    for line in lines:
        stripped = line.strip()
        # drop metadata (> ...) and image markdown (![...](...)) from body text
        if stripped.startswith(">") or stripped.startswith("!"):
            continue
        m = _AREA_RE.match(line)
        if m and len(stripped) < 80:
            if current_area is not None or buf:
                blocks.append((current_area or "General", "\n".join(buf)))
            current_area = clean_area(m.group(1).strip())
            buf = []
        else:
            buf.append(line)
    if current_area is not None or buf:
        blocks.append((current_area or "General", "\n".join(buf)))
    if not blocks:
        blocks.append(("General", text))
    return blocks


def _first_temp(text: str, pattern) -> Optional[float]:
    m = pattern.search(text)
    return float(m.group(1)) if m else None


def extract_observations(doc: SourceDocument, config: Optional[dict] = None) -> List[Observation]:
    """Deterministic extraction of observations from a source document."""
    cfg = (config or {}).get("extraction", {})
    delta = float(cfg.get("thermal_anomaly_delta_c", 5.0))
    ref_default = float(cfg.get("default_ref_temp_c", 30.0))

    observations: List[Observation] = []
    blocks = _split_blocks(doc.raw_text)

    # index images by (loose) area for attachment
    def area_key(a):
        return re.sub(r"[^a-z0-9]+", " ", (a or "").lower()).strip()

    img_by_area: dict = {}
    for img in doc.images:
        k = area_key(img.area)
        img_by_area.setdefault(k, []).append(img)

    for area, block in blocks:
        if not block.strip():
            continue
        # split block into sentence-ish observations, keep headings out
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}", block) if s.strip()]
        if not sentences:
            sentences = [block.strip()]
        ref = _first_temp(block, _REF_RE)
        # attach the first image whose area matches this block
        ak = area_key(area)
        block_imgs = img_by_area.get(ak, [])
        for idx, sent in enumerate(sentences):
            if sent.startswith("#") or sent.startswith(">"):
                continue
            temp = _first_temp(sent, _TEMP_RE)
            is_thermal = doc.doc_type == "thermal"
            anomaly = False
            if temp is not None and is_thermal:
                ref_c = ref if ref is not None else ref_default
                anomaly = abs(temp - ref_c) >= delta
            sev = _detect_severity(sent)
            # thermal anomalies escalate severity
            if anomaly and sev in (Severity.LOW, Severity.MEDIUM):
                sev = Severity.HIGH
            img: Optional[ImageRef] = block_imgs[0] if (idx == 0 and block_imgs) else None
            observations.append(
                Observation(
                    area=area or "General",
                    description=sent,
                    source=doc.doc_type.value,
                    severity=sev,
                    temperature_c=temp,
                    reference_temp_c=ref,
                    anomaly=anomaly,
                    image=img,
                    confidence=1.0,
                    raw=sent,
                )
            )
    return observations


# ---------------------------------------------------------------------------
# LLM strategy (optional)
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = (
    "You are an expert building-diagnostics analyst. Given a raw inspection or "
    "thermal report, extract discrete observations as JSON. Return ONLY JSON of "
    "the form: "
    '{"observations":[{"area":str,"description":str,"severity":'
    '"Low|Medium|High|Critical","temperature_c":number|null,"anomaly":bool}]}'
)

_PROMPT_USER = (
    "Document type: {doc_type}\nTitle: {title}\n\nText:\n{text}\n\n"
    "Extract observations. Do not invent facts not present in the text."
)


def extract_observations_with_llm(doc: SourceDocument, client: LLMClient, config: dict) -> List[Observation]:
    """Use an LLM to extract observations, falling back to heuristics on error."""
    try:
        raw = client.complete(
            _EXTRACT_SYSTEM,
            _PROMPT_USER.format(doc_type=doc.doc_type.value, title=doc.title, text=doc.raw_text[:12000]),
        )
        data = client.extract_json(raw)
        obs = []
        for item in data.get("observations", []):
            obs.append(
                Observation(
                    area=(item.get("area") or "General").strip(),
                    description=item.get("description", "").strip(),
                    source=doc.doc_type.value,
                    severity=Severity.from_text(item.get("severity", "Low")),
                    temperature_c=item.get("temperature_c"),
                    anomaly=bool(item.get("anomaly", False)),
                    confidence=0.9,
                )
            )
        if obs:
            return obs
    except Exception as exc:  # graceful degradation
        import warnings
        warnings.warn(f"LLM extraction failed ({exc}); using heuristic extractor.")
    return extract_observations(doc, config)
