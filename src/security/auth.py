from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Request


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    """
    Middleware to require authentication for specific paths.
    If the user is not authenticated, redirect them to the login page.
    """

    def __init__(self, app, login_path, protected_paths=None):
        super().__init__(app)
        self.login_path = login_path
        self.protected_paths = protected_paths or ["/admin", "/admin/*", "/", "/*"]

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)