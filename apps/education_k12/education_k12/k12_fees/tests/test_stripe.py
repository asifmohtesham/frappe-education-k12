import hashlib
import hmac
import json
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.gateways.stripe import (
    StripeGateway,
    verify_webhook_signature,
)


class TestStripeGateway(FrappeTestCase):
    def setUp(self):
        frappe.conf.stripe_secret_key = "sk_test_dummy"
        frappe.conf.stripe_webhook_secret = "whsec_dummy"

    def test_create_checkout_posts_session(self):
        fake_response = type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self: {"url": "https://checkout.stripe.com/pay/cs_test"},
                "text": "",
            },
        )()
        with patch(
            "education_k12.k12_fees.gateways.stripe.requests.post",
            return_value=fake_response,
        ) as post:
            gateway = StripeGateway()
            result = gateway.create_checkout_for("FEE-X-001", 12100)
        self.assertEqual(
            result["payment_url"], "https://checkout.stripe.com/pay/cs_test"
        )
        args, kwargs = post.call_args
        self.assertIn("checkout/sessions", args[0])
        self.assertEqual(kwargs["auth"][0], "sk_test_dummy")
        sent = kwargs["data"]
        self.assertEqual(sent["metadata[fees]"], "FEE-X-001")
        self.assertEqual(sent["line_items[0][price_data][unit_amount]"], 1210000)

    def test_webhook_signature_roundtrip(self):
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        timestamp = str(int(time.time()))
        signed = hmac.new(
            b"whsec_dummy", f"{timestamp}.".encode() + payload, hashlib.sha256
        ).hexdigest()
        header = f"t={timestamp},v1={signed}"
        self.assertTrue(verify_webhook_signature(payload, header, "whsec_dummy"))

    def test_webhook_bad_signature_rejected(self):
        payload = b"{}"
        header = f"t={int(time.time())},v1=deadbeef"
        self.assertFalse(verify_webhook_signature(payload, header, "whsec_dummy"))
