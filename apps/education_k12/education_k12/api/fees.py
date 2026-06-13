"""Parent-portal fee endpoints. Authorization model identical to api/portal.py:
explicit guardian-ownership checks BEFORE any permission-bypassing read."""

import frappe
from frappe import _
from frappe.utils import flt

from education_k12.api.portal import _children_of, _guardian
from education_k12.k12_fees.gateways import get_gateway
from education_k12.k12_fees.gateways.mock import consume_token
from education_k12.k12_fees.gateways.stripe import verify_webhook_signature
from education_k12.k12_fees.payments import record_fee_payment


def _own_student(student):
    guardian = _guardian()
    if student not in _children_of(guardian):
        frappe.throw(_("Not your child"), frappe.PermissionError)


@frappe.whitelist()
def get_child_fees(student):
    _own_student(student)
    rows = frappe.get_all(
        "Fees",
        filters={"student": student, "docstatus": 1},
        fields=[
            "name",
            "due_date",
            "posting_date",
            "grand_total",
            "outstanding_amount",
            "currency",
            "academic_year",
        ],
        order_by="due_date desc",
    )
    for row in rows:
        row["components"] = frappe.get_all(
            "Fee Component",
            filters={"parent": row["name"], "parenttype": "Fees"},
            fields=["fees_category", "amount", "discount", "total", "description"],
            order_by="idx asc",
        )
    return rows


def _own_fees(fees_name):
    fees = frappe.db.get_value(
        "Fees",
        fees_name,
        ["name", "student", "outstanding_amount", "docstatus"],
        as_dict=True,
    )
    if not fees:
        frappe.throw(_("Not your fees"), frappe.PermissionError)
    _own_student(fees.student)
    return fees


@frappe.whitelist()
def initiate_fee_payment(fees_name):
    fees = _own_fees(fees_name)
    if fees.docstatus != 1 or flt(fees.outstanding_amount) <= 0:
        frappe.throw(_("Nothing outstanding on {0}").format(fees_name))
    return get_gateway().create_checkout_for(fees.name, flt(fees.outstanding_amount))


@frappe.whitelist()
def complete_mock_payment(token):
    """Landing endpoint for the Mock gateway's payment_url (logged-in parent)."""
    payload = consume_token(token)
    if not payload:
        frappe.throw(_("Payment link expired or already used"))
    record_fee_payment(
        payload["fees"], payload["amount"], reference=f"MOCK-{token[:8]}", mode="Mock"
    )
    frappe.db.commit()
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/portal"


def _complete_mock_payment_for_tests(token):
    """Test seam: same flow without the HTTP redirect plumbing."""
    payload = consume_token(token)
    if not payload:
        frappe.throw(_("Payment link expired or already used"))
    record_fee_payment(
        payload["fees"], payload["amount"], reference=f"MOCK-{token[:8]}", mode="Mock"
    )


@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    """Stripe checkout.session.completed → record payment. Signature-verified."""
    secret = frappe.conf.get("stripe_webhook_secret")
    payload = frappe.request.data
    header = frappe.get_request_header("Stripe-Signature") or ""
    if not secret or not verify_webhook_signature(payload, header, secret):
        frappe.throw(_("Invalid signature"), frappe.PermissionError)
    event = frappe.parse_json(payload)
    if event.get("type") != "checkout.session.completed":
        return "ignored"
    session = event["data"]["object"]
    # TODO: deduplicate by session["payment_intent"] — Stripe delivers webhooks at-least-once;
    # a duplicate event for a partially-settled fee can still post a second JE.
    # Check for an existing JE referencing this payment_intent before calling record_fee_payment.
    try:
        record_fee_payment(
            session["metadata"]["fees"],
            flt(session["amount_total"]) / 100,
            reference=session.get("payment_intent"),
            mode="Stripe",
        )
    except Exception:
        frappe.db.rollback()
        raise
    frappe.db.commit()
    return "ok"


@frappe.whitelist()
def download_receipt(fees_name):
    fees = _own_fees(fees_name)
    if fees.docstatus != 1:
        frappe.throw(_("Receipt not available"), frappe.PermissionError)
    html = frappe.get_print("Fees", fees_name, print_format=_receipt_format())
    frappe.local.response.filename = f"{fees_name}-receipt.pdf"
    frappe.local.response.filecontent = frappe.utils.pdf.get_pdf(html)
    frappe.local.response.type = "pdf"


def _receipt_format():
    return (
        "K12 Fee Receipt"
        if frappe.db.exists("Print Format", "K12 Fee Receipt")
        else "Standard"
    )
