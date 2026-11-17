"""Regression tests for the native-dispatch gate (no spawn, no network, no env leakage)."""

import inspect
import os
import unittest
from unittest import mock

from core import WorkflowError
from engine import Engine


class _TruthyLauncher:
    def __call__(self, job):
        raise AssertionError("launcher must not be invoked by the gate tests")


class _FalsyLauncher(_TruthyLauncher):
    def __bool__(self):
        return False


def _engine_with(launcher):
    engine = Engine.__new__(Engine)   # gate is a pure predicate; no store/graph needed
    engine.launcher = launcher
    return engine


class DispatchGateTests(unittest.TestCase):
    def test_no_env_refuses(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
            with self.assertRaises(WorkflowError):
                _engine_with(None)._enforce_native_dispatch_gate()

    def test_wrong_value_refuses(self):
        with mock.patch.dict(os.environ, {"ENGINE_NATIVE_DISPATCH": "true"}, clear=False):
            with self.assertRaises(WorkflowError):
                _engine_with(None)._enforce_native_dispatch_gate()

    def test_explicit_value_admits_native(self):
        with mock.patch.dict(os.environ, {"ENGINE_NATIVE_DISPATCH": "allow-native-host-access"}, clear=False):
            self.assertIsNone(_engine_with(None)._enforce_native_dispatch_gate())

    def test_truthy_launcher_skips_gate(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
            self.assertIsNone(_engine_with(_TruthyLauncher())._enforce_native_dispatch_gate())

    def test_falsy_launcher_still_refuses(self):
        """The spawn branch treats a falsy launcher as native; the gate must too."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
            with self.assertRaises(WorkflowError):
                _engine_with(_FalsyLauncher())._enforce_native_dispatch_gate()

    def test_gate_runs_before_launch_intent_and_spawn(self):
        source = inspect.getsource(Engine._dispatch)
        gate = source.index("self._enforce_native_dispatch_gate()")
        intent = source.index('"LAUNCH_INTENT"')
        spawn = source.index("subprocess.Popen(")
        launcher_call = source.index("self.launcher(job)")
        self.assertLess(gate, intent)
        self.assertLess(intent, spawn)
        self.assertLess(intent, launcher_call)


if __name__ == "__main__":
    unittest.main()
