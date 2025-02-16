# E-commerce API Project

This project is a Python-based E-commerce API designed to handle user authentication, product management, shopping cart operations, and payment processing.

## Features
- **JWT Authentication**: Secure user authentication and session management.
- **CRUD Operations**: Basic Create, Read, Update, Delete functionality for products, carts, and users.
- **Payment Gateway Integration**: Seamless payment processing with Stripe.
- **Complex Data Model**: Supports products, shopping carts, users, orders, and more.
- **Admin Panel**: Starlette Admin with PostgreSQL for product and inventory management.

## Requirements
- User sign-up and log-in functionality.
- Adding, removing, and managing products in a shopping cart.
- Viewing and searching for products.
- Checkout and payment process integration.
- Admin panel for product management, pricing, and inventory control.

## Tools and Technologies
- **Python**
- **JWT (PyJWT)**
- **Stripe API**
- **PostgreSQL**
- **Starlette Admin**
- **HTML, CSS, Jinja/EJS (Frontend)**
- **Postman (API Testing)**

## Project Structure
- **API Development**: Backend development with Python.
- **Database**: PostgreSQL setup for data storage and management.
- **Authentication**: JWT implementation for secure user sessions.
- **Payment Integration**: Stripe API for handling payments.
- **Admin Interface**: Starlette Admin for managing e-commerce data.
- **Frontend**: Basic HTML, CSS, and templating engine.

## Setup Instructions
1. Clone the repository.
2. Set up a virtual environment using Poetry.
3. Install dependencies.
4. Configure PostgreSQL database.
5. Run database migrations.
6. Run dev with uvicorn app:app
7. Access the API via Postman or build a simple frontend.

## Future Enhancements
- Refined JWT authentication and security.
- Custom user model for flexibility.
- Advanced product search and filtering.
- Enhanced admin panel features.

## License
[!INFO]
This project is licensed under the [MIT License](./LICENSE).

---

*Built with ❤️ using Python and [Starlette-admin](https://github.com/jowilf/starlette-admin).*

