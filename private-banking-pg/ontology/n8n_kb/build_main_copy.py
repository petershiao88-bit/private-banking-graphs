"""Build the current native Jev Decisions workflows; preserve live credentials by reference."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("build_evidence_workflow.py")),run_name="__main__")
