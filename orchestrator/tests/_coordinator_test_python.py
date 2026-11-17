#!/usr/bin/env python3
"""Test-only Python entry point for coordinator subprocess integration tests.

It intercepts only the dashboard API module invocation and injects the local
synthetic launcher subclass. Other Python commands pass through unchanged.
This file is selected only by the test fixture's ORCHESTRATOR_PYTHON setting.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

if sys.argv[1:3] != ["-m", "orchestrator.dashboard_api"]:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])

from engine import Engine
from t3_supervisor_client import SupervisorLauncher

from orchestrator import dashboard_api


class SyntheticWorkflowLauncher(SupervisorLauncher):
    allow_builder_for_tests = True


def supervisor_engine(root, socket_path, token_file):
    token = Path(token_file).read_text().strip()
    policy_path = Path(root) / "orchestrator/launch_policy.json"
    allowed = []
    if policy_path.is_file():
        allowed = list((json.loads(policy_path.read_text()) or {}).get("allowed_models") or [])
    return Engine(root, launcher=SyntheticWorkflowLauncher(root, socket_path, token, allowed_models=allowed))


dashboard_api._supervisor_engine = supervisor_engine
sys.argv = [sys.argv[0], *sys.argv[3:]]
dashboard_api.main()
