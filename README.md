# E-commerce API - Estructura del Proyecto

## 🛠️ Stack Tecnológico

### Backend Core

- **Framework**: FastAPI
- **Base de datos**: PostgreSQL + SQLMODEL (ORM)
- **Autenticación**: JWT con python-jose
- **Validación**: Pydantic
- **Migraciones**: Alembic

### Servicios Externos

- **Pagos**: Stripe SDK
- **Almacenamiento**: AWS S3 / Cloudinary (imágenes de productos)
- **Email**: SendGrid / Amazon SES
- **Cache**: Redis (opcional para optimización)

### Herramientas de Desarrollo

- **Gestor de dependencias**: Poetry
- **Testing**: pytest + pytest-asyncio
- **Documentación**: FastAPI automática (Swagger/OpenAPI)
- **Linting**: black + flake8 + isort
- **Variables de entorno**: python-dotenv

## 🚀 Etapas de Desarrollo

### **Etapa 1: Configuración Base (Semana 1)**

**Objetivos:**

- Configurar Poetry y entorno de desarrollo
- Establecer la estructura del proyecto
- Configurar base de datos y migraciones

**Tareas:**

1. Inicializar proyecto con Poetry (`poetry init`)
2. Configurar dependencias en pyproject.toml
3. Crear estructura de directorios
4. Configurar FastAPI con configuraciones básicas
5. Configurar PostgreSQL y SQLAlchemy
6. Implementar sistema de migraciones con Alembic
7. Crear modelos base (User, Product, Category)
8. Configurar variables de entorno
9. Configurar herramientas de desarrollo (black, flake8, isort)

**Entregables:**

- Proyecto configurado con Poetry
- Estructura de directorios definida
- Conexión a base de datos funcional
- Migraciones básicas
- Herramientas de desarrollo configuradas

### **Etapa 2: Autenticación y Usuarios (Semana 2)**

**Objetivos:**

- Implementar sistema de autenticación JWT
- CRUD completo para usuarios
- Sistema de roles (usuario/admin)

**Tareas:**

1. Implementar registro de usuarios
2. Sistema de login con JWT
3. Middleware de autenticación
4. Endpoints de perfil de usuario
5. Sistema de roles y permisos
6. Validación de datos con Pydantic

**Entregables:**

- API de autenticación funcional
- Sistema de roles implementado
- Documentación de endpoints

### **Etapa 3: Gestión de Productos (Semana 3)**

**Objetivos:**

- CRUD completo para productos
- Sistema de categorías
- Búsqueda y filtrado
- Gestión de inventario

**Tareas:**

1. Modelos de Product y Category
2. Endpoints CRUD para productos
3. Sistema de búsqueda y filtros
4. Gestión de imágenes de productos
5. Control de inventario
6. Panel de administración para productos

**Entregables:**

- API de productos completa
- Sistema de búsqueda funcional
- Panel administrativo básico

### **Etapa 4: Carrito de Compras (Semana 4)**

**Objetivos:**

- Sistema de carrito de compras
- Gestión de sesiones
- Validaciones de stock

**Tareas:**

1. Modelo de Cart y CartItem
2. Endpoints para gestión del carrito
3. Validación de disponibilidad de productos
4. Cálculo de totales y descuentos
5. Persistencia del carrito

**Entregables:**

- Sistema de carrito funcional
- Validaciones de negocio implementadas

### **Etapa 5: Sistema de Órdenes (Semana 5)**

**Objetivos:**

- Proceso de checkout
- Gestión de órdenes
- Estados de pedidos

**Tareas:**

1. Modelo de Order y OrderItem
2. Proceso de checkout
3. Gestión de estados de pedido
4. Historial de órdenes para usuarios
5. Panel administrativo para órdenes

**Entregables:**

- Sistema de órdenes completo
- Proceso de checkout funcional

### **Etapa 6: Integración de Pagos (Semana 6)**

**Objetivos:**

- Integrar Stripe para pagos
- Webhooks para confirmación
- Manejo de errores de pago

**Tareas:**

1. Configurar Stripe SDK
2. Crear Payment Intents
3. Implementar webhooks de Stripe
4. Manejo de estados de pago
5. Reembolsos y cancelaciones

**Entregables:**

- Integración de pagos funcional
- Webhooks configurados
- Manejo de errores robusto

### **Etapa 7: Funcionalidades Avanzadas (Semana 7)**

**Objetivos:**

- Notificaciones por email
- Optimizaciones de rendimiento
- Funciones adicionales

**Tareas:**

1. Sistema de notificaciones por email
2. Implementar cache con Redis
3. Optimización de consultas
4. Sistema de reviews/ratings (opcional)
5. Analytics básicos

**Entregables:**

- Sistema de notificaciones
- Optimizaciones implementadas

### **Etapa 8: Testing y Deployment (Semana 8)**

**Objetivos:**

- Testing completo
- Preparación para producción
- Documentación final

**Tareas:**

1. Tests unitarios y de integración
2. Configuración para producción
3. Docker containers
4. CI/CD básico
5. Documentación completa

**Entregables:**

- Suite de tests completa
- Aplicación lista para producción
- Documentación finalizada

## 📋 Modelos de Datos Principales

### User

- id, email, password_hash, first_name, last_name
- is_active, is_admin, created_at, updated_at

### Product

- id, name, description, price, stock_quantity
- category_id, image_urls, sku, is_active
- created_at, updated_at

### Category

- id, name, description, parent_id

### Cart

- id, user_id, created_at, updated_at

### CartItem

- id, cart_id, product_id, quantity, price_at_time

### Order

- id, user_id, total_amount, status, shipping_address
- created_at, updated_at

### OrderItem

- id, order_id, product_id, quantity, price_at_time

### Payment

- id, order_id, stripe_payment_intent_id, amount
- status, created_at

## 🔒 Consideraciones de Seguridad

1. **Autenticación**: JWT con expiración
2. **Autorización**: Middleware de roles
3. **Validación**: Pydantic para todos los inputs
4. **Rate Limiting**: Prevenir abuso de API
5. **CORS**: Configuración apropiada
6. **Variables sensibles**: Variables de entorno
7. **Sanitización**: Prevenir SQL injection
8. **HTTPS**: Solo en producción

## 🎯 Métricas de Éxito

- [ ] API completamente funcional
- [ ] Autenticación segura implementada
- [ ] Integración de pagos funcionando
- [ ] Tests con cobertura > 80%
- [ ] Documentación completa
- [ ] Rendimiento optimizado
- [ ] Deploy exitoso

## 🚀 Próximos Pasos

1. **Revisar y aprobar** esta estructura
2. **Inicializar proyecto con Poetry**:

   ```bash
   mkdir ecommerce_api
   cd ecommerce_api
   poetry init
   ```

3. **Configurar dependencias** en pyproject.toml
4. **Crear estructura** de directorios
5. **Comenzar con Etapa 1**

## 📦 Configuración inicial de Poetry

### pyproject.toml básico

```toml
[tool.poetry]
name = "ecommerce-api"
version = "0.1.0"
description = "E-commerce API with FastAPI"
authors = ["Tu Nombre <email@ejemplo.com>"]
packages = [{include = "app"}]

[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = "^2.0.23"
psycopg2-binary = "^2.9.9"
alembic = "^1.12.1"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"
python-dotenv = "^1.0.0"
stripe = "^7.8.0"
pydantic = {extras = ["email"], version = "^2.5.2"}

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
black = "^23.11.0"
flake8 = "^6.1.0"
isort = "^5.12.0"
httpx = "^0.25.2"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 88

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### Comandos útiles

```bash
# Instalar todas las dependencias
poetry install

# Agregar nueva dependencia
poetry add nueva-dependencia

# Agregar dependencia de desarrollo
poetry add --group dev nueva-dev-dependency

# Actualizar dependencias
poetry update

# Mostrar dependencias instaladas
poetry show

# Exportar requirements.txt (si es necesario)
poetry export -f requirements.txt --output requirements.txt
```

¿Te parece bien esta estructura? ¿Quieres que modifiquemos alguna etapa o tecnología?
