from construction.services.boq_accounting import validate_transaction_row


CHILD_TABLE_BY_DOCTYPE = {
	"Purchase Order": "items",
	"Purchase Receipt": "items",
	"Purchase Invoice": "items",
	"Sales Invoice": "items",
	"Stock Entry": "items",
	"Timesheet": "time_logs",
	"Journal Entry": "accounts",
	"Material Request": "items",
}


def validate_document(doc, method=None):
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
