import secrets

from frappe.model.document import Document
from frappe.utils import nowdate


class BOQImportBatch(Document):
    def autoname(self):
        self.name = f"BOQIMP-{nowdate().replace('-', '')}-{secrets.token_hex(4)}"
