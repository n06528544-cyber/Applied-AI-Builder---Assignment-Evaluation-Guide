# DDR Report Generator — Applied AI Builder Assignment

> **AI Generalist | Applied AI Builder — DDR Report Generation**
>
> An AI workflow that reads a site **Inspection Report** and a **Thermal
> Report** (text + images), reconciles them, and produces a client-ready
> **DDR (Detailed Diagnostic Report)** with the exact 7-section structure the
> brief requires — handling duplicates, conflicts, and missing data, and
> placing supporting images in the right sections.

This repository is a complete, production-grade deliverable. It runs
**out-of-the-box with no API key** (a deterministic extractor is the default
engine) and can optionally use an LLM (OpenAI / Anthropic / Ollama) for
unstructured documents.

---

## 1. What it does

| Requirement (from the brief) | How this project satisfies it |
| --- | --- |
| Extract relevant observations | `src/ddr/extraction.py` turns raw text into structured `Observation`s (area, description, severity, temperature, anomaly). |
| Combine inspection + thermal logically | `src/ddr/pipeline.py` aligns areas across documents (even when named differently) and merges findings. |
| Avoid duplicate points | Fuzzy similarity de-duplication (`difflib`) within each area. |
| Handle missing / conflicting details | Explicit conflict detection (e.g. "no defect" vs thermal anomaly) and a dedicated *Missing or Unclear* section that writes **"Not Available"**. |
| Client-friendly report | Simple language, severity badges, clear tables; no unnecessary jargon. |
| Extract **and place images** | `src/ddr/ingest.py` pulls embedded PDF images / markdown image refs and `src/ddr/report.py` embeds them under the correct area ("Image Not Available" if missing). |
| Generalises to similar reports | Format-agnostic ingestion (PDF / Markdown / text) + editable rule base. |

### Output structure (always produced)

1. Property Issue Summary
2. Area-wise Observations (with images + conflict call-outs)
3. Probable Root Cause
4. Severity Assessment (with reasoning)
5. Recommended Actions
6. Additional Notes
7. Missing or Unclear Information

---

## 2. Architecture

```
┌────────────┐   ┌────────────┐
│ Inspection │   │  Thermal   │   (PDF / .md / .txt  + images)
│  Report    │   │  Report    │
└─────┬──────┘   └─────▲──────┘
      │  ingest (text + image extraction)
      ▼                │
┌─────────────────────────────┐
│  extraction (heuristic/LLM) │  raw text  ->  Observation[]
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│  pipeline (reconcile)       │  merge · dedupe · conflict · severity
│                             │  root-cause · actions · missing
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│  report (render)            │  Markdown · HTML(+images) · PDF · JSON
└─────────────────────────────┘
```

Key design choices (the "system thinking" the brief evaluates):

- **Explainable, not a black box.** Every decision (merge, severity, conflict)
  is a transparent rule that produces human-readable reasoning, so output is
  auditable and reliable.
- **Graceful degradation.** If an LLM is configured but fails, the system
  falls back to the heuristic extractor instead of crashing.
- **No fabrication.** The extractor only uses facts present in the source
  documents; unknown fields become *"Not Available"*.
- **Generalises.** Ingestion is format-agnostic and the knowledge base
  (`_ROOT_CAUSE_RULES`, `_ACTION_RULES`) is editable without code changes.

---

## 3. Quick start

```bash
# 1. create & activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. install
pip install -r requirements.txt
pip install -e .            # registers the `ddr` CLI

# 3. run the bundled demo (Markdown sample inputs)
ddr demo

# 4. (optional) generate realistic sample PDFs, then run on those
ddr make-samples
ddr generate --inspection samples/inputs/inspection_report.pdf \
             --thermal samples/inputs/thermal_report.pdf \
             --out samples/output
```

Outputs land in `samples/output/`: `DDR_Report.md`, `DDR_Report.html`
(images embedded as base64), `DDR_Report.pdf`, and `DDR_Report.json`.

### Streamlit UI (optional)

```bash
streamlit run src/ddr/app.py
```

Upload the two reports, click **Generate DDR**, preview inline, download.

---

## 4. Using your own documents

Drop in any **Inspection Report** and **Thermal Report** as PDF (with embedded
images) or Markdown/text. The system:

- Extracts text and images from each page (PyMuPDF for PDFs).
- Parses area sections and temperature readings.
- Reconciles the two sources and renders the DDR.

To enable an LLM for messy/free-form PDFs, copy `.env.example` to `.env`, set
`DDR_LLM_API_KEY`, and edit `config.yaml`:

```yaml
llm:
  provider: openai        # openai | anthropic | ollama
  model: gpt-4o-mini
```

---

## 5. Project layout

```
.
├── config.yaml                  # runtime configuration
├── requirements.txt
├── pyproject.toml               # packaging + `ddr` console script
├── Dockerfile / Makefile        # containerised run
├── conftest.py                  # pytest path setup
├── src/ddr/
│   ├── models.py                # typed dataclasses (Observation, DDRReport, ...)
│   ├── config.py                # config loader w/ defaults
│   ├── ingest.py                # PDF + Markdown/text ingestion (text + images)
│   ├── extraction.py            # heuristic + LLM observation extraction
│   ├── llm.py                   # pluggable LLM client (OpenAI/Anthropic/Ollama)
│   ├── pipeline.py              # reconciliation core (merge/dedupe/conflict/severity)
│   ├── report.py                # Markdown / HTML(+img) / PDF renderers
│   ├── cli.py                   # `ddr generate | demo | make-samples`
│   └── app.py                   # Streamlit UI
├── tests/                       # pytest suite (extraction, pipeline, report)
└── samples/
    ├── inputs/                  # sample inspection + thermal reports (.md/.pdf) + images
    ├── build_sample_pdfs.py     # regenerate the sample PDFs
    └── output/                  # DDR_Example.* (the demonstration deliverable)
```

---

## 6. Tests

```bash
pytest -q
```

Covers: temperature/anomaly extraction, multi-area parsing, area alignment,
conflict detection, missing-data flagging, root-cause/action inference,
de-duplication, and renderer output (all 7 sections present).

---

## 7. Evaluation mapping

| Criterion | Where it is addressed |
| --- | --- |
| Accuracy of extracted info | `extraction.py` (temperatures, anomalies, areas) |
| Logical merging of inspection + thermal | `pipeline.py` area alignment + merge |
| Handling missing/conflicting | conflict detection + *Missing or Unclear* section |
| Clarity of final DDR | `report.py` (badges, tables, plain language) |
| System thinking & reliability | modular pipeline, graceful LLM fallback, tests, config |

---

## 8. Limitations & how I would improve it

**Limitations**
- The default extractor is rule/keyword based; it handles the common
  inspection/thermal vocabulary well but will misread novel phrasing.
- Severity is inferred from keywords + thermal delta, not from a calibrated
  risk model.
- OCR is not included — scanned (image-only) PDFs need a pre-OCR step.
- "Probable root cause" uses a transparent lookup, not causal inference.

**Improvements**
- Add an OCR stage (e.g. Tesseract / cloud Vision) for scanned PDFs.
- Use the LLM path as the primary extractor with the heuristic as a
  validation cross-check (consistency voting).
- Introduce a calibrated severity model trained on labelled DDRs.
- Add a human-in-the-loop review UI and a versioned report audit trail.
- Containerise as a hosted API + front-end for a shareable live demo link.

See `docs/SUBMISSION.md` for the Loom video script, submission checklist, and
live-demo / Google Drive instructions.
