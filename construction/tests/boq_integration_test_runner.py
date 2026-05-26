import unittest

import frappe


TARGETED_TEST_MODULES = (
	"construction.tests.test_hook_regression",
	"construction.tests.test_accounting_dimension",
	"construction.tests.test_boq_item_stage",
	"construction.tests.test_transaction_validation",
)


def run_targeted_tests():
	loader = unittest.defaultTestLoader
	suite = unittest.TestSuite()
	for module in TARGETED_TEST_MODULES:
		suite.addTests(loader.loadTestsFromName(module))

	result = unittest.TextTestRunner(verbosity=2).run(suite)
	if not result.wasSuccessful():
		frappe.throw(
			"Targeted BOQ tests failed: {0} failures, {1} errors".format(
				len(result.failures), len(result.errors)
			)
		)

	return {
		"modules": TARGETED_TEST_MODULES,
		"tests_run": result.testsRun,
		"failures": len(result.failures),
		"errors": len(result.errors),
	}
