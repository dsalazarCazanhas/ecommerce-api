# E2E Checkout Test After Seeding Database

This guide documents a full end-to-end test flow after loading `scripts/sql/seed_test_data.sql`.

## Goal

Validate this happy path:

1. Authenticate with a seeded test user.
2. List products and add one to cart.
3. Create an order from cart checkout.
4. Create a Stripe Checkout Session.
5. Pay in Stripe test mode.
6. Confirm webhook processing updated order/payment state.

## Prerequisites

- API running locally at `http://localhost:8000`.
- PostgreSQL running with seeded data.
- Stripe CLI installed and authenticated.
- `.env` contains test-mode Stripe credentials:
  - `STRIPE_API_KEY=sk_test_...`
  - `STRIPE_WEBHOOK_SECRET=whsec_...`

## 1) Start Stripe listener (webhooks)

Run in a separate terminal:

```bash
stripe listen --forward-to http://localhost:8000/api/v1/stripe/webhook
```

If Stripe CLI prints a new signing secret, update `.env` with that value and restart the API.

## 2) Define test variables

```bash
export BASE_URL="http://localhost:8000"
export API_V1="$BASE_URL/api/v1"
export COOKIE_JAR="/tmp/ecommerce.cookies"
```

## 3) Login with seeded user

Seeded credentials:

- Username: `qa_user_1`
- Password: `TestPass123!`

```bash
curl -i -c "$COOKIE_JAR" -X POST "$API_V1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "qa_user_1",
    "password": "TestPass123!"
  }'
```

Expected result:

- HTTP 200
- `Set-Cookie` includes `access_token`

## 4) List products and choose one

```bash
curl -s "$API_V1/products/" | jq
```

Use one seeded product ID, for example:

- `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2` (QA Mechanical Keyboard)

## 5) Add product to cart

```bash
curl -i -b "$COOKIE_JAR" -X POST \
  "$API_V1/cart/add?product_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2&quantity=1"
```

Optional verification:

```bash
curl -s -b "$COOKIE_JAR" "$API_V1/cart/me/items" | jq
```

## 6) Checkout cart (creates order)

Generate idempotency key:

```bash
export CHECKOUT_KEY="$(uuidgen)"
```

Call checkout:

```bash
curl -s -b "$COOKIE_JAR" -X POST "$API_V1/cart/checkout" \
  -H "Idempotency-Key: $CHECKOUT_KEY" | jq
```

Save returned `order_id`:

```bash
export ORDER_ID="<paste_order_id_here>"
```

## 7) Create Stripe Checkout Session

Generate a second idempotency key:

```bash
export STRIPE_KEY="$(uuidgen)"
```

Create session:

```bash
curl -s -b "$COOKIE_JAR" -X POST "$API_V1/stripe/checkout" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $STRIPE_KEY" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"line_items\": [],
    \"success_url\": \"http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}\",
    \"cancel_url\": \"http://localhost:3000/cancel\"
  }" | jq
```

Copy the returned `session_url` and open it in your browser.

## 8) Pay in Stripe hosted page

Use Stripe test card:

- Card: `4242 4242 4242 4242`
- Expiry: any future date
- CVC: any 3 digits
- ZIP/Postal: any value

## 9) Confirm webhook processed successfully

In the Stripe CLI terminal, verify events were forwarded with `2xx` responses.

Typical events include:

- `checkout.session.completed`
- `payment_intent.succeeded`

## 10) Verify final state in database

Example with Docker Postgres container named `ecommerce-pg`:

```bash
docker exec -it ecommerce-pg psql -U postgres -d ecommerce -c \
"SELECT id, status, total_amount, stripe_session_id, stripe_payment_intent_id
 FROM \"order\"
 WHERE id = '$ORDER_ID';"
```

```bash
docker exec -it ecommerce-pg psql -U postgres -d ecommerce -c \
"SELECT id, order_id, status, amount, stripe_session_id, stripe_payment_intent_id
 FROM payment
 WHERE order_id = '$ORDER_ID';"
```

Expected final state:

- `order.status = PAID`
- `payment.status = SUCCEEDED`

## Troubleshooting

- `401 Unauthorized` on protected endpoints:
  - Re-run login and ensure `-c`/`-b` cookie flags are used.
- `409` with idempotency message:
  - Generate a new UUID for `Idempotency-Key`.
- `400 success_url must include {CHECKOUT_SESSION_ID}`:
  - Ensure placeholder is present exactly in `success_url`.
- Webhook not updating DB:
  - Confirm Stripe CLI forwarding to `/api/v1/stripe/webhook`.
  - Confirm `.env` has the current `STRIPE_WEBHOOK_SECRET`.
  - Restart API after changing `.env`.
