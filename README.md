# E-commerce API

![Status](https://img.shields.io/badge/status-development-orange?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.13%2B-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135.2-009688?style=flat-square)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.37-2E7D32?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.x-336791?style=flat-square)
![Stripe](https://img.shields.io/badge/Stripe-7.8.0-635BFF?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

FastAPI e-commerce backend with JWT auth, cart checkout, and Stripe webhook processing.

## 5-Minute Onboarding

1. Install dependencies

```bash
poetry install --no-root
```

1. Create local environment file

```bash
cp .env.plantilla .env
```

1. Fill required values in .env

- DATABASE_URL
- SECRET_KEY, SESSION_KEY, CSRF_KEY (32+ chars)
- STRIPE_API_KEY
- STRIPE_WEBHOOK_SECRET

1. Start PostgreSQL with seeded QA data

```bash
docker run --name ecommerce-pg --rm \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ecommerce \
  -v "$(pwd)/scripts/sql/seed_test_data.sql:/docker-entrypoint-initdb.d/seed.sql" \
  -p 5432:5432 \
  postgres:17.2
```

1. Run API

```bash
poetry run python main.py
```

1. Open API docs

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Current Stack

- Python >= 3.13
- FastAPI ^0.135.2
- SQLModel ^0.0.37 + PostgreSQL (psycopg2-binary)
- Pydantic v2 + pydantic-settings
- PyJWT + passlib[bcrypt]
- Stripe SDK ^7.8.0
- Alembic

Source of truth: pyproject.toml.

## Tested Local Flow

Validated end-to-end in local Docker environment:

- login
- add product to cart
- cart checkout
- Stripe hosted checkout
- webhook processing
- persisted final status: order=PAID, payment=SUCCEEDED

## Stripe Local Webhooks

```bash
stripe listen --forward-to http://localhost:8000/api/v1/stripe/webhook
```

If Stripe CLI outputs a new whsec\_ value, update .env and restart the API.

## Seeded QA Credentials

- username: qa_user_1
- password: TestPass123!

## Documentation

- End-to-end checkout runbook: docs/e2e-checkout-after-seed.md
- Functional validation roadmap: docs/functional-validation-roadmap.md
- Data model diagram notes: docs/models-diagram.md

## Tests

```bash
poetry run pytest -q
```

## License

MIT License. See LICENSE.
