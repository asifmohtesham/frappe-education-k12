import frappe


def get_gateway():
    from education_k12.k12_fees.gateways.mock import MockGateway

    name = frappe.db.get_single_value("K12 Settings", "payment_gateway") or "Mock"
    if name == "Stripe":
        try:
            from education_k12.k12_fees.gateways.stripe import StripeGateway
        except ImportError:
            frappe.throw(
                "Stripe gateway module not available. Install T4 first or switch to Mock."
            )
        return StripeGateway()
    return MockGateway()
