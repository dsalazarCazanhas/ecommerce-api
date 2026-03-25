BEGIN;

-- =========================================================
-- QA seed bootstrap for ecommerce-api (PostgreSQL)
-- Mode: non-destructive (no reset, no truncate)
-- Safe to re-run: uses ON CONFLICT upserts
--
-- Seeded test password for all users in this file:
--   TestPass123!
-- bcrypt hash:
--   $2b$12$MfUh6KKYtVAA.VlY5xYNMO6TIHKNTiaYE/u2cthIf7yLzww7M0grK

-- NOTE: PostgreSQL ENUM labels are the Python enum *names* (uppercase),
-- not the .value strings. SQLAlchemy native enum creation uses names by default.
-- UserRole: ADMIN | USER | MODERATOR
-- UserStatus: ACTIVE | INACTIVE | SUSPENDED
-- CartStatus: ACTIVE | ABANDONED | ORDERED
-- =========================================================

-- ---------------------------------------------------------
-- 1) Users with different roles
-- ---------------------------------------------------------
INSERT INTO "user" (
    id,
    created_at,
    updated_at,
    name,
    last_name,
    phone,
    role,
    status,
    username,
    email,
    password_hash,
    last_login,
    failed_login_attempts
)
VALUES
(
    '11111111-1111-4111-8111-111111111111',
    NOW(),
    NULL,
    'QA',
    'Admin',
    '+573001000001',
    'ADMIN',
    'ACTIVE',
    'qa_admin',
    'qa_admin@example.com',
    '$2b$12$MfUh6KKYtVAA.VlY5xYNMO6TIHKNTiaYE/u2cthIf7yLzww7M0grK',
    NULL,
    0
),
(
    '22222222-2222-4222-8222-222222222222',
    NOW(),
    NULL,
    'QA',
    'UserOne',
    '+573001000002',
    'USER',
    'ACTIVE',
    'qa_user_1',
    'qa_user_1@example.com',
    '$2b$12$MfUh6KKYtVAA.VlY5xYNMO6TIHKNTiaYE/u2cthIf7yLzww7M0grK',
    NULL,
    0
),
(
    '33333333-3333-4333-8333-333333333333',
    NOW(),
    NULL,
    'QA',
    'UserTwo',
    '+573001000003',
    'USER',
    'ACTIVE',
    'qa_user_2',
    'qa_user_2@example.com',
    '$2b$12$MfUh6KKYtVAA.VlY5xYNMO6TIHKNTiaYE/u2cthIf7yLzww7M0grK',
    NULL,
    0
),
(
    '44444444-4444-4444-8444-444444444444',
    NOW(),
    NULL,
    'QA',
    'Moderator',
    '+573001000004',
    'MODERATOR',
    'ACTIVE',
    'qa_moderator',
    'qa_moderator@example.com',
    '$2b$12$MfUh6KKYtVAA.VlY5xYNMO6TIHKNTiaYE/u2cthIf7yLzww7M0grK',
    NULL,
    0
)
ON CONFLICT (id) DO UPDATE
SET
    updated_at = NOW(),
    name = EXCLUDED.name,
    last_name = EXCLUDED.last_name,
    phone = EXCLUDED.phone,
    role = EXCLUDED.role,
    status = EXCLUDED.status,
    username = EXCLUDED.username,
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    failed_login_attempts = EXCLUDED.failed_login_attempts;

-- ---------------------------------------------------------
-- 2) Products for cart/checkout/stripe tests
-- ---------------------------------------------------------
INSERT INTO product (
    id,
    created_at,
    updated_at,
    name,
    description,
    price,
    stock,
    image_url
)
VALUES
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1',
    NOW(),
    NULL,
    'QA Laptop Pro 14',
    'QA seed product',
    1499.99,
    8,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2',
    NOW(),
    NULL,
    'QA Mechanical Keyboard',
    'QA seed product',
    129.50,
    25,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3',
    NOW(),
    NULL,
    'QA Wireless Mouse',
    'QA seed product',
    49.90,
    40,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4',
    NOW(),
    NULL,
    'QA USB-C Hub',
    'QA seed product',
    69.00,
    35,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa5',
    NOW(),
    NULL,
    'QA 27 Monitor',
    'QA seed product',
    329.99,
    15,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa6',
    NOW(),
    NULL,
    'QA Noise Cancelling Headphones',
    'QA seed product',
    219.00,
    20,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa7',
    NOW(),
    NULL,
    'QA WebCam HD',
    'QA seed product',
    89.00,
    30,
    NULL
),
(
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa8',
    NOW(),
    NULL,
    'QA External SSD 1TB',
    'QA seed product',
    159.99,
    18,
    NULL
)
ON CONFLICT (id) DO UPDATE
SET
    updated_at = NOW(),
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    stock = EXCLUDED.stock,
    image_url = EXCLUDED.image_url;

-- ---------------------------------------------------------
-- 3) Starter carts (active)
-- ---------------------------------------------------------
INSERT INTO cart (
    id,
    created_at,
    updated_at,
    user_id,
    status
)
VALUES
(
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1',
    NOW(),
    NULL,
    '22222222-2222-4222-8222-222222222222',
    'ACTIVE'
),
(
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2',
    NOW(),
    NULL,
    '33333333-3333-4333-8333-333333333333',
    'ACTIVE'
)
ON CONFLICT (id) DO UPDATE
SET
    updated_at = NOW(),
    user_id = EXCLUDED.user_id,
    status = EXCLUDED.status;

COMMIT;
