"""Development/demo gateway: a single-use token redeemed by a portal endpoint.

Tokens are stored in an in-process dict (not Redis) so that this gateway
works even when Redis is unavailable or misconfigured — a common situation in
development and CI environments.  The narrow TOCTOU window on the
get-then-delete in consume_token is acceptable: this gateway is never used in
production.
"""

import time

import frappe

from education_k12.k12_fees.gateways.base import BaseGateway

TOKEN_TTL_SECONDS = 3600

# module-level store: token -> (payload_dict, expiry_epoch)
_token_store: dict = {}


class MockGateway(BaseGateway):
    def create_checkout_for(self, fees_name, amount):
        token = frappe.generate_hash(length=32)
        _token_store[token] = (
            {"fees": fees_name, "amount": amount},
            time.monotonic() + TOKEN_TTL_SECONDS,
        )
        return {
            "payment_url": (
                "/api/method/education_k12.api.fees.complete_mock_payment"
                f"?token={token}"
            )
        }


def consume_token(token):
    entry = _token_store.get(token)
    if not entry:
        return None
    payload, expiry = entry
    if time.monotonic() > expiry:
        _token_store.pop(token, None)
        return None
    del _token_store[token]
    return payload
