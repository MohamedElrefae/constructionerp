from construction.services.boq_accounting import validate_transaction_row
from construction.services.boq_scope_registry import CHILD_TABLE_BY_DOCTYPE, get_transaction_scope_rule


def validate_document(doc, method=None):
    if not get_transaction_scope_rule(doc.doctype):
        return

    child_table = get_child_table(doc)
    if not child_table:
        return

    for row in child_table:
        validate_transaction_row(row, doc)


def get_child_table(doc):
    table_field = CHILD_TABLE_BY_DOCTYPE.get(doc.doctype)
    if not table_field:
        return None
    if hasattr(doc, "get"):
        return doc.get(table_field)
    return getattr(doc, table_field, None)
