"""Seed the narrow ERPNext baseline required by the CI business tests.

Invoke from the CI disposable ``test_site`` after installing Construction and
before the configured test modules. Company insertion uses ERPNext's native
controller so its standard chart, departments, warehouses, and defaults are
created through the same lifecycle used by ERPNext setup.

The company intentionally matches ERPNext's canonical test company
(``erpnext/setup/doctype/company/test_records.json``: ``_Test Company``,
India, INR, Standard chart). Frappe's legacy ``FrappeTestCase`` preparation
preloads ERPNext's standard test records (Purchase Invoice, Fiscal Year, ...)
for this company; a different currency makes those records fail validation,
and a different company name leaves them unseeded.
"""

import os

import frappe


COMPANY_NAME = "_Test Company"
COMPANY_ABBR = "_TC"
COMPANY_CURRENCY = "INR"
COMPANY_COUNTRY = "India"


def seed():
    """Create/reuse only this identified fixture, failing closed elsewhere."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Business fixtures may only be seeded in GitHub Actions")
    if frappe.local.site != "test_site":
        raise RuntimeError("Business fixtures are restricted to the disposable test_site")
    if not frappe.conf.get("allow_tests"):
        raise RuntimeError("Business fixtures require allow_tests on the disposable test site")

    try:
        companies = frappe.get_all("Company", pluck="name", limit_page_length=0)
        if any(name != COMPANY_NAME for name in companies):
            raise RuntimeError(f"Refusing to seed over unrecognized Companies: {companies!r}")

        if frappe.db.exists("Company", COMPANY_NAME):
            company = frappe.get_doc("Company", COMPANY_NAME)
            _assert_fixture_company(company)
        else:
            _ensure_transit_warehouse_type()
            company = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": COMPANY_NAME,
                    "abbr": COMPANY_ABBR,
                    "default_currency": COMPANY_CURRENCY,
                    "country": COMPANY_COUNTRY,
                    "create_chart_of_accounts_based_on": "Standard Template",
                    "chart_of_accounts": "Standard",
                    "enable_perpetual_inventory": 0,
                }
            ).insert(ignore_permissions=True)
            _assert_fixture_company(company)

        _ensure_transit_warehouse_type()
        _ensure_current_fiscal_year()
        global_defaults = frappe.get_doc("Global Defaults")
        global_defaults.update(
            {
                "default_company": company.name,
                "default_currency": COMPANY_CURRENCY,
                "country": COMPANY_COUNTRY,
            }
        )
        global_defaults.save(ignore_permissions=True)

        final_companies = frappe.get_all("Company", pluck="name", limit_page_length=0)
        if final_companies != [COMPANY_NAME]:
            raise RuntimeError(f"Unexpected Company rows after CI fixture setup: {final_companies!r}")
        _assert_fixture_company(frappe.get_doc("Company", COMPANY_NAME))
        if frappe.db.get_single_value("Global Defaults", "default_company") != COMPANY_NAME:
            raise RuntimeError("Global Defaults did not retain the CI fixture Company")
        if frappe.db.get_single_value("Global Defaults", "default_currency") != COMPANY_CURRENCY:
            raise RuntimeError("Global Defaults did not retain the CI fixture currency")
        if frappe.db.get_single_value("Global Defaults", "country") != COMPANY_COUNTRY:
            raise RuntimeError("Global Defaults did not retain the CI fixture country")

        frappe.db.commit()
        return COMPANY_NAME
    except Exception:
        frappe.db.rollback()
        raise


def _ensure_transit_warehouse_type():
    if not frappe.db.exists("Warehouse Type", "Transit"):
        frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(
            ignore_permissions=True
        )


def _ensure_current_fiscal_year():
    """Seed one active calendar-year Fiscal Year covering the current date.

    A bare ``bench new-site`` has no Fiscal Year (ERPNext's setup wizard
    normally creates one), so report defaults that resolve ``get_fiscal_year``
    fail closed. The document intentionally has no ``companies`` rows: ERPNext
    applies company-less Fiscal Years to every Company, which is how the
    report tests exercise a non-installed company label (for example the
    ``Elrefae`` filters in the bilingual statement tests). CI evidence shows
    the legacy test-record preparation does not create Fiscal Year rows, so
    this company-less year is the only source and cannot overlap. The year is
    derived from the current date so the fixture stays valid on later CI dates.
    """
    from erpnext.accounts.utils import get_fiscal_year
    from frappe.utils import add_days, add_years, getdate

    today = getdate(frappe.utils.today())
    year = str(today.year)
    existing = get_fiscal_year(
        date=today,
        company=COMPANY_NAME,
        verbose=0,
        as_dict=True,
        raise_on_missing=False,
    )
    if existing:
        return existing.name
    if frappe.db.exists("Fiscal Year", year):
        raise RuntimeError(f"Refusing to seed over unrecognized Fiscal Year: {year!r}")
    start = getdate(f"{year}-01-01")
    end = add_days(add_years(start, 1), -1)
    fiscal_year = frappe.get_doc(
        {
            "doctype": "Fiscal Year",
            "year": year,
            "year_start_date": start,
            "year_end_date": end,
        }
    ).insert(ignore_permissions=True)
    return fiscal_year.name


def _assert_fixture_company(company):
    expected = {
        "name": COMPANY_NAME,
        "company_name": COMPANY_NAME,
        "abbr": COMPANY_ABBR,
        "default_currency": COMPANY_CURRENCY,
        "country": COMPANY_COUNTRY,
        "chart_of_accounts": "Standard",
    }
    actual = {field: company.get(field) for field in expected}
    if actual != expected:
        raise RuntimeError(f"Existing CI Company does not match the recognized fixture: {actual!r}")
