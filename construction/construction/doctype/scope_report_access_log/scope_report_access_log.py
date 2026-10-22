import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ScopeReportAccessLog(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()
