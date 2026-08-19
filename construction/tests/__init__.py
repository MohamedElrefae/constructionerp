import unittest

import frappe

# Applied at test-package import time: the standard runner imports
# construction.tests BEFORE preloading test records, so the guard is in
# place exactly when the bootstrap needs it and never in production.
try:
    from construction.tests.test_bootstrap_guard import apply_test_generator_guard

    apply_test_generator_guard()
except Exception:
    pass


def run_vfc_tests():
    """Run the VFC backend test suite and return results.

    Can be called via:
        bench --site v16.localhost execute construction.tests.run_vfc_tests
    """
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    modules = [
        "construction.tests.test_vfc_backend",
    ]

    for module in modules:
        try:
            suite.addTests(loader.loadTestsFromName(module))
        except Exception as e:
            frappe.msgprint(f"Error loading {module}: {e}")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "was_successful": result.wasSuccessful(),
        "failure_details": [(test.id(), str(err)) for test, err in result.failures],
        "error_details": [(test.id(), str(err)) for test, err in result.errors],
    }


def run_quantity_revision_tests():
    """Run the VO Quantity Revision test suite and return results.

    Can be called via:
        bench --site v16.localhost execute construction.tests.run_quantity_revision_tests
    """
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    modules = [
        "construction.tests.test_quantity_revisions",
        "construction.tests.test_variation_orders",
        "construction.tests.test_boq_link_queries",
    ]

    for module in modules:
        try:
            suite.addTests(loader.loadTestsFromName(module))
        except Exception as e:
            frappe.msgprint(f"Error loading {module}: {e}")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "was_successful": result.wasSuccessful(),
        "failure_details": [(test.id(), str(err)) for test, err in result.failures],
        "error_details": [(test.id(), str(err)) for test, err in result.errors],
    }
