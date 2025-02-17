from typing import List, Optional
from starlette_admin import CustomView
from starlette.routing import Request, Response
from starlette.templating import Jinja2Templates

from src.models.users import User
from utils.funcdb import get_total_entries_by_model


class HomeView(CustomView):
    def __init__(
            self,
            label: str = "Admin-Home",
            icon: Optional[str] = None,
            path: str = "/",
            template_path: str = "index.html",
            name: Optional[str] = None,
            methods: Optional[List[str]] = None,
            add_to_menu: bool = False,
    ):
        super().__init__(label=label, icon=icon, path=path, template_path=template_path,
                         name=name, methods=methods, add_to_menu=add_to_menu)

    async def render(self, request: Request, templates: Jinja2Templates) -> Response:
        """Default methods to render view. Override this methods to add your custom logic."""
        cant_users = get_total_entries_by_model(model=User)
        return templates.TemplateResponse(
            self.template_path, {"request": request,
                                 "title": self.title(request),
                                 "cant_users": cant_users}
        )

    def is_active(self, request: Request) -> bool:
        return request.scope["path"] == self.path