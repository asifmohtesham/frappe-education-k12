"""Development/demo gateway: a single-use token redeemed by a portal endpoint."""

import frappe

from education_k12.k12_fees.gateways.base import BaseGateway

TOKEN_TTL_SECONDS = 3600


def _cache_key(token):
    return f"k12_mock_payment:{token}"


class MockGateway(BaseGateway):
    def create_checkout_for(self, fees_name, amount):
        token = frappe.generate_hash(length=32)
        frappe.cache().set_value(
            _cache_key(token),
            frappe.as_json({"fees": fees_name, "amount": amount}),
            expires_in_sec=TOKEN_TTL_SECONDS,
        )
        return {
            "payment_url": (
                "/api/method/education_k12.api.fees.complete_mock_payment"
                f"?token={token}"
            )
        }


def consume_token(token):
    # frappe.cache().set_value pickles values, so we cannot use the raw Redis
    # GETDEL command here (it would return pickle bytes, not JSON).  Switching
    # to raw-conn writes would add complexity for a dev-only gateway.  The
    # non-atomic get+delete below has a narrow TOCTOU window, which is
    # acceptable: this gateway is never used in production.
    key = _cache_key(token)
    raw = frappe.cache().get_value(key)
    if not raw:
        return None
    frappe.cache().delete_value(key)
    return frappe.parse_json(raw)
