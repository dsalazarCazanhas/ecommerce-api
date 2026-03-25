"""One-time utility script to register this server's webhook endpoint with Stripe
and retrieve the signing secret (whsec_...) that must be stored in
STRIPE_WEBHOOK_SECRET.

Usage (from project root, with STRIPE_API_KEY already set in .env):

    python -m src.services.webhook_setup --url https://yourdomain.com/api/v1/stripe/webhook

For local development with the Stripe CLI tunnel use the CLI instead:

    stripe listen --forward-to http://localhost:8000/api/v1/stripe/webhook

The CLI prints the signing secret directly to stdout and handles key rotation
automatically, so this script is only needed for production/staging deployments.

Why STRIPE_WEBHOOK_SECRET matters
----------------------------------
This is the HMAC-SHA256 key Stripe embeds in every webhook delivery (as the
Stripe-Signature header).  Without verifying it, any actor can POST to your
/stripe/webhook endpoint and forge payment events (e.g. fake a paid order).
Reference: https://docs.stripe.com/webhooks#verify-official-libraries
"""

import argparse
import sys

import stripe

# The full set of events the webhook handler in src/api/v1/stripe.py consumes.
_HANDLED_EVENTS: list[str] = [
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "payment_intent.payment_failed",
    "charge.refunded",
]


def register_webhook(url: str, api_key: str) -> str:
    """Create a WebhookEndpoint on Stripe for the given URL and return the secret.

    The secret is returned only at creation time; Stripe does not expose it
    again via the API.  If you lose it, delete the endpoint and recreate it.

    Parameters
    ----------
    url:
        Publicly reachable HTTPS URL that Stripe will POST events to.
        Must start with https:// for production/staging.
    api_key:
        Stripe secret key (sk_live_... or sk_test_...).

    Returns
    -------
    str
        The signing secret (whsec_...) to set as STRIPE_WEBHOOK_SECRET.
    """
    stripe.api_key = api_key

    endpoint = stripe.WebhookEndpoint.create(
        enabled_events=_HANDLED_EVENTS,
        url=url,
    )

    # `secret` is present only on the create response, not on subsequent reads.
    secret: str = endpoint.secret  # type: ignore[attr-defined]
    return secret


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register a Stripe webhook endpoint and print the signing secret.",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Public HTTPS URL Stripe will deliver events to, e.g. "
        "https://yourdomain.com/api/v1/stripe/webhook",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Stripe API key (sk_test_... or sk_live_...).  "
        "Defaults to STRIPE_API_KEY from the .env file.",
    )
    args = parser.parse_args()

    # Fall back to the application settings when no explicit key is provided.
    if args.api_key:
        api_key = args.api_key
    else:
        try:
            from src.config.ext import settings  # noqa: PLC0415

            api_key = settings.STRIPE_API_KEY
        except Exception as exc:
            print(
                f"ERROR: Could not load STRIPE_API_KEY from settings: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Registering webhook for: {args.url}")
    print(f"Enabled events: {', '.join(_HANDLED_EVENTS)}")
    print()

    try:
        secret = register_webhook(url=args.url, api_key=api_key)
    except stripe.error.AuthenticationError:
        print(
            "ERROR: Invalid Stripe API key.  Check STRIPE_API_KEY in your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)
    except stripe.error.InvalidRequestError as exc:
        print(f"ERROR: Invalid request to Stripe: {exc}", file=sys.stderr)
        sys.exit(1)
    except stripe.error.StripeError as exc:
        print(f"ERROR: Stripe API error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Webhook endpoint registered successfully.")
    print()
    print("Add the following line to your .env (or secrets manager):")
    print()
    print(f"    STRIPE_WEBHOOK_SECRET={secret}")
    print()
    print("IMPORTANT: This secret is shown only once.  Store it securely now.")


if __name__ == "__main__":
    main()
