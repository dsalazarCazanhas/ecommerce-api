# 🛍️ E-commerce API

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLModel-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Build-Passing-brightgreen)

A scalable and modular **E-commerce REST API** built with **FastAPI**, **SQLModel**, and **PostgreSQL**.  
It provides secure authentication, product management, cart and order handling, and payment integration with **Stripe**.

---

## ⚙️ Tech Stack

### 🧠 Core Backend

- **Framework:** FastAPI `^0.104.1`
- **Database:** PostgreSQL + SQLModel `^0.0.24`
- **Auth:** JWT (via `python-jose ^3.3.0`)
- **Validation:** Pydantic v2 `^2.5.2`
- **Migrations:** Alembic `^1.12.1`

### 💳 External Services

- **Payments:** Stripe SDK `^7.8.0`

### 🧰 Development Tools

- **Dependency Manager:** Poetry
- **Testing:** pytest + pytest-asyncio
- **Documentation:** FastAPI (Swagger / OpenAPI auto-docs)
- **Linting & Formatting:** black + flake8 + isort
- **Environment Management:** python-dotenv `^1.0.0`

---

## 🚀 Quick Start

### 1️⃣ Clone and install dependencies

```bash
git clone https://github.com/yourusername/ecommerce-api.git
cd ecommerce-api
poetry install
````

### 2️⃣ Run the development server

```bash
python main.py
```

### 3️⃣ Environment variables

Create a `.env` file in the project root with:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce
HOST=127.0.0.1
PORT=8000
```

---

## 🧩 Project Structure

```bash
src/
 ├── api/                # API routers and endpoints
 ├── config/             # Engine and settings configuration
 ├── crud/               # Database operations (SQLModel CRUD)
 ├── models/             # ORM + Pydantic models
 ├── security/           # Auth and JWT handling
 ├── app.py             # Application entrypoint
 └── ...
```

---

## 🧠 Development Roadmap

### Stage 1: Base Configuration

- Initialize Poetry and dependencies
- Setup FastAPI project structure
- Configure database and migrations
- Create base models (User, Product)

### Stage 2: Authentication & Users

- JWT authentication system
- Full CRUD for users
- Role management (admin / user)

### Stage 3: Product Management

- CRUD operations for products and categories
- Search and filtering
- Inventory and image handling

### Stage 4: Shopping Cart

- Cart and CartItem models
- Session handling and stock validation

### Stage 5: Orders & Checkout

- Order and OrderItem models
- Checkout flow and order states

### Stage 6: Payment Integration

- Stripe integration and webhooks
- Payment state handling, refunds, and errors

### Stage 7: Advanced Features

- Email notifications
- Redis caching and performance optimization
- Reviews / ratings and analytics

### Stage 8: Testing & Documentation

- Unit and integration tests
- Final documentation and cleanup

---

## 🧾 Core Data Models

| Model         | Key Fields                                                                       |
| ------------- | -------------------------------------------------------------------------------- |
| **User**      | id, email, password_hash, first_name, last_name, is_active, is_admin, created_at |
| **Product**   | id, name, description, price, stock, category_id, image_url, created_at          |
| **Category**  | id, name, description, parent_id                                                 |
| **Cart**      | id, user_id, created_at, updated_at                                              |
| **CartItem**  | id, cart_id, product_id, quantity, price_at_time                                 |
| **Order**     | id, user_id, total_amount, status, shipping_address, created_at                  |
| **OrderItem** | id, order_id, product_id, quantity, price_at_time                                |
| **Payment**   | id, order_id, stripe_payment_intent_id, amount, status, created_at               |

---

## 🔒 Security Considerations

1. **Authentication:** JWT tokens with expiration
2. **Authorization:** Role-based middleware
3. **Validation:** Pydantic for all inputs
4. **Rate Limiting:** Prevent abuse
5. **CORS:** Proper configuration
6. **Sensitive Data:** Loaded via `.env`
7. **SQL Injection Prevention:** SQLModel parameter binding
8. **HTTPS:** Enforced in production

---

## ✅ Success Metrics

- [ ] Fully functional API
- [ ] Secure authentication
- [ ] Working Stripe integration
- [ ] Test coverage > 80%
- [ ] Complete documentation
- [ ] Optimized performance

---

## 📄 License

This project is licensed under the **MIT License**.

---

> *Built with ❤️ using FastAPI and Poetry — designed for scalability, clarity, and clean architecture.*
