import frappe
from frappe import _


def populate_admission_documents(doc, method=None):
    """Seed the mandatory-document checklist on new applicants (before_insert)."""
    existing = {row.document_type for row in doc.admission_documents}
    mandatory = frappe.get_all(
        "K12 Admission Document Type", filters={"mandatory": 1}, pluck="name"
    )
    for doc_type in mandatory:
        if doc_type not in existing:
            doc.append(
                "admission_documents", {"document_type": doc_type, "status": "Pending"}
            )


def warn_pending_documents(doc, method=None):
    """Non-blocking nudge when approving/admitting with pending mandatory docs."""
    if doc.application_status not in ("Approved", "Admitted"):
        return
    mandatory = set(
        frappe.get_all(
            "K12 Admission Document Type", filters={"mandatory": 1}, pluck="name"
        )
    )
    pending = [
        row.document_type
        for row in doc.admission_documents
        if row.status == "Pending" and row.document_type in mandatory
    ]
    if pending:
        frappe.msgprint(
            _("Mandatory admission documents still pending: {0}").format(
                ", ".join(pending)
            ),
            indicator="orange",
        )
