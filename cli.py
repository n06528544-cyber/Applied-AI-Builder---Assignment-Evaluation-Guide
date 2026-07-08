"""Command-line interface for the DDR Report Generator."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

# Allow running directly (e.g. `python src/ddr/cli.py`) by making the `ddr`
# package and the `samples/` folder importable from any working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))  # .../src/ddr
_SRC = os.path.dirname(_HERE)                        # .../src
_ROOT = os.path.dirname(_SRC)                        # repo root
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# pylint: disable=wrong-import-position
from ddr.config import load_config
from ddr.ingest import load_document
from ddr.llm import LLMClient
from ddr.models import DocType
from ddr.pipeline import build_report
from ddr.report import render_html, render_markdown, render_pdf
# pylint: enable=wrong-import-position


def _build(inspection_path, thermal_path, config, name, date, out_dir):
    inspection = load_document(inspection_path, DocType.INSPECTION)
    thermal = load_document(thermal_path, DocType.THERMAL)
    client = LLMClient(config)
    report = build_report(inspection, thermal, config, llm_client=client, property_name=name, report_date=date)
    os.makedirs(out_dir, exist_ok=True)
    written: List[str] = []

    md = render_markdown(report)
    md_path = os.path.join(out_dir, "DDR_Report.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    written.append(md_path)

    html = render_html(report, brand=config.get("report", {}).get("brand_name", "Diagnostic Reports"))
    html_path = os.path.join(out_dir, "DDR_Report.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    written.append(html_path)

    try:
        pdf_path = os.path.join(out_dir, "DDR_Report.pdf")
        render_pdf(report, pdf_path, brand=config.get("report", {}).get("brand_name", "Diagnostic Reports"))
        written.append(pdf_path)
    except Exception as exc:
        print(f"[warn] PDF export skipped: {exc}", file=sys.stderr)

    json_path = os.path.join(out_dir, "DDR_Report.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2)
    written.append(json_path)

    return report, written


def generate_cmd(args):
    config = load_config(args.config)
    report, written = _build(args.inspection, args.thermal, config, args.name, args.date, args.out)
    print(f"DDR generated for: {report.property_name} ({len(report.areas)} areas)")
    for w in written:
        print(f"  - {w}")


def demo_cmd(args):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
    insp = os.path.join(root, "samples", "inputs", "inspection_report.md")
    therm = os.path.join(root, "samples", "inputs", "thermal_report.md")
    out = args.out or os.path.join(root, "samples", "output")
    if not os.path.exists(insp) or not os.path.exists(therm):
        print("Sample inputs not found. Run `ddr make-samples` first.", file=sys.stderr)
        sys.exit(1)
    config = load_config(args.config)
    report, written = _build(insp, therm, config, None, None, out)
    print(f"Demo DDR generated ({len(report.areas)} areas):")
    for w in written:
        print(f"  - {w}")


def make_samples_cmd(args):
    try:
        from samples.build_sample_pdfs import build as build_pdfs
    except Exception:
        sys.path.insert(0, os.getcwd())
        from samples.build_sample_pdfs import build as build_pdfs
    build_pdfs()
    print("Sample PDFs written to samples/inputs/.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="ddr", description="DDR Report Generator (Applied AI Builder)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate a DDR from inspection + thermal inputs")
    g.add_argument("--inspection", required=True, help="Inspection report (.pdf/.md/.txt)")
    g.add_argument("--thermal", required=True, help="Thermal report (.pdf/.md/.txt)")
    g.add_argument("--out", default="samples/output", help="Output directory")
    g.add_argument("--config", default="config.yaml", help="Config YAML path")
    g.add_argument("--name", default=None, help="Property name override")
    g.add_argument("--date", default=None, help="Report date override")
    g.set_defaults(func=generate_cmd)

    d = sub.add_parser("demo", help="Run on the bundled sample inputs")
    d.add_argument("--out", default=None)
    d.add_argument("--config", default="config.yaml")
    d.set_defaults(func=demo_cmd)

    m = sub.add_parser("make-samples", help="Generate sample PDF inputs")
    m.set_defaults(func=make_samples_cmd)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
