"""Document ingestion: read PDF / Markdown / text and extract text + images.

The ingestion layer is deliberately format-agnostic at the boundary: callers
hand it a path and get back a :class:`SourceDocument` containing the raw text
and any extracted images. Two backends are provided:

* :func:`load_pdf`  - uses PyMuPDF to pull text blocks and embedded images,
                      mapping each image to the page/area it appeared on.
* :func:`load_text` - parses Markdown / plain text (our sample format) where
                      area sections and image references are explicit.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from typing import List, Optional

from .models import DocType, ImageRef, SourceDocument, clean_area

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def _norm_area(text: str) -> str:
    """Normalise an area label for matching (case/space/punctuation)."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _save_image_bytes(data: bytes, out_dir: str, prefix: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    digest = hashlib.md5(data).hexdigest()[:10]
    path = os.path.join(out_dir, f"{prefix}_{digest}.png")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


# ---------------------------------------------------------------------------
# PDF ingestion
# ---------------------------------------------------------------------------

def load_pdf(
    path: str,
    doc_type: DocType,
    images_dir: Optional[str] = None,
    title: Optional[str] = None,
) -> SourceDocument:
    """Extract text and embedded images from a PDF report.

    Images are written next to the document (or into ``images_dir``) and
    returned as :class:`ImageRef` objects with a best-effort area guess taken
    from the surrounding text on the same page.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyMuPDF is required for PDF ingestion. `pip install pymupdf`."
        ) from exc

    images_dir = images_dir or os.path.join(os.path.dirname(path) or ".", "images")
    doc = fitz.open(path)
    raw_parts: List[str] = []
    images: List[ImageRef] = []

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""
        raw_parts.append(text)

        # Guess area context from the page heading / first lines.
        heading = " ".join(text.splitlines()[:3])
        area_guess = _guess_area_from_text(heading)

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:  # CMYK -> RGBA
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                png = pix.tobytes("png")
            except Exception:
                continue
            saved = _save_image_bytes(
                png, images_dir, prefix=f"{doc_type.value}_p{page_index}"
            )
            images.append(
                ImageRef(
                    path=saved,
                    area=area_guess,
                    source=doc_type.value,
                    caption=f"{doc_type.value.title()} image (page {page_index + 1})",
                )
            )

    raw = "\n".join(raw_parts)
    return SourceDocument(
        doc_type=doc_type,
        title=title or os.path.basename(path),
        raw_text=raw,
        images=images,
        metadata={"source_path": path, "pages": len(doc)},
    )


def _guess_area_from_text(text: str) -> Optional[str]:
    m = re.search(r"(area|zone|location|section)\s*[:\-]?\s*([A-Za-z0-9][^\n]{1,40})", text, re.I)
    if m:
        return m.group(2).strip().strip(":. ")
    # fall back to first ALL-CAPS token that looks like a place
    for token in re.findall(r"\b[A-Z][A-Z0-9][A-Za-z0-9 /-]{2,30}\b", text):
        if any(w in token.lower() for w in ("room", "panel", "floor", "roof", "wall", "area", "unit")):
            return token.strip()
    return None


# ---------------------------------------------------------------------------
# Markdown / text ingestion (used for the sample inputs)
# ---------------------------------------------------------------------------

_AREA_RE = re.compile(r"^#{2,3}\s*(?:area\s*[:\-]?\s*)?(.*)$", re.I)
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)", re.I)
_META_RE = re.compile(r"^>\s*([A-Za-z ]+):\s*(.+)$")


def load_text(
    path: str,
    doc_type: DocType,
    images_dir: Optional[str] = None,
    title: Optional[str] = None,
) -> SourceDocument:
    """Parse a Markdown/text report with explicit Area sections and images.

    Expected (sample) layout:
        # Inspection Report
        > Property: Maple Court
        > Date: 2026-07-08

        ## Area: Main Electrical Room
        Some observation text...
        ![caption](images/inspection_ceiling.png)

    Area boundaries reset on each heading; images are attached to the
    currently-active area.
    """
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    base_dir = os.path.dirname(path) or "."
    metadata: dict = {}
    raw_parts: List[str] = []
    images: List[ImageRef] = []
    current_area: Optional[str] = None

    for line in lines:
        m = _META_RE.match(line.strip())
        if m and current_area is None:
            metadata[m.group(1).strip().lower()] = m.group(2).strip()
        if _AREA_RE.match(line):
            current_area = clean_area(_AREA_RE.match(line).group(1).strip()) or current_area
        for alt, src in _IMG_RE.findall(line):
            img_path = src if os.path.isabs(src) else os.path.normpath(os.path.join(base_dir, src))
            images.append(
                ImageRef(
                    path=img_path,
                    caption=alt or f"{doc_type.value} image",
                    area=current_area,
                    source=doc_type.value,
                    alt=alt,
                )
            )
        raw_parts.append(line.rstrip("\n"))

    return SourceDocument(
        doc_type=doc_type,
        title=title or os.path.basename(path),
        raw_text="\n".join(raw_parts),
        images=images,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def load_document(
    path: str,
    doc_type: DocType,
    images_dir: Optional[str] = None,
    title: Optional[str] = None,
) -> SourceDocument:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return load_pdf(path, doc_type, images_dir=images_dir, title=title)
    return load_text(path, doc_type, images_dir=images_dir, title=title)
