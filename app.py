"""Optional Streamlit UI for the DDR Report Generator.

Run with:  streamlit run src/ddr/app.py
Upload an Inspection report and a Thermal report, click Generate, and preview
the DDR inline (HTML) with a download button.
"""
from __future__ import annotations

import os
import sys
import tempfile

import streamlit as st

# Allow running directly (e.g. `streamlit run src/ddr/app.py`) by making the
# `ddr` package importable regardless of the current working directory.
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# pylint: disable=wrong-import-position
from ddr.config import load_config
from ddr.ingest import load_document
from ddr.llm import LLMClient
from ddr.models import DocType
from ddr.pipeline import build_report
from ddr.report import render_html, render_markdown
# pylint: enable=wrong-import-position


def main():
    """Streamlit UI: upload an inspection + thermal report and preview the DDR."""
    st.set_page_config(page_title="DDR Report Generator", layout="wide")
    st.title("DDR Report Generator")
    st.caption(
        "Applied AI Builder - merge inspection + thermal data into a "
        "client-ready DDR."
    )

    with st.sidebar:
        st.header("Inputs")
        insp_file = st.file_uploader("Inspection report", type=["pdf", "md", "txt"])
        therm_file = st.file_uploader("Thermal report", type=["pdf", "md", "txt"])
        name = st.text_input("Property name (optional)")
        date = st.text_input("Report date (optional)")
        go = st.button("Generate DDR", type="primary")

    if go and insp_file and therm_file:
        with st.spinner("Extracting and reconciling..."):
            insp_path = _save(insp_file)
            therm_path = _save(therm_file)
            inspection = load_document(insp_path, DocType.INSPECTION)
            thermal = load_document(therm_path, DocType.THERMAL)
            config = load_config("config.yaml")
            client = LLMClient(config)
            report = build_report(
                inspection,
                thermal,
                config,
                llm_client=client,
                property_name=name or None,
                report_date=date or None,
            )
        severity = report.metadata.get("highest_severity")
        st.success(
            f"DDR ready - {len(report.areas)} area(s), highest severity {severity}"
        )

        # Text preview only; images are streamed separately below. Rendering the
        # full base64-embedded HTML via st.html marshals a huge srcdoc and can
        # OOM, so we preview as markdown and show pictures with st.image.
        preview_md = "\n".join(
            ln for ln in render_markdown(report).splitlines()
            if not ln.strip().startswith("!") and not ln.strip().startswith("- !")
        )
        st.markdown(preview_md)

        for area in report.areas:
            if area.images:
                st.subheader(f"{area.area} - images")
                for im in area.images:
                    if os.path.exists(im.path):
                        st.image(im.path, caption=im.caption or im.alt or area.area)

        report_html = render_html(
            report,
            brand=config.get("report", {}).get("brand_name", "Diagnostic Reports"),
        )
        st.download_button(
            "Download HTML",
            report_html,
            file_name="DDR_Report.html",
            mime="text/html",
        )
        st.download_button(
            "Download Markdown",
            render_markdown(report),
            file_name="DDR_Report.md",
            mime="text/markdown",
        )
    else:
        st.info("Upload both reports and press Generate.")


def _save(uploaded):
    suffix = os.path.splitext(uploaded.name)[1] or ".txt"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(uploaded.read())
    return path


if __name__ == "__main__":
    main()
