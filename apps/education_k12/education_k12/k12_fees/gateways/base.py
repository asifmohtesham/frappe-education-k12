class BaseGateway:
    """Two-method gateway contract.

    create_checkout_for(fees_name, amount) -> {"payment_url": str}
    Callback handling is gateway-specific (token endpoint for Mock,
    signed webhook for Stripe); each gateway converts its callback into a
    record_fee_payment() call.
    """

    def create_checkout_for(self, fees_name, amount):
        raise NotImplementedError
