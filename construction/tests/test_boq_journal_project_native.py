"""Native regression for the Journal Entry BOQ project propagation (F44).

A Journal Entry Account row that carries a BOQ attribution (``boq_item``)
belongs to the project of the selected BOQ Header, but the native ERPNext
controller copies the ROW's ``project`` into the General Ledger entry. A BOQ
expense row saved with a blank row project therefore produced a posted GL entry
with ``project = NULL``: the cost was invisible in the project-scoped General
Ledger while the voucher itself stayed balanced.

This module exercises the REAL server save/submit/cancel lifecycle on a native
``Journal Entry``: the assertions are about persisted rows, persisted General
Ledger entries and refused operations, not about a model of the policy. The
site-less policy coverage of the same rule lives in
``construction/tests/test_boq_journal_project.py``.

Fixture setup and cleanup are owned by the suite.

NATIVE EXECUTION STATUS (2026-10-22): this module was executed by the private
CI run 39762705088 (Server job, exact commit bf103e5c2808c0e9a9683ef8f2381b70288ef029).
That run FAILED: 12 tests ran, 5 passed, 3 failed and 4 errored. Every failure
was diagnosed against the pinned vendor source (Frappe af44091716ed4e9be32720483a27d3f1937ad7fd,
ERPNext 7474d9e786277383de1242ab882f16856d17a9c9) and is corrected HERE, in the
TEST module only:

* the General Ledger read used the non-existent column ``GL Entry.voucher_name``;
  the pinned ERPNext field is ``voucher_no`` (two errors);
* the native Frappe new-document DEFAULT (a single Project User Permission
  fills the blank ``Journal Entry Account.project`` of EVERY new row) silently
  pre-filled the row project and moved the refusal of three cases to an
  earlier layer;
* the native User Permission enforcement refused the crafted mismatch before
  the application's validator could see it;
* the plain counterpart row legitimately carries the native default, so a
  hard-coded ``NULL`` expectation was an invented business policy.

The corrected module is NOT natively verified yet: it awaits an exact CI rerun
of this commit. Nothing in this file may be read as a native pass.

TWO CORRECTION ROUNDS (both TEST module only)
----------------------------------------------

Round 1 corrected the seven failures above and split the native transport
denial from the application refusal. The review of that corrected module found
two defects IN THE CORRECTION, both fixed in round 2:

* one ORIGINAL case was accidentally dropped
  (``test_a_cross_company_boq_project_is_refused_on_the_first_save``). It is
  restored here under its EXACT original name, with the layer representative,
  and it keeps the company's first-save refusal and the no-store assertion.
  The module therefore carries all 12 original cases plus the 3 new ones.
* the new transport-denial case read the INTERNAL diagnostic flag
  ``frappe.flags.has_permission_check_logs``. The pinned
  ``frappe/permissions.py::print_has_permission_check_logs`` REMOVES that flag
  before it returns, so the flag is NOT a stable observable of a refused write
  and the case raised ``TypeError`` instead of proving the refusal. The case
  now proves the native refusal with the observable native semantics only: the
  exact exception class, the absence of every application refusal message, the
  fact that the refused document was never NAMED (the pinned
  ``frappe/model/document.py::Document.insert`` checks the create permission
  BEFORE it names the document, so an unnamed document proves that the
  application's validation chain never ran), a non-persistence readback, and an
  independent ALLOWED control that proves the same principal and the same
  fixture are accepted by the native layer.

TWO FIXTURE REPRESENTATIVES, ONE ROLE COMBINATION
--------------------------------------------------

Both representatives are created by this suite, both carry the SAME approved
role combination and both carry a real scope context. They differ ONLY in the
Project User Permission set, because that set is exactly the layer under test:

``self.user`` (the ordinary representative)
    ONE Project User Permission (the active scope project). This is the
    ordinary profile. The pinned Frappe new-document default
    (``frappe/model/create_new.py::set_user_and_static_default_values`` with
    ``frappe/permissions.py::filter_allowed_docs_for_doctype``) fills the blank
    ``project`` of EVERY new Journal Entry Account row with the ONLY allowed
    Project. That is EXISTING NATIVE behaviour and it is preserved and
    asserted, never suppressed.

``self.layer_user`` (the layer representative)
    The SAME roles and the SAME scope context, but TWO Project User
    Permissions (the scope project and the other project of the same company).
    With more than one allowed Project the native new-document default does
    not fire, so a blank row project stays blank, and the other project is
    allowed by the native transport layer so a crafted mismatch can
    legitimately REACH the application's own validation chain.

This is an isolated TEST FIXTURE permission state of a throwaway user created
by this suite. It changes no production permission, no role and no existing
person; the scope layer still restricts both representatives to the active
scope project.

Fixture rules honoured by this module:

* every fixture write runs as ``Administrator`` in ``setUp`` with
  ``ignore_permissions=True`` and only for the fixture itself;
* the direct database writes of this module are fixtures and are marked as
  such in the code. The pre-fix historical NULL simulation is performed as
  ``Administrator`` and the ordinary representative is restored immediately
  afterwards, so every tested save/submit/cancel runs as the ordinary user.
  The missing-scope-context case removes its own User Scope Context row to
  create the condition it tests;
* the tested business write always runs as the ordinary representative with
  real roles, a real scope context and a real User Permission - no
  ``ignore_permissions`` and no bypass flag on that path;
* the ordinary representative uses the EXISTING approved role combination
  (``Accounts User`` + ``Site Engineer`` + ``Projects User``). No role is
  created and no real user is changed;
* the amounts are supplied as the native controller expects them
  (``debit_in_account_currency`` / ``credit_in_account_currency`` with an
  ``exchange_rate``), because the pinned ERPNext
  ``set_amounts_in_company_currency`` RECOMPUTES ``debit``/``credit`` from
  those fields;
* the cost center, the account currency and the Fiscal Year come from the
  authoritative Company/ERPNext helpers, and every account is a leaf under an
  existing group of the same company.

Two assumptions are explicitly NOT verified by the author and must be checked
by the later stage with the ordinary Finance principal (never Administrator):

* whether Frappe's link validation accepts the DERIVED child ``project`` for a
  user whose Project access is granted through a User Permission (the suite
  grants one, so the case is realistic);
* that the derived project reaches ``GL Entry.project`` on the posted voucher
  in the installed ERPNext version (the installed controller copies the row
  project, but the posted row must be read back, not assumed).

Deliberately NOT covered here: the stored row project of the other seven
transaction DocTypes. This module proves the Journal Entry path only; the
other DocTypes are covered at the policy layer by the site-less suite.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_years, getdate, nowdate

from construction.tests.test_boq_helpers import _ensure_transit_warehouse_type, get_or_create_test_project

# The existing, approved Finance representative: the native ERPNext Accounts
# role (Journal Entry create/write/submit), the existing ERPNext Projects role
# (Project access) and the existing construction Site Engineer role (BOQ Item
# read access, required to link a BOQ Item). No role is created by this suite.
TEST_USER_ROLES = ("Accounts User", "Site Engineer", "Projects User")

EXPENSE_AMOUNT = 100
COUNTERPART_AMOUNT = 100

MISMATCH_MESSAGE = "Project mismatch"
COMPANY_MESSAGE = "does not belong to Company"
SCOPE_MESSAGE = "Scope boundary violation"
SCOPE_CONTEXT_MESSAGE = "active User Scope Context is required"


class JournalEntryBoqProjectNativeTests(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.scope_project = get_or_create_test_project()
        self.company = frappe.db.get_value("Project", self.scope_project, "company")
        self.company_currency = frappe.db.get_value("Company", self.company, "default_currency")
        self.other_project = self._make_project("_Test JE Other Scope Project", self.company)
        self.other_company = self._make_company("_Test JE Other Company", "_TJE")
        self.cross_company_project = self._make_project("_Test JE Cross Company Project", self.other_company)
        self.cost_center = self._resolve_cost_center()
        self.expense_account = self._make_leaf_account("_Test JE BOQ Expense")
        self.counterpart_account = self._make_leaf_account("_Test JE Counterpart")
        self.fiscal_year = self._ensure_fiscal_year()
        # Every BOQ fixture is created as Administrator, BEFORE the tested
        # ordinary user is used, so no fixture write ever runs as the ordinary
        # user.
        self.boq_item = self._make_boq_item(self.scope_project, "_Test JE BOQ")
        self.cross_company_item = self._make_boq_item(
            self.cross_company_project, "_Test JE Cross Company BOQ"
        )
        self.out_of_scope_item = self._make_boq_item(self.other_project, "_Test JE Out Of Scope BOQ")
        # The ordinary representative: the approved role combination, a real
        # scope context and ONE Project User Permission (the native new-document
        # default therefore fills the blank row project).
        self.user = self._make_user("ordinary", (self.scope_project,))
        # The layer representative: the SAME approved role combination and the
        # SAME scope context, with a second Project User Permission so that the
        # native default does not fire and the other project is reachable
        # through the native transport layer.
        self.layer_user = self._make_user("layer", (self.scope_project, self.other_project))
        self._set_scope_enforcement(True)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # ---------------------------------------------------------------- fixtures

    def _make_company(self, company_name, abbr):
        if frappe.db.exists("Company", company_name):
            return company_name
        _ensure_transit_warehouse_type()
        frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": company_name,
                "abbr": abbr,
                "default_currency": self.company_currency,
                "country": "India",
                "create_chart_of_accounts_based_on": "Standard Template",
                "chart_of_accounts": "Standard",
            }
        ).insert(ignore_permissions=True)
        return company_name

    def _make_project(self, label, company):
        existing = frappe.db.get_value("Project", {"project_name": label}, "name")
        if existing:
            return existing
        return (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": label,
                    "company": company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _resolve_cost_center(self):
        """The company's own default (leaf) cost center."""
        cost_center = frappe.db.get_value("Company", self.company, "cost_center")
        if cost_center and frappe.db.exists("Cost Center", cost_center):
            return cost_center
        cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
        if not cost_center:
            self.fail(f"no leaf Cost Center for company {self.company}")
        return cost_center

    def _make_leaf_account(self, account_name):
        """A leaf expense account under an EXISTING group of the same company."""
        existing = frappe.db.get_value(
            "Account", {"company": self.company, "account_name": account_name}, "name"
        )
        if existing:
            return existing
        parent = self._expense_group_account()
        return (
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": account_name,
                    "company": self.company,
                    "account_type": "Expense Account",
                    "parent_account": parent,
                    "is_group": 0,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _expense_group_account(self):
        """An existing Expense ACCOUNT GROUP of the same company.

        The pinned ERPNext standard chart creates the Expense groups with
        ``root_type = "Expense"`` and WITHOUT an ``account_type`` of their
        own ("Direct Expenses", "Indirect Expenses", "Expenses"); no account
        of that chart carries the legacy ``account_type = "Expense Account"``.
        The parent is therefore resolved by its ROOT TYPE, deterministically
        ordered by name, and the fixture fails clearly when the company has no
        Expense group at all. No root account is created and no bypass flag is
        used.
        """
        parent = frappe.db.get_value(
            "Account",
            {"company": self.company, "root_type": "Expense", "is_group": 1},
            "name",
            order_by="name",
        )
        if not parent:
            self.fail(f"no Expense group account in company {self.company}")
        return parent

    def _ensure_fiscal_year(self):
        """One active Fiscal Year covering today for this company.

        A bare ``bench new-site`` has no Fiscal Year (ERPNext's setup wizard
        normally creates one), and the General Ledger refuses to post without
        one. The existing ERPNext helper resolves it; only a missing year is
        created here, as an Administrator fixture.
        """
        from erpnext.accounts.utils import get_fiscal_year

        existing = get_fiscal_year(
            date=nowdate(),
            company=self.company,
            verbose=0,
            as_dict=True,
            raise_on_missing=False,
        )
        if existing:
            # ``erpnext.accounts.utils.get_fiscal_year(as_dict=True)`` returns
            # ONE fiscal-year mapping: it already selected ``fiscal_years[0]``
            # internally (``fiscal_year = fiscal_years[0]; return
            # fiscal_year``). The name is read from that mapping - not from
            # ``existing[0]``, which would index the mapping itself. The CI
            # business fixture (``.github/ci/business_fixtures.py``) resolves
            # the same value the same way.
            return existing.name
        year = str(getdate(nowdate()).year)
        start = getdate(f"{year}-01-01")
        end = add_days(add_years(start, 1), -1)
        return (
            frappe.get_doc(
                {
                    "doctype": "Fiscal Year",
                    "year": year,
                    "disabled": 0,
                    "year_start_date": start,
                    "year_end_date": end,
                    "companies": [{"company": self.company}],
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _make_boq_item(self, project, title):
        """A BOQ Item of a Frozen BOQ Header (a status the BOQ gate accepts)."""
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": project,
                "title": title,
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": f"{title} Structure",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc("BOQ Item", {"structure": structure.name})
        item.quantity = 10
        item.unit = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
        item.contract_unit_price = 25
        item.save(ignore_permissions=True)
        for status in ("Pricing", "Frozen"):
            header = frappe.get_doc("BOQ Header", header.name)
            header.status = status
            header.save(ignore_permissions=True)
        return item.name

    def _make_user(self, label, projects):
        """A throwaway representative of this suite.

        The approved role combination, a real User Scope Context (the active
        scope project of the fixture) and one Project User Permission per
        requested project.

        The number of Project User Permissions decides whether the NATIVE
        Frappe new-document default fires: the pinned
        ``frappe/permissions.py::filter_allowed_docs_for_doctype`` only returns
        a default document when EXACTLY ONE document is allowed for the link
        field. One permission therefore reproduces the ordinary production
        behaviour, and more than one isolates the application's own
        contribution from that native default.

        No role is created, no existing user is changed and no production
        permission is touched: these are throwaway users of the suite.
        """
        email = f"je-boq-project-{label}-{frappe.generate_hash(length=8)}@example.invalid"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "JE BOQ Project",
                "send_welcome_email": 0,
                "roles": [{"role": role} for role in TEST_USER_ROLES],
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "User Scope Context",
                "user": email,
                "company": self.company,
                "project": self.scope_project,
            }
        ).insert(ignore_permissions=True)
        for project in projects:
            if not frappe.db.exists(
                "User Permission", {"user": email, "allow": "Project", "for_value": project}
            ):
                frappe.get_doc(
                    {
                        "doctype": "User Permission",
                        "user": email,
                        "allow": "Project",
                        "for_value": project,
                        "apply_to_all_doctypes": 1,
                    }
                ).insert(ignore_permissions=True)
        return email

    @staticmethod
    def _set_scope_enforcement(enabled):
        frappe.db.set_single_value("Construction Settings", "enable_scope_context", 1 if enabled else 0)

    # ---------------------------------------------------------------- builders

    def _journal_row(self, account, debit=0, credit=0, boq_item=None, project=None, row_name=None):
        """A native Journal Entry Account row with the native amount fields.

        ``debit``/``credit`` are NOT set: the pinned ERPNext controller
        recomputes them from ``debit_in_account_currency`` /
        ``credit_in_account_currency`` and ``exchange_rate``.
        """
        row = {
            "doctype": "Journal Entry Account",
            "account": account,
            "cost_center": self.cost_center,
            "account_currency": self.company_currency,
            "exchange_rate": 1,
            "debit_in_account_currency": debit,
            "credit_in_account_currency": credit,
        }
        if row_name:
            row["name"] = row_name
        if boq_item:
            row["boq_item"] = boq_item
            row["expense_category"] = "Direct"
        if project:
            row["project"] = project
        return row

    def _new_journal_entry(self, boq_item=None, project=None, company=None):
        """A native Journal Entry with a BOQ expense row and a plain counterpart."""
        rows = [
            self._journal_row(self.expense_account, debit=EXPENSE_AMOUNT, boq_item=boq_item, project=project),
            self._journal_row(self.counterpart_account, credit=COUNTERPART_AMOUNT),
        ]
        return frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "company": company or self.company,
                "posting_date": nowdate(),
                "accounts": rows,
            }
        )

    # ---------------------------------------------------------------- helpers

    def _journal_entry_count(self):
        return frappe.db.count("Journal Entry")

    def _journal_entry_account_count(self):
        """The persisted child rows of every Journal Entry (the stored rows)."""
        return frappe.db.count("Journal Entry Account")

    def _row_project(self, doc, idx=1):
        row = doc.accounts[idx - 1]
        return frappe.db.get_value("Journal Entry Account", row.name, "project")

    def _control_journal_entry(self):
        """A REAL Journal Entry with NO BOQ attribution at all (the native control).

        It is saved by the SAME representative, in the same request, so its
        plain row shows exactly what the NATIVE flow produces for a Journal
        Entry Account row that carries no BOQ attribution. It is the reference
        the plain row of a BOQ-attributed voucher is compared against, so the
        expectation is never an invented NULL policy.
        """
        doc = self._new_journal_entry()
        doc.insert()
        return doc

    def _gl_rows(self, doc):
        """The persisted General Ledger rows of a posted voucher.

        The pinned ERPNext ``GL Entry`` doctype names the voucher reference
        ``voucher_no`` (a Dynamic Link to ``voucher_type``); there is no
        ``voucher_name`` column, so a read on it fails with
        ``Unknown column 'voucher_name' in 'WHERE'``. The value written by
        ``erpnext/controllers/accounts_controller.py::get_gl_dict`` is
        ``"voucher_no": self.name``.
        """
        return frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Journal Entry", "voucher_no": doc.name},
            fields=["account", "project", "debit", "credit", "is_cancelled"],
        )

    def _assert_refused(self, doc, message, expected_exception=frappe.ValidationError):
        """The intended refusal, with its message, and no stored voucher.

        ``expected_exception`` names the EXACT exception class the refusal
        must raise, so an unrelated failure is never masked:

        * the integrity refusals (an explicit project mismatch, a Project that
          does not belong to the document Company) are raised with
          ``frappe.throw`` and are therefore ``frappe.ValidationError``;
        * the SCOPE refusals (a BOQ project outside the active scope, a
          missing active User Scope Context) are raised with
          ``frappe.throw(..., frappe.PermissionError)``. In the pinned Frappe
          ``frappe.PermissionError`` inherits ``Exception`` DIRECTLY and is
          therefore NOT a ``frappe.ValidationError``; catching
          ``ValidationError`` there would not catch the refusal at all.
        """
        before = self._journal_entry_count()
        with self.assertRaises(expected_exception) as ctx:
            doc.insert()
        self.assertIn(message, str(ctx.exception))
        self.assertEqual(
            self._journal_entry_count(),
            before,
            "a refused Journal Entry must not be stored",
        )

    # ---------------------------------------------------- the corrected case

    def test_a_new_boq_row_persists_the_authoritative_project(self):
        """The reproduced defect: a BOQ row saved with a blank row project."""
        frappe.set_user(self.layer_user)
        before = self._journal_entry_count()
        control = self._control_journal_entry()
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        self.assertEqual(self._journal_entry_count(), before + 2)
        self.assertEqual(
            self._row_project(doc, 1),
            self.scope_project,
            "the BOQ row must persist the authoritative BOQ project",
        )
        self.assertEqual(
            self._row_project(doc, 2),
            self._row_project(control, 2),
            "the row without a BOQ attribution keeps exactly the native project behaviour",
        )

    def test_the_posted_gl_entry_carries_the_derived_project(self):
        """The posted General Ledger entry inherits the derived row project."""
        frappe.set_user(self.layer_user)
        control = self._control_journal_entry()
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        doc.submit()
        rows = self._gl_rows(doc)
        self.assertEqual(len(rows), 2, "a posted voucher produces one GL row per account")
        by_account = {row.account: row for row in rows}
        self.assertEqual(by_account[self.expense_account].project, self.scope_project)
        self.assertEqual(by_account[self.expense_account].debit, EXPENSE_AMOUNT)
        self.assertEqual(
            by_account[self.counterpart_account].project,
            self._row_project(control, 2),
            "the unattributed counterpart keeps the native project behaviour: no cash allocation is invented",
        )
        self.assertEqual(doc.total_debit, EXPENSE_AMOUNT)
        self.assertEqual(doc.total_credit, COUNTERPART_AMOUNT)

    def test_a_persisted_project_is_not_lost_when_the_document_is_saved_again(self):
        """C1 regression on the native path.

        The row already carries the authoritative project. A later save that
        arrives without the row project (a client that does not carry the
        field, or a partial API update) must not clear the assigned project.
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        self.assertEqual(self._row_project(doc, 1), self.scope_project)

        doc.reload()
        doc.accounts[0].project = None
        doc.save()

        self.assertEqual(
            self._row_project(doc, 1),
            self.scope_project,
            "a later save must not clear an already assigned project",
        )

    def test_a_newly_appended_row_is_not_a_historical_row(self):
        """A row appended to an existing voucher is a NEW row.

        It receives the authoritative project; it does not inherit the
        historical treatment of the rows that were already stored.
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        doc.reload()
        doc.append(
            "accounts",
            self._journal_row(
                self.expense_account,
                debit=EXPENSE_AMOUNT,
                boq_item=self.boq_item,
            ),
        )
        doc.save()
        self.assertEqual(
            self._row_project(doc, 3),
            self.scope_project,
            "an appended row is attributed like any other new BOQ-bearing row",
        )

    def test_a_client_supplied_child_identity_is_attributed_like_a_new_row(self):
        """A client-supplied child identity is never trusted as "historical".

        The row carries an explicit identity that the server has never
        persisted, so the historical exception cannot apply to it: it is
        attributed like a new row and receives the authoritative project.

        This is a NEW / COPY operation, NOT a proof about a foreign existing
        identity: the pinned ``Journal Entry Account`` child table uses
        ``autoname: hash``, so Frappe's ``set_new_name`` clears the supplied
        child name and assigns a generated one on insert. The test therefore
        records the requested name and asserts the ACTUAL stored child
        identity, its parent and its derived project; it does not assert that
        a supplied name survives. The foreign-existing-identity policy is
        proven by the site-less suite, which exercises the real
        ``is_new_or_changed_attribution`` parent-bound helper.
        """
        frappe.set_user(self.layer_user)
        requested_name = f"JE-COPIED-{frappe.generate_hash(length=8)}"
        self.assertFalse(frappe.db.exists("Journal Entry Account", requested_name))
        doc = self._new_journal_entry()
        doc.accounts[0].boq_item = self.boq_item
        doc.accounts[0].expense_category = "Direct"
        doc.append(
            "accounts",
            self._journal_row(
                self.expense_account,
                debit=EXPENSE_AMOUNT,
                boq_item=self.boq_item,
                row_name=requested_name,
            ),
        )
        doc.insert()

        appended = doc.accounts[-1]
        actual_name = appended.name
        self.assertTrue(actual_name, "the appended row received a stored child identity")
        self.assertTrue(
            frappe.db.exists("Journal Entry Account", actual_name),
            "the appended row is stored under its actual child identity",
        )
        self.assertEqual(
            frappe.db.get_value("Journal Entry Account", actual_name, "parent"),
            doc.name,
            "the appended row is a new child of this voucher",
        )
        self.assertEqual(
            frappe.db.get_value("Journal Entry Account", actual_name, "boq_item"),
            self.boq_item,
            "the appended row keeps its BOQ attribution",
        )
        self.assertEqual(
            frappe.db.get_value("Journal Entry Account", actual_name, "project"),
            self.scope_project,
            "a never-persisted child identity is attributed like a new row",
        )

    def test_the_plain_row_keeps_the_native_project_behaviour(self):
        """No invented cash allocation, asserted against the native flow.

        The ordinary representative has exactly ONE Project User Permission, so
        the NATIVE Frappe new-document default fills the blank ``project`` of
        every new Journal Entry Account row with the only allowed Project. That
        is EXISTING NATIVE behaviour: the application neither clears it nor
        replaces it, and no NULL business policy is invented. The plain row of
        a BOQ-attributed voucher is compared with the plain row of a REAL
        no-BOQ control voucher saved by the same representative.
        """
        frappe.set_user(self.user)
        control = self._control_journal_entry()
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()

        native_project = self._row_project(control, 2)
        self.assertEqual(
            native_project,
            self.scope_project,
            "the native new-document default fills the blank row project with the only allowed Project",
        )
        self.assertEqual(
            self._row_project(doc, 2),
            native_project,
            "the application invents no cash allocation on the plain row: the native value is preserved",
        )

    # ------------------------------------------------------------- refusals

    def test_an_explicit_project_mismatch_is_refused(self):
        """The intended refusal reaches the application's own validation chain.

        The representative of THIS case carries a Project User Permission for
        the other project as well, so the crafted row project is allowed by the
        native transport layer and the write legitimately REACHES the
        application's BOQ validation chain (the shared validator and the
        Journal Entry helper of
        ``construction/services/boq_journal_project.py``), which refuses it
        with the project-mismatch message.

        The refusal is raised by the SHARED validator
        (``construction/services/boq_accounting.py``): it is registered BEFORE
        the Journal Entry helper in ``hooks.py`` and it raises the IDENTICAL
        message, so for a Journal Entry the helper's own explicit-mismatch
        branch is a DEFENSIVE OVERLAP and not a second refusal point. The
        helper handles Journal Entry ONLY - it returns immediately for every
        other doctype - so the branch is not reachable for another doctype
        either. It IS reachable for a Journal Entry through the stored-stale-row
        path, which is proven separately by
        ``test_a_stale_stored_project_is_refused_by_the_application_validator``.
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item, project=self.other_project)
        self._assert_refused(doc, MISMATCH_MESSAGE)

    def test_the_project_user_permission_refuses_the_mismatch_before_the_app_validator(self):
        """The REAL transport denial is kept, and it is proven to be the transport layer.

        The ordinary representative has exactly ONE Project User Permission (the
        scope project). A row that names ANOTHER project is refused by the
        native User Permission enforcement - the pinned Frappe checks the link
        fields of the CHILD rows against the allowed documents
        (``frappe/permissions.py::has_user_permission``) - BEFORE the
        application's validation chain runs.

        The proof uses the OBSERVABLE native semantics only. It deliberately does
        NOT read ``frappe.flags``: the pinned
        ``frappe/permissions.py::print_has_permission_check_logs`` REMOVES its
        ``has_permission_check_logs`` diagnostic flag before it returns, so that
        flag is not a stable observable of a refused write.

        * the refusal is a ``frappe.PermissionError`` and NOT a
          ``frappe.ValidationError``: in the pinned Frappe
          ``frappe.PermissionError`` inherits ``Exception`` directly, while
          every application INTEGRITY refusal is a ``frappe.ValidationError``;
        * none of the application's refusal messages appears in the refusal;
        * the refused document was never NAMED: the pinned
          ``frappe/model/document.py::Document.insert`` calls
          ``check_permission("create")`` BEFORE ``set_new_name``, and the
          application's own refusals happen after the naming. An unnamed
          document therefore proves that the application's validation chain
          never ran;
        * nothing was stored: no voucher and no child row;
        * an INDEPENDENT ALLOWED CONTROL: the SAME representative, with the
          SAME fixture, saves a voucher whose row names the PERMITTED project,
          and the write succeeds. The refusal is therefore specific to the
          out-of-scope project and not to the fixture.

        No permission is widened for this case, no production module is patched
        and no exception is broadened.
        """
        frappe.set_user(self.user)

        # The INDEPENDENT ALLOWED CONTROL: the same representative and the same
        # fixture, with the PERMITTED project named on the row.
        control = self._new_journal_entry(boq_item=self.boq_item, project=self.scope_project)
        control.insert()
        self.assertEqual(
            self._row_project(control, 1),
            self.scope_project,
            "the native transport layer accepts the permitted project for this representative",
        )

        doc = self._new_journal_entry(boq_item=self.boq_item, project=self.other_project)
        before = self._journal_entry_count()
        rows_before = self._journal_entry_account_count()

        with self.assertRaises(frappe.PermissionError) as ctx:
            doc.insert()

        self.assertNotIsInstance(
            ctx.exception,
            frappe.ValidationError,
            "the refusal is the native transport refusal, not an application validation refusal",
        )
        for message in (MISMATCH_MESSAGE, COMPANY_MESSAGE, SCOPE_MESSAGE, SCOPE_CONTEXT_MESSAGE):
            self.assertNotIn(
                message,
                str(ctx.exception),
                f"the application refusal {message!r} did not refuse this write",
            )
        self.assertFalse(
            doc.name,
            "the refused document was never named: the native create-permission check refused it before the application's validation chain ran",
        )
        self.assertEqual(
            self._journal_entry_count(),
            before,
            "a refused Journal Entry must not be stored",
        )
        self.assertEqual(
            self._journal_entry_account_count(),
            rows_before,
            "a refused Journal Entry must not store a child row either",
        )

    def test_a_stale_stored_project_is_refused_by_the_application_validator(self):
        """The Journal Entry helper's OWN project-mismatch refusal.

        The stored row project contradicts the authoritative BOQ project (the
        BOQ Header's project was corrected after the row was written). The
        incoming row project is blank, so the SHARED validator - which only
        compares the INCOMING value - passes, and the refusal comes from
        ``construction/services/boq_journal_project.py`` itself. The stale
        value is neither silently cleared nor silently overwritten.
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        row_name = doc.accounts[0].name
        self.assertEqual(self._row_project(doc, 1), self.scope_project)

        # ---- FIXTURE (Administrator only) -------------------------------------
        # Simulate a row whose stored project contradicts the authoritative BOQ
        # project. The write is a fixture, not a business write, so it runs as
        # ``Administrator``; the ordinary representative is restored immediately
        # afterwards and performs the tested save below.
        frappe.set_user("Administrator")
        frappe.db.set_value("Journal Entry Account", row_name, "project", self.other_project)
        frappe.set_user(self.layer_user)
        # ---- end of fixture --------------------------------------------------

        doc.reload()
        self.assertEqual(self._row_project(doc, 1), self.other_project)

        doc.accounts[0].project = None
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save()

        self.assertIn(MISMATCH_MESSAGE, str(ctx.exception))
        self.assertIn(self.other_project, str(ctx.exception))
        self.assertIn(self.scope_project, str(ctx.exception))

        doc.reload()
        self.assertEqual(
            self._row_project(doc, 1),
            self.other_project,
            "a refused save must not silently clear or overwrite the stored project",
        )

    def test_a_cross_company_boq_project_is_refused_on_the_first_save(self):
        """The app's own check, not only ERPNext's later controller check.

        The BOQ Item belongs to a Project of ANOTHER company, so the
        application's own company integrity rule refuses the write on the FIRST
        save of the voucher.

        The layer representative is used: with TWO Project User Permissions the
        native new-document default does not fire, so the blank row project
        stays blank, the native transport layer has nothing to refuse and the
        refusal observed here is the APPLICATION's own company rule (the
        shared validator compares only the INCOMING row project, which is
        blank, and therefore passes).
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.cross_company_item)
        self._assert_refused(doc, COMPANY_MESSAGE)

    def test_a_boq_project_outside_the_active_scope_is_refused(self):
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.out_of_scope_item)
        self._assert_refused(doc, SCOPE_MESSAGE, frappe.PermissionError)

    def test_a_missing_active_scope_context_is_refused(self):
        # Remove the context as fixture setup, then test the ordinary write.
        frappe.set_user("Administrator")
        frappe.db.delete("User Scope Context", {"user": self.layer_user})
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item)
        self._assert_refused(doc, SCOPE_CONTEXT_MESSAGE, frappe.PermissionError)

    # ------------------------------------------------- privileged boundaries

    def test_administrator_keeps_the_company_integrity_rule(self):
        """The scope comparison is skipped for Administrator, the company rule is not."""
        doc = self._new_journal_entry(boq_item=self.cross_company_item)
        self._assert_refused(doc, COMPANY_MESSAGE)

    def test_a_disabled_scope_context_keeps_the_company_integrity_rule(self):
        self._set_scope_enforcement(False)
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.cross_company_item)
        self._assert_refused(doc, COMPANY_MESSAGE)

    # ----------------------------------------------- unchanged historical row

    def test_an_unchanged_historical_row_keeps_its_null_project(self):
        """No silent backfill: a stored NULL row stays NULL on save, submit and cancel.

        The stored row is forced back to NULL as a FIXTURE (it simulates a row
        written before the correction); the attribution itself is unchanged, so
        the historical exception applies and the project must NOT be derived
        again - not on the later save, not on the submission, and not in the
        posted or cancelled General Ledger history.
        """
        frappe.set_user(self.layer_user)
        doc = self._new_journal_entry(boq_item=self.boq_item)
        doc.insert()
        row_name = doc.accounts[0].name

        # ---- FIXTURE (Administrator only) -------------------------------------
        # Simulate a row that was written BEFORE the correction: the stored
        # project is forced back to NULL with one direct database write. The
        # write is a fixture, not a business write, so it runs as
        # ``Administrator``; the ordinary representative is restored
        # immediately afterwards and performs every tested write below.
        frappe.set_user("Administrator")
        frappe.db.set_value("Journal Entry Account", row_name, "project", None)
        frappe.set_user(self.layer_user)
        # ---- end of fixture --------------------------------------------------

        doc.reload()
        self.assertIsNone(self._row_project(doc, 1))
        doc.save()
        self.assertIsNone(
            self._row_project(doc, 1),
            "an unchanged historical row keeps its stored project: no backfill, no history rewrite",
        )

        doc.submit()
        gl_rows = self._gl_rows(doc)
        self.assertEqual(len(gl_rows), 2)
        for row in gl_rows:
            self.assertIsNone(
                row.project,
                "the posted General Ledger history of an unchanged historical row stays NULL",
            )
        by_account = {row.account: row for row in gl_rows}
        self.assertEqual(by_account[self.expense_account].debit, EXPENSE_AMOUNT)

        doc.cancel()
        self.assertEqual(doc.docstatus, 2)
        cancelled_rows = self._gl_rows(doc)
        self.assertEqual(len(cancelled_rows), 4, "a cancelled voucher keeps its four reversal GL rows")
        for row in cancelled_rows:
            self.assertIsNone(
                row.project,
                "the cancelled General Ledger history stays NULL as well",
            )
        for account in (self.expense_account, self.counterpart_account):
            net = sum(row.debit - row.credit for row in cancelled_rows if row.account == account)
            self.assertEqual(net, 0, "every account nets to zero after the cancellation")
