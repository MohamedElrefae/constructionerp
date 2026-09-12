"""Phase 2 verification only; reuse frozen disposable fixtures unchanged."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "orchestrator"), str(ROOT / "orchestrator/tests")]
spec = importlib.util.spec_from_file_location("frozen_fixturedefs", ROOT / "orchestrator/tests/conftest.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
repo = module.repo
configured = module.configured
