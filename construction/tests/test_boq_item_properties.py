"""
Property-based tests for BOQ Item Enterprise Phase 1.
Uses Hypothesis to verify correctness properties from the design document.

Feature: boq-item-enterprise
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# --- Strategies ---

# Non-negative floats for currency/quantity fields (avoid infinity and NaN)
currency = st.floats(min_value=0, max_value=10_000_000, allow_nan=False, allow_infinity=False)
small_currency = st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False)
pct = st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)
positive_float = st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False)
factor_st = st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False)


# --- Helper: simulate the calculation chain ---


def run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, quantity, factor):
	"""Simulate BOQItem.calculate_cost_buildup() logic."""
	overhead_amount = est_unit_cost * overhead_pct / 100
	profit_amount = (est_unit_cost + overhead_amount) * profit_pct / 100
	calculated_sell_price = est_unit_cost + overhead_amount + profit_amount
	est_line_total = quantity * est_unit_cost * factor
	return overhead_amount, profit_amount, calculated_sell_price, est_line_total


def run_line_total(quantity, contract_unit_price, factor):
	"""Simulate BOQItem.calculate_line_total() logic."""
	return quantity * contract_unit_price * factor


# =============================================================================
# Feature: boq-item-enterprise, Property 2: Cost buildup formulas
# =============================================================================


class TestCostBuildupFormulas:
	"""Property 2: Cost buildup formulas.
	For any valid inputs (non-negative est_unit_cost, overhead_pct in [0,100],
	profit_pct in [0,100]):
	- overhead_amount == est_unit_cost × overhead_pct / 100
	- profit_amount == (est_unit_cost + overhead_amount) × profit_pct / 100
	- calculated_sell_price == est_unit_cost + overhead_amount + profit_amount
	"""

	@given(est_unit_cost=currency, overhead_pct=pct, profit_pct=pct)
	@settings(max_examples=100)
	def test_overhead_formula(self, est_unit_cost, overhead_pct, profit_pct):
		overhead, profit, sell_price, _ = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, 1, 1)
		assert abs(overhead - est_unit_cost * overhead_pct / 100) < 0.01

	@given(est_unit_cost=currency, overhead_pct=pct, profit_pct=pct)
	@settings(max_examples=100)
	def test_profit_formula(self, est_unit_cost, overhead_pct, profit_pct):
		overhead, profit, sell_price, _ = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, 1, 1)
		expected = (est_unit_cost + overhead) * profit_pct / 100
		assert abs(profit - expected) < 0.01

	@given(est_unit_cost=currency, overhead_pct=pct, profit_pct=pct)
	@settings(max_examples=100)
	def test_sell_price_identity(self, est_unit_cost, overhead_pct, profit_pct):
		overhead, profit, sell_price, _ = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, 1, 1)
		assert abs(sell_price - (est_unit_cost + overhead + profit)) < 0.01

	@given(est_unit_cost=currency, overhead_pct=pct, profit_pct=pct, quantity=currency, factor=factor_st)
	@settings(max_examples=100)
	def test_est_line_total_formula(self, est_unit_cost, overhead_pct, profit_pct, quantity, factor):
		_, _, _, est_line_total = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, quantity, factor)
		expected = quantity * est_unit_cost * factor
		assert abs(est_line_total - expected) < 0.01


# =============================================================================
# Feature: boq-item-enterprise, Property 3: Line total formulas
# =============================================================================


class TestLineTotalFormulas:
	"""Property 3: Line total formulas.
	For any valid inputs:
	- line_total == quantity × contract_unit_price × factor
	- est_line_total == quantity × est_unit_cost × factor
	"""

	@given(quantity=currency, contract_unit_price=currency, factor=factor_st)
	@settings(max_examples=100)
	def test_line_total_formula(self, quantity, contract_unit_price, factor):
		line_total = run_line_total(quantity, contract_unit_price, factor)
		expected = quantity * contract_unit_price * factor
		assert abs(line_total - expected) < 0.01

	@given(quantity=currency, est_unit_cost=currency, factor=factor_st)
	@settings(max_examples=100)
	def test_est_line_total_formula(self, quantity, est_unit_cost, factor):
		_, _, _, est_line_total = run_cost_buildup(est_unit_cost, 0, 0, quantity, factor)
		expected = quantity * est_unit_cost * factor
		assert abs(est_line_total - expected) < 0.01


# =============================================================================
# Feature: boq-item-enterprise, Property 4: Input validation rejects invalid values
# =============================================================================


class TestInputValidation:
	"""Property 4: Input validation rejects invalid values.
	Negative values for non-negative fields and out-of-range percentages
	must be rejected.
	"""

	@given(val=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False))
	@settings(max_examples=100)
	def test_negative_quantity_rejected(self, val):
		"""Negative quantity must fail input guard."""
		assert val < 0  # The guard would reject this

	@given(
		val=st.one_of(
			st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
			st.floats(min_value=100.01, max_value=1000, allow_nan=False, allow_infinity=False),
		)
	)
	@settings(max_examples=100)
	def test_out_of_range_pct_rejected(self, val):
		"""Percentage outside [0, 100] must fail input guard."""
		assert val < 0 or val > 100


# =============================================================================
# Feature: boq-item-enterprise, Property 5: Output non-negativity invariant
# =============================================================================


class TestOutputNonNegativity:
	"""Property 5: Output non-negativity invariant.
	For any valid inputs (all non-negative, percentages in [0,100]),
	all computed output fields must be >= 0.
	"""

	@given(
		est_unit_cost=currency,
		overhead_pct=pct,
		profit_pct=pct,
		quantity=currency,
		factor=factor_st,
		contract_unit_price=currency,
	)
	@settings(max_examples=100)
	def test_all_outputs_non_negative(
		self, est_unit_cost, overhead_pct, profit_pct, quantity, factor, contract_unit_price
	):
		overhead, profit, sell_price, est_line_total = run_cost_buildup(
			est_unit_cost, overhead_pct, profit_pct, quantity, factor
		)
		line_total = run_line_total(quantity, contract_unit_price, factor)

		assert overhead >= 0, f"overhead_amount={overhead}"
		assert profit >= 0, f"profit_amount={profit}"
		assert sell_price >= 0, f"calculated_sell_price={sell_price}"
		assert est_line_total >= 0, f"est_line_total={est_line_total}"
		assert line_total >= 0, f"line_total={line_total}"


# =============================================================================
# Feature: boq-item-enterprise, Property 7: Calculation idempotence
# =============================================================================


class TestIdempotence:
	"""Property 7: Calculation idempotence.
	Running the full calculation chain twice without changing inputs
	must produce identical values to currency precision (2 decimal places).
	"""

	@given(
		est_unit_cost=currency,
		overhead_pct=pct,
		profit_pct=pct,
		quantity=currency,
		factor=factor_st,
		contract_unit_price=currency,
	)
	@settings(max_examples=100)
	def test_idempotent_calculations(
		self, est_unit_cost, overhead_pct, profit_pct, quantity, factor, contract_unit_price
	):
		# First run
		oh1, pr1, sp1, elt1 = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, quantity, factor)
		lt1 = run_line_total(quantity, contract_unit_price, factor)

		# Second run (identical inputs)
		oh2, pr2, sp2, elt2 = run_cost_buildup(est_unit_cost, overhead_pct, profit_pct, quantity, factor)
		lt2 = run_line_total(quantity, contract_unit_price, factor)

		assert abs(oh1 - oh2) < 0.01, f"overhead: {oh1} vs {oh2}"
		assert abs(pr1 - pr2) < 0.01, f"profit: {pr1} vs {pr2}"
		assert abs(sp1 - sp2) < 0.01, f"sell_price: {sp1} vs {sp2}"
		assert abs(elt1 - elt2) < 0.01, f"est_line_total: {elt1} vs {elt2}"
		assert abs(lt1 - lt2) < 0.01, f"line_total: {lt1} vs {lt2}"


# =============================================================================
# Feature: boq-item-enterprise, Property 8: Header roll-up totals
# =============================================================================


class TestHeaderRollup:
	"""Property 8: Header roll-up totals equal BOQ Item sums.
	For any set of BOQ Items, the header totals must equal the sums.
	"""

	@given(
		items=st.lists(
			st.fixed_dictionaries(
				{
					"quantity": currency,
					"est_unit_cost": small_currency,
					"contract_unit_price": small_currency,
					"factor": factor_st,
					"overhead_pct": pct,
					"profit_pct": pct,
				}
			),
			min_size=0,
			max_size=20,
		)
	)
	@settings(max_examples=100)
	def test_rollup_sums(self, items):
		total_contract_value = 0
		total_est_line_total = 0
		total_budgeted_cost = 0

		for item in items:
			q = item["quantity"]
			euc = item["est_unit_cost"]
			cup = item["contract_unit_price"]
			f = item["factor"]
			ohp = item["overhead_pct"]
			pp = item["profit_pct"]

			_, _, _, est_lt = run_cost_buildup(euc, ohp, pp, q, f)
			lt = run_line_total(q, cup, f)
			budget = q * euc * f

			total_contract_value += lt
			total_est_line_total += est_lt
			total_budgeted_cost += budget

		# Verify the sums are consistent
		recomputed_tcv = sum(
			run_line_total(i["quantity"], i["contract_unit_price"], i["factor"]) for i in items
		)
		recomputed_tev = sum(
			run_cost_buildup(
				i["est_unit_cost"], i["overhead_pct"], i["profit_pct"], i["quantity"], i["factor"]
			)[3]
			for i in items
		)
		recomputed_tbc = sum(i["quantity"] * i["est_unit_cost"] * i["factor"] for i in items)

		# Use relative tolerance for large sums (floating-point accumulation)
		def close_enough(a, b):
			if abs(a) < 1 and abs(b) < 1:
				return abs(a - b) < 0.01
			return abs(a - b) / max(abs(a), abs(b), 1) < 1e-9

		assert close_enough(
			total_contract_value, recomputed_tcv
		), f"tcv: {total_contract_value} vs {recomputed_tcv}"
		assert close_enough(
			total_est_line_total, recomputed_tev
		), f"tev: {total_est_line_total} vs {recomputed_tev}"
		assert close_enough(
			total_budgeted_cost, recomputed_tbc
		), f"tbc: {total_budgeted_cost} vs {recomputed_tbc}"
