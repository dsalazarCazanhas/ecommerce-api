from typing import Any, Dict

import stripe

from src.config.ext import settings

stripe.api_key = settings.STRIPE_API_KEY


class StripeService:
    """Centralized service for interacting with the Stripe API."""

    @staticmethod
    def _handle_stripe_error(e: Exception) -> None:
        """Standardized Stripe error handler."""
        if isinstance(e, stripe.error.CardError):
            raise ValueError(f"Card error: {e.user_message}")
        elif isinstance(e, stripe.error.RateLimitError):
            raise ValueError("Too many requests to Stripe API.")
        elif isinstance(e, stripe.error.InvalidRequestError):
            raise ValueError("Invalid parameters sent to Stripe API.")
        elif isinstance(e, stripe.error.AuthenticationError):
            raise ValueError("Invalid Stripe API credentials.")
        elif isinstance(e, stripe.error.APIConnectionError):
            raise ValueError("Network communication with Stripe failed.")
        elif isinstance(e, stripe.error.StripeError):
            raise ValueError("Generic Stripe error.")
        else:
            raise e

    # === Payment Methods ===
    @staticmethod
    def create_payment_method(
        account_number: str, routing_number: str, holder_name: str
    ) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethod.create(
                type="us_bank_account",
                us_bank_account={
                    "account_holder_type": "individual",
                    "account_number": account_number,
                    "routing_number": routing_number,
                },
                billing_details={"name": holder_name},
            )
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def update_payment_method(
        payment_method_id: str, metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethod.modify(payment_method_id, metadata=metadata)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def get_payment_method(payment_method_id: str) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethod.retrieve(payment_method_id)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def attach_payment_method(
        payment_method_id: str, customer_id: str
    ) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def detach_payment_method(payment_method_id: str) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethod.detach(payment_method_id)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def list_customer_payment_methods(
        customer_id: str, limit: int = 5
    ) -> Dict[str, Any]:
        try:
            return stripe.Customer.list_payment_methods(customer_id, limit=limit)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    # === Payment Method Configurations ===
    @staticmethod
    def create_payment_method_configuration(name: str) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethodConfiguration.create(name=name)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def update_payment_method_configuration(config_id: str, **kwargs) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethodConfiguration.modify(config_id, **kwargs)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def retrieve_payment_method_configuration(config_id: str) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethodConfiguration.retrieve(config_id)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def list_payment_method_configurations(limit: int = 10) -> Dict[str, Any]:
        try:
            return stripe.PaymentMethodConfiguration.list(limit=limit)
        except Exception as e:
            StripeService._handle_stripe_error(e)
        except Exception as e:
            StripeService._handle_stripe_error(e)

    # === Stripe Sessions ===
    @staticmethod
    def create_checkout_session(
        self,
        line_items: list,
        success_url: str,
        cancel_url: str,
        mode: str = "payment",
        payment_method_types: list = ["card"],
    ) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=payment_method_types,
                mode=mode,
                line_items=line_items,
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def update_checkout_session(self, session_id: str, **kwargs) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.modify(session_id, **kwargs)
            return session
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def retrieve_checkout_session(self, session_id: str) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def retrieve_line_item(self, session_id: str, line_item_id: str) -> Dict[str, Any]:
        try:
            line_item = stripe.checkout.Session.list_line_items(
                session_id, limit=1, starting_after=line_item_id
            )
            return line_item
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def list_all_checkout_sessions(self, limit: int = 10) -> Dict[str, Any]:
        try:
            sessions = stripe.checkout.Session.list(limit=limit)
            return sessions
        except Exception as e:
            StripeService._handle_stripe_error(e)

    @staticmethod
    def expire_checkout_session(self, session_id: str) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.expire(session_id)
            return session
        except Exception as e:
            StripeService._handle_stripe_error(e)
