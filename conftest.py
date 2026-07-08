"""Pytest root configuration: make the `ddr` package importable from `src/`."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)  # allow `from samples...` if needed
