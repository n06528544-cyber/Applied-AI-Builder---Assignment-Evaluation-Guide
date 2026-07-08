# Submission Kit — Applied AI Builder (DDR Report Generation)

This document covers the *assignment deliverables* that are not pure code:

- a **3–5 minute Loom video script**,
- a **submission checklist**, and
- instructions for the **live/demo link**, **GitHub repo**, and **Google Drive** folder.

---

## 1. Loom video script (≈4 minutes)

> Record a Loom walking through the repo. Speak to each bullet; keep it
> conversational.

**0:00 – 0:30 · What I built**
- "I built an AI workflow that turns a site *Inspection Report* and a *Thermal
  Report* into a client-ready **DDR** with the exact 7 sections the brief asks
  for."
- Show the repo tree (`src/ddr/...`) and the sample inputs + the generated
  `samples/output/DDR_Example.html`.

**0:30 – 1:30 · How it works**
- Ingestion (`ingest.py`): pulls text **and embedded images** from PDFs, plus
  Markdown/text. Show `samples/inputs/`.
- Extraction (`extraction.py`): free text → structured `Observation`s
  (area, severity, temperature, anomaly). Note it runs with **no API key**
  (deterministic) and can optionally use an LLM.
- Reconciliation (`pipeline.py`): aligns areas even when named differently
  ("Roof Membrane (Plant Room)" vs "Roof / Plant Room"), de-duplicates,
  detects conflicts, assigns severity *with reasoning*, infers root cause and
  actions, and flags missing data.
- Rendering (`report.py`): Markdown / HTML (images embedded) / PDF / JSON.

**1:30 – 2:30 · The result**
- Open `DDR_Example.html`: walk the 7 sections. Highlight:
  - The **roof conflict** (inspection said "no defect" but thermal shows a
    cool moisture patch) — explicitly called out.
  - **Images placed under the correct area** (thermal panel, roof patch,
    ceiling stain, wall crack).
  - The **Missing or Unclear** section writing *"Not Available"* for areas
    with no thermal scan.

**2:30 – 3:15 · Limitations**
- Rule/keyword extraction (great for the common vocab, not novel phrasing).
- No OCR yet for scanned PDFs.
- Severity is heuristic, not a calibrated model.
- Root cause is a transparent lookup, not causal inference.

**3:15 – 4:00 · How I'd improve it**
- OCR stage for scanned docs; LLM-as-primary with heuristic cross-check;
  calibrated severity model; human-in-the-loop review UI; hosted API + front
  end for a live link.

---

## 2. Submission checklist

- [ ] `DDR_Report` generated from the provided inputs (Markdown + HTML + PDF in `samples/output/`).
- [ ] `DDR_Example.*` committed as the worked demonstration.
- [ ] Sample inputs present (`samples/inputs/`) including the 4 images.
- [ ] `README.md` explains architecture, run steps, and evaluation mapping.
- [ ] `pytest` passes.
- [ ] Loom video recorded using the script above.
- [ ] GitHub repo created, code pushed, `README` rendered.
- [ ] Live/demo link added (Streamlit Community Cloud or Hugging Face — see below).
- [ ] Single Google Drive folder (named with your full name) containing:
  - this repo (or a ZIP),
  - `DDR_Example.pdf`,
  - `DDR_Example.html`,
  - the Loom link (as a `.txt` or in a `README`),
  - the GitHub + live links.

---

## 3. Live / demo link (no card needed)

**Option A — Streamlit Community Cloud (recommended, free)**
1. Push the repo to GitHub.
2. Go to https://share.streamlit.io, sign in, "New app", pick the repo,
   set the entry point to `src/ddr/app.py`, deploy.
3. Share the resulting `*.streamlit.app` URL.

**Option B — Hugging Face Spaces**
1. Create a Space with the Streamlit SDK.
2. Upload the repo; set `src/ddr/app.py` as the app file.
3. Share the Space URL.

> Note: the bundled sample inputs + `samples/output/DDR_Example.html` already
> constitute a fully working, offline demonstration you can open directly.

---

## 4. Google Drive folder structure

```
<Your Full Name>/
├── README.md                      # points to repo, video, live link
├── DDR_Report_Example.pdf
├── DDR_Report_Example.html
├── DDR_Generator_Source.zip       # the whole repo
├── Loom_Link.txt                  # https://www.loom.com/share/...
├── GitHub_Link.txt                # https://github.com/<you>/ddr-report-generator
└── Live_Demo_Link.txt             # https://<you>.streamlit.app
```

Share **only this one folder link** with the reviewer.
