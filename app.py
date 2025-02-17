from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette_csrf import CSRFMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route, RedirectResponse
from starlette_admin import I18nConfig
from starlette_admin.contrib.sqlmodel import Admin
from starlette_admin.auth import AuthProvider

from configs.engine import engine, init_db
from configs.ext import SESSION_KEY, CSRF_KEY
from src.customViews.index import HomeView
from src.customViews.users_view import CustomUserView
from src.models.users import User
from src.security.auth import AuthRequiredMiddleware

# Redirect root URL '/' to '/admin'
async def redirection(request):
    return RedirectResponse(url='/admin')

routes = [
    Route('/', endpoint=redirection),
]

app = Starlette(on_startup=[init_db], routes=routes)
app.add_middleware(AuthRequiredMiddleware, login_path="/admin/login")

admin = Admin(engine,
              title="ecommerce-admin",
              base_url="/admin",
              route_name="admin",
              statics_dir="./statics",
              favicon_url="./statics/favicon.ico",
              templates_dir="./templates",
              index_view=HomeView(),
              debug=True,
              i18n_config=I18nConfig(default_locale="en"),
              auth_provider=AuthProvider(login_path="/login", logout_path="/logout", allow_routes=["login", "logout"]),
              middlewares=[Middleware(SessionMiddleware, secret_key=SESSION_KEY, https_only=False),
                            Middleware(TrustedHostMiddleware,allowed_hosts=['localhost',
                                                                            '127.0.0.1']),
                            Middleware(CSRFMiddleware, secret=CSRF_KEY),
                            #Middleware(HTTPSRedirectMiddleware),
                            Middleware(CORSMiddleware, allow_origins=['*'], 
                                       allow_methods=['GET', 'POST'])])

admin.add_view(CustomUserView(model=User, label="Users", icon="fa fa-user"))

admin.mount_to(app)