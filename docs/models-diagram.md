# Models Diagram

:::mermaid
erDiagram
    USER {
        UUID id PK
        string username
        string email
        string password_hash
        string name
        string last_name
        string phone
        enum role
        enum status
        datetime created_at
        datetime updated_at
        datetime last_login
        int failed_login_attempts
    }

    CART {
        UUID id PK
        UUID user_id FK
        enum status
        datetime created_at
        datetime updated_at
    }

    CART_ITEM {
        UUID id PK
        UUID cart_id FK
        UUID product_id FK
        int quantity
        float unit_price
        datetime created_at
        datetime updated_at
    }

    PRODUCT {
        UUID id PK
        string name
        string description
        float price
        int stock
        string image_url
        datetime created_at
        datetime updated_at
    }

    %% === RELATIONSHIPS ===
    USER ||--o{ CART : "has many"
    CART ||--o{ CART_ITEM : "contains"
    PRODUCT ||--o{ CART_ITEM : "listed in"
    CART_ITEM }o--|| PRODUCT : "references"
:::
