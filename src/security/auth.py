from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette_admin.auth import AuthProvider
from starlette_admin.exceptions import LoginFailed
from starlette.routing import Request, Response
from sqlalchemy.exc import DBAPIError
import time

from utils.funcdb import get_user_by_username
from security.creds import verify_password

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
    
class CustomAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        token = request.headers.get('Authorization')
        if not token:
            try:
                user = get_user_by_username(username)
                if user & verify_password(plain_password=password, stored_password=user.password):
                    # Store the username or relevant token data in the session
                    now = time.time()
                    request.session.update({'username': username,
                                    'refresh_token': enc_refresh_token,
                                    'access_token': token_data['access_token'],
                                    'expires_in': token_data['expires_in']+now,
                                    'refresh_expires_in': token_data['refresh_expires_in']+now
                                    })
                    # Check for 'next' parameter in the request, or redirect to the default page
                    next_url = request.query_params.get('next', '/')
                    response = RedirectResponse(url=next_url, status_code=303)
            except (DBAPIError) as exc:
                raise LoginFailed(exc.error_message)
        if token_data:
            enc_refresh_token = encrypt_token(token_data['refresh_token'])

            return response

        raise LoginFailed("Invalid username or password")

    async def logout(self, request: Request, response: Response) -> Response:
        # Decrypt the token
        refresh_token = decrypt_token(request.session.get("refresh_token"))
        if refresh_token:
            try:
                keycloak.keycloak_openid.logout(refresh_token=refresh_token)

            except (Exception, KeycloakPostError,
                    KeycloakInvalidTokenError,
                    KeycloakConnectionError):
                    request.session.clear()
                    return response

        request.session.clear()
        return response

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get('username')
        if not username:
            return False

        """Refresh the access token if it is close to expiring."""
        # If access token is about to expire but refresh token is valid, attempt refresh
        expires_in = request.session.get("expires_in")
        refresh_expires_in = request.session.get("refresh_expires_in")
        now = time.time()
        if refresh_expires_in >= now >= expires_in:
            # Retrieve the refresh token
            refresh_token = decrypt_token(request.session.get("refresh_token"))
            # Refresh the keycloak session
            token_data = keycloak.keycloak_openid.refresh_token(refresh_token)
            # Encrypt the refresh token again
            enc_refresh_token = encrypt_token(token_data['refresh_token'])
            # Update session with new tokens and expiration
            try:
                request.session.update({"refresh_token": enc_refresh_token,
                                        "access_token": token_data['access_token'],
                                        "expires_in": token_data['expires_in'] + now,
                                        "refresh_expires_in": token_data['refresh_expires_in'] + now
                                        })
            except (Exception, KeycloakPostError,
                    KeycloakInvalidTokenError,
                    KeycloakConnectionError) as e:
                # If refresh fails, clear session and require re-authentication
                request.session.clear()
                print(f"Token refresh failed: {e}")
                return False
        elif now > refresh_expires_in:
            request.session.clear()
            return False

        return True