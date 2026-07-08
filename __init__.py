"""DDR Report Generator.

An Applied-AI builder that ingests a site Inspection Report and a Thermal
Report (text + images), merges and reconciles them, and emits a client-ready
DDR (Detailed Diagnostic Report) with a fixed 7-section structure.

The project is intentionally split into small, testable units:

    ingestion  -> read PDF / text / markdown, pull out text + images
    extraction -> turn raw text into structured Observations
    pipeline   -> merge, dedupe, detect conflicts/missing, assign severity
    report     -> render the DDR to HTML / PDF / Markdown
    llm        -> optional LLM provider (OpenAI / Anthropic / Ollama)
"""

__version__ = "1.0.0"
