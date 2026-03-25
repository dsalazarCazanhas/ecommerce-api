# Functional Validation Roadmap

This document defines the full validation path to complete project flow coverage before formal functional testing starts.

## Scope

The roadmap covers:

- End-to-end flow verification per domain.
- Negative-path and edge-case validation.
- Data consistency checks at API and database levels.
- Readiness criteria for the functional testing phase.
- Production recommendations to reduce deployment risk.

## Validation Phases

### Phase 1: Baseline Environment and Data

Objective: ensure repeatable and deterministic test runs.

Checklist:

1. Start PostgreSQL and API in local/dev mode.
2. Seed database using `scripts/sql/seed_test_data.sql`.
3. Start Stripe CLI forwarding to `/api/v1/stripe/webhook`.
4. Confirm `.env` has valid test credentials and webhook secret.
5. Verify health of core endpoints (`/api/v1/products/`, login endpoint).

Exit criteria:

- Seed loaded with no enum/data errors.
- Auth works with seeded users.
- Stripe listener receives and forwards events.

### Phase 2: Happy Path Coverage by Domain

Objective: validate expected behavior of each core module.

#### Auth

- `POST /api/v1/auth/login` with valid seeded user.
- `POST /api/v1/auth/refresh` with refresh cookie.
- `POST /api/v1/auth/logout` idempotent behavior.

Expected checks:

- Correct HTTP status codes.
- Access/refresh cookies set with expected flags.
- No-store response headers on auth endpoints.

#### Users

- `GET /api/v1/users/me` returns authenticated profile.
- `PATCH /api/v1/users/me` updates allowed fields.

Expected checks:

- Unauthorized fields are ignored/rejected as designed.
- Response schema remains stable.

#### Products

- `GET /api/v1/products/` lists seeded products.
- Admin-only product management endpoints behave with proper authorization.

Expected checks:

- Public listing is accessible.
- Admin operations reject non-admin users.

#### Cart and Checkout

- Add item to cart.
- View cart items.
- Checkout cart with `Idempotency-Key`.
- Validate order generation and stock update.

Expected checks:

- Cart transitions from active to ordered as designed.
- Order summary fields are consistent.
- Idempotency replay returns cached result for same key+payload.

#### Stripe

- Create checkout session from local order.
- Complete test payment in hosted checkout.
- Process webhook events.

Expected checks:

- `order.status` transitions to `PAID`.
- `payment.status` transitions to `SUCCEEDED`.
- Stripe event deduplication prevents duplicated side effects.

### Phase 3: Negative and Edge Cases

Objective: validate resilience and error-handling contracts.

Run these minimum scenarios:

1. Invalid credentials (`401`).
2. Inactive/blocked account (`403`).
3. Missing/invalid idempotency key (`400`/`409`).
4. Reused idempotency key with different payload (`409`).
5. Non-owner access to protected resources (`403`/`404`).
6. Stock conflict during checkout (`409`).
7. Duplicate webhook event delivery (idempotent processing).
8. Stripe payment failure event path (`FAILED` status handling).
9. Refund event path (`REFUNDED` status handling).

Exit criteria:

- Error contracts are stable and intentional.
- No data corruption after retries or duplicated events.

### Phase 4: Data Integrity and Cleanup

Objective: ensure the data model remains coherent after intensive testing.

Checks:

1. `order.total_amount` equals sum of its `order_item` snapshots.
2. `payment.amount` and currency align with order and Stripe payload.
3. Product stock changes match successful checkout quantities only.
4. Idempotency records reflect completed/failed states consistently.
5. Test artifacts are removable with deterministic cleanup scripts.

Deliverables:

- A short SQL verification pack (read-only checks).
- Cleanup commands for rerunning full suites safely.

### Phase 5: Functional Testing Readiness Gate

Objective: confirm readiness to start structured functional test execution.

Ready when:

1. Happy path is green across all core modules.
2. Critical negative paths are green.
3. Known defects are documented with severity and owner.
4. Runbook and endpoint contracts are up to date.
5. Test data setup/teardown is reproducible in under 10 minutes.

## Recommended Execution Order

1. Baseline setup and seed validation.
2. Auth and users domain checks.
3. Products and cart domain checks.
4. Checkout and Stripe end-to-end path.
5. Error and replay scenarios.
6. Data integrity SQL verification.
7. Cleanup and rerun confirmation.

## Evidence Template (per test case)

For each case, capture:

1. Test ID and objective.
2. Request (endpoint, headers, payload).
3. Response (status, body excerpt).
4. Database validation query and result.
5. Pass/Fail and notes.

## Production Recommendations

### Security

1. Store secrets in a dedicated secret manager (not plain `.env` in deployment hosts).
2. Enforce secure cookies in production (`Secure=true`, `HttpOnly=true`, strict `SameSite` policy aligned with frontend architecture).
3. Restrict `ALLOWED_ORIGINS`, `ALLOWED_HOSTS`, and admin surface to explicit values per environment.
4. Add rate-limiting and abuse controls on auth, checkout, and webhook endpoints.
5. Rotate JWT and Stripe credentials periodically with a tested rotation procedure.

### Payments and Stripe Operations

1. Use distinct Stripe accounts/projects and webhook endpoints per environment.
2. Keep strict webhook signature verification enabled and monitor signature failures.
3. Require idempotency keys in all payment-critical operations.
4. Maintain a reconciliation runbook for mismatches between local payment records and Stripe events.
5. Add alerting for failed webhook deliveries and repeated payment failures.

### Database and Data Governance

1. Use versioned migrations for schema evolution and maintain rollback paths.
2. Enable automated backups and test restore procedures periodically.
3. Define retention policies for idempotency records, logs, and test data.
4. Protect financial records with auditing fields and immutable payment history strategy.
5. Validate index coverage for high-frequency lookup paths (order id, stripe ids, user + idempotency key).

### Observability and Operations

1. Emit structured logs with request correlation IDs.
2. Track SLO-oriented metrics: error rates, checkout latency, webhook processing latency, retry/conflict rates.
3. Define alert thresholds with on-call ownership and incident playbooks.
4. Add health/readiness checks tied to DB and critical external dependencies.
5. Gate deployments with CI checks: lint, unit tests, integration smoke tests, and migration checks.

## Related Runbook

For a concrete checkout test walkthrough after seed, use:

- `docs/e2e-checkout-after-seed.md`

## References

- FastAPI Security: <https://fastapi.tiangolo.com/advanced/security/>
- FastAPI Deployment Concepts: <https://fastapi.tiangolo.com/deployment/>
- SQLAlchemy ORM Documentation: <https://docs.sqlalchemy.org/en/20/orm/>
- Stripe Webhooks Best Practices: <https://docs.stripe.com/webhooks>
- Stripe Idempotent Requests: <https://docs.stripe.com/api/idempotent_requests>
- OWASP ASVS Project: <https://owasp.org/www-project-application-security-verification-standard/>
- PostgreSQL Documentation: <https://www.postgresql.org/docs/>
