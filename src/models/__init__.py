# Import all table models here to ensure SQLModel.metadata registers them
# before init_db() calls create_all().
# Without these imports, tables for models not explicitly imported in the app
# import tree would not be created at startup.
from src.models.auth import IdempotencyRecord, RefreshToken  # noqa: F401
from src.models.cart import Cart, CartItem  # noqa: F401
from src.models.order import Order, OrderItem, Payment  # noqa: F401
from src.models.products import Product  # noqa: F401
from src.models.stripe import StripeWebhookEvent  # noqa: F401
from src.models.users import User  # noqa: F401
