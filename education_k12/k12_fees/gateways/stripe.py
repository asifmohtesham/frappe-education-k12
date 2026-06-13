"""Stripe Checkout adapter (no SDK; raw HTTPS).

Config (site_config.json): stripe_secret_key, stripe_webhook_secret.
Currency: the school site's company currency is assumed Stripe-supported
(AED is). Amounts are sent in fils/cents (x100).

UNVERIFIED AGAINST LIVE STRIPE: unit-tested with stubbed HTTP only. Set
the keys and run a test-mode checkout before offering this to a school.
"""

import hashlib
import hmac
import time

import requests

import frappe
from frappe import _

from education_k12.k12_fees.gateways.base import BaseGateway

API_BASE = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE_SECONDS = 300


class StripeGateway(BaseGateway):
    def __init__(self):
        self.secret_key = frappe.conf.get("stripe_secret_key")
        if not self.secret_key:
            frappe.throw(_("stripe_secret_key missing from site config"))

    def create_checkout_for(self, fees_name, amount):
        site_url = frappe.utils.get_url()
        currency = (
            frappe.db.get_single_value("Global Defaults", "default_currency") or "AED"
        )
        response = requests.post(
            f"{API_BASE}/checkout/sessions",
            auth=(self.secret_key, ""),
            data={
                "mode": "payment",
                "success_url": f"{site_url}/portal",
                "cancel_url": f"{site_url}/portal",
                "metadata[fees]": fees_name,
                "line_items[0][quantity]": 1,
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": int(round(amount * 100)),
                "line_items[0][price_data][product_data][name]": f"School fees {fees_name}",
            },
            timeout=30,
        )
        if response.status_code != 200:
            frappe.throw(_("Stripe error: {0}").format(response.text[:300]))
        return {"payment_url": response.json()["url"]}


def verify_webhook_signature(payload, signature_header, webhook_secret):
    try:
        parts = dict(item.split("=", 1) for item in signature_header.split(","))
        timestamp, expected = parts["t"], parts["v1"]
    except (ValueError, KeyError):
        return False
    if abs(time.time() - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    computed = hmac.new(
        webhook_secret.encode(),
        f"{timestamp}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)
