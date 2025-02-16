from starlette.applications import Starlette
from starlette_admin import I18nConfig
from starlette_admin.contrib.sqlmodel import Admin

from configs.engine import engine, init_db

app = Starlette(on_startup=[init_db])

admin = Admin(engine,
              title="ecommerce-admin",
              #base_url="/admin",
              #route_name="admin",
              #statics_dir="./statics",
              #favicon_url="./statics/favicon.svg",
              #templates_dir="./templates",
              #logo_url="/statics/home_icon.svg",
              #login_logo_url="/statics/home_icon.svg",
              #index_view=HomeView(),
              debug=True,
              i18n_config=I18nConfig(default_locale="en"),
              #auth_provider="",
              #middlewares=[]
              )

admin.mount_to(app)