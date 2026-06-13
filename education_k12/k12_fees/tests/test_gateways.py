import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.gateways import get_gateway
from education_k12.k12_fees.gateways.mock import MockGateway, consume_token


class TestGatewayRegistry(FrappeTestCase):
    def test_default_gateway_is_mock(self):
        frappe.db.set_single_value("K12 Settings", "payment_gateway", "Mock")
        self.assertIsInstance(get_gateway(), MockGateway)

    def test_mock_checkout_issues_consumable_token(self):
        gateway = MockGateway()
        result = gateway.create_checkout_for("FEE-TEST-001", 5000)
        self.assertIn("token=", result["payment_url"])
        token = result["payment_url"].split("token=")[1].split("&")[0]
        payload = consume_token(token)
        self.assertEqual(payload["fees"], "FEE-TEST-001")
        self.assertEqual(payload["amount"], 5000)
        self.assertIsNone(consume_token(token))  # single-use

    def test_mock_expired_token_returns_none(self):
        self.assertIsNone(consume_token("nonexistent_token_xyz"))
