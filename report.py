"""Report rendering: DDR -> Markdown / HTML / PDF.

The HTML renderer embeds images as base64 data URIs when the source files are
present, producing a single self-contained file that renders correctly anywhere
(including the in-app preview and email attachments).
"""
from __future__ import annotations

import base64
import mimetypes
import os
from typing import List

from .models import DDRReport, ImageRef, Severity

_SEV_CLASS = {
    Severity.LOW: "sev-low",
    Severity.MEDIUM: "sev-medium",
    Severity.HIGH: "sev-high",
    Severity.CRITICAL: "sev-critical",
}


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def render_markdown(report: DDRReport) -> str:
    lines: List[str] = []
    lines.append(f"# Detailed Diagnostic Report (DDR)")
    lines.append("")
    lines.append(f"**Property:** {report.property_name}  ")
    lines.append(f"**Date:** {report.report_date}  ")
    lines.append(f"**Prepared by:** {report.prepared_by}")
    lines.append("")

    lines.append("## 1. Property Issue Summary")
    lines.append("")
    lines.append(report.summary)
    lines.append("")

    lines.append("## 2. Area-wise Observations")
    lines.append("")
    for i, a in enumerate(report.areas, 1):
        lines.append(f"### 2.{i} {a.area}")
        if a.combined_notes:
            for n in a.combined_notes:
                lines.append(f"- {n}")
        else:
            lines.append("- Not Available")
        if a.images:
            lines.append("")
            lines.append("**Supporting images:**")
            for im in a.images:
                rel = _relative_path(im.path)
                lines.append(f"- ![{im.caption or im.alt or a.area}]({rel})")
        if a.conflicts:
            lines.append("")
            lines.append("**Conflicts:**")
            for c in a.conflicts:
                lines.append(f"- {c}")
        lines.append("")

    lines.append("## 3. Probable Root Cause")
    lines.append("")
    for a in report.areas:
        lines.append(f"- **{a.area}:** {a.probable_root_cause}")
    lines.append("")

    lines.append("## 4. Severity Assessment")
    lines.append("")
    lines.append("| Area | Severity | Reasoning |")
    lines.append("| --- | --- | --- |")
    for a in report.areas:
        lines.append(f"| {a.area} | {a.severity.value} | {a.severity_reasoning} |")
    lines.append("")

    lines.append("## 5. Recommended Actions")
    lines.append("")
    for a in report.areas:
        lines.append(f"### {a.area}")
        if a.recommended_actions:
            for act in a.recommended_actions:
                lines.append(f"- {act}")
        else:
            lines.append("- Not Available")
        lines.append("")

    lines.append("## 6. Additional Notes")
    lines.append("")
    for n in report.additional_notes:
        lines.append(f"- {n}")
    lines.append("")

    lines.append("## 7. Missing or Unclear Information")
    lines.append("")
    if report.missing_info:
        for m in report.missing_info:
            lines.append(f"- {m}")
    else:
        lines.append("- None identified.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _embed_image(im: ImageRef) -> str:
    """Return an <img> tag; embeds base64 when the file is readable."""
    rel = _relative_path(im.path)
    alt = (im.alt or im.caption or im.area or "image").replace('"', "")
    if os.path.exists(im.path):
        mime = mimetypes.guess_type(im.path)[0] or "image/png"
        with open(im.path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        src = f"data:{mime};base64,{data}"
    else:
        src = rel  # fallback to path (may not resolve in preview)
    return f'<img src="{src}" alt="{alt}" class="fig"/>'


def _relative_path(path: str) -> str:
    # make paths relative to cwd for portability
    try:
        return os.path.relpath(path)
    except Exception:
        return path


def render_html(report: DDRReport, brand: str = "Diagnostic Reports") -> str:
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append(f"<title>DDR - {report.property_name}</title>")
    parts.append("<style>")
    parts.append(_CSS)
    parts.append("</style></head><body>")
    parts.append(f'<header><div class="brand">{brand}</div><h1>Detailed Diagnostic Report</h1>'
                 f'<div class="meta"><span><b>Property:</b> {report.property_name}</span>'
                 f'<span><b>Date:</b> {report.report_date}</span>'
                 f'<span><b>Prepared by:</b> {report.prepared_by}</span></div></header>')

    parts.append('<section><h2>1. Property Issue Summary</h2><p>' + report.summary + "</p></section>")

    parts.append('<section><h2>2. Area-wise Observations</h2>')
    for i, a in enumerate(report.areas, 1):
        parts.append(f'<div class="area"><h3>2.{i} {a.area} '
                     f'<span class="badge {_SEV_CLASS[a.severity]}">{a.severity.value}</span></h3>')
        if a.combined_notes:
            parts.append("<ul>")
            for n in a.combined_notes:
                parts.append(f"<li>{_esc(n)}</li>")
            parts.append("</ul>")
        else:
            parts.append("<p>Not Available</p>")
        if a.images:
            parts.append('<div class="figs">')
            for im in a.images:
                parts.append(f'<figure>{_embed_image(im)}<figcaption>{_esc(im.caption or im.alt or a.area)}</figcaption></figure>')
            parts.append("</div>")
        if a.conflicts:
            parts.append('<div class="conflict"><b>Conflict:</b><ul>')
            for c in a.conflicts:
                parts.append(f"<li>{_esc(c)}</li>")
            parts.append("</ul></div>")
        parts.append("</div>")
    parts.append("</section>")

    parts.append('<section><h2>3. Probable Root Cause</h2><ul>')
    for a in report.areas:
        parts.append(f"<li><b>{_esc(a.area)}:</b> {_esc(a.probable_root_cause)}</li>")
    parts.append("</ul></section>")

    parts.append('<section><h2>4. Severity Assessment</h2>')
    parts.append('<table><thead><tr><th>Area</th><th>Severity</th><th>Reasoning</th></tr></thead><tbody>')
    for a in report.areas:
        parts.append(f"<tr><td>{_esc(a.area)}</td>"
                     f'<td><span class="badge {_SEV_CLASS[a.severity]}">{a.severity.value}</span></td>'
                     f"<td>{_esc(a.severity_reasoning)}</td></tr>")
    parts.append("</tbody></table></section>")

    parts.append('<section><h2>5. Recommended Actions</h2>')
    for a in report.areas:
        parts.append(f"<h3>{_esc(a.area)}</h3>")
        if a.recommended_actions:
            parts.append("<ul>" + "".join(f"<li>{_esc(x)}</li>" for x in a.recommended_actions) + "</ul>")
        else:
            parts.append("<p>Not Available</p>")
    parts.append("</section>")

    parts.append('<section><h2>6. Additional Notes</h2><ul>')
    for n in report.additional_notes:
        parts.append(f"<li>{_esc(n)}</li>")
    parts.append("</ul></section>")

    parts.append('<section><h2>7. Missing or Unclear Information</h2><ul>')
    if report.missing_info:
        for m in report.missing_info:
            parts.append(f"<li>{_esc(m)}</li>")
    else:
        parts.append("<li>None identified.</li>")
    parts.append("</ul></section>")

    parts.append('<footer>Generated by the DDR Report Generator &middot; Applied AI Builder assignment deliverable.</footer>')
    parts.append("</body></html>")
    return "\n".join(parts)


_CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1f2933;--muted:#66707a;--line:#e3e8ee;--brand:#0b5c8a;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.55;}
header{background:linear-gradient(135deg,#0b5c8a,#0e7ab5);color:#fff;padding:28px 36px;}
header .brand{font-size:12px;letter-spacing:2px;text-transform:uppercase;opacity:.85}
header h1{margin:6px 0 12px;font-size:26px}
.meta{display:flex;flex-wrap:wrap;gap:18px;font-size:13px;opacity:.95}
section{max-width:980px;margin:24px auto;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px 26px;}
h2{border-bottom:2px solid var(--line);padding-bottom:8px;color:var(--brand);font-size:20px}
h3{margin:18px 0 8px;font-size:16px}
.area{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0;background:#fcfdff}
.figs{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px}
figure{margin:0;max-width:320px}
.fig{width:100%;border-radius:8px;border:1px solid var(--line)}
figcaption{font-size:12px;color:var(--muted);margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#eef3f7}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.sev-low{background:#3a9d4e}.sev-medium{background:#d99500}.sev-high{background:#d9531e}.sev-critical{background:#c0182b}
.conflict{background:#fff4f4;border:1px solid #f3c2c2;color:#8a1f1f;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:14px}
ul{margin:8px 0;padding-left:20px}
footer{text-align:center;color:var(--muted);font-size:12px;padding:24px}
"""

# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def render_pdf(report: DDRReport, out_path: str, brand: str = "Diagnostic Reports") -> str:
    html = render_html(report, brand=brand)
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=os.getcwd()).write_pdf(out_path)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"PDF export failed ({exc}). Install weasyprint or export HTML instead.") from exc
    return out_path


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
