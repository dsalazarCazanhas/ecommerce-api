from typing import Any, Dict
from httpx import HTTPStatusError, RequestError
from starlette_admin.contrib.sqlmodel import ModelView
from starlette.routing import Request

from src.security.creds import hash_password

class CustomUserView(ModelView):
    exclude_fields_from_list = ["password"] # Fields that should be excluded from list view
    async def before_create(
        self, request: Request, data: Dict[str, Any], obj: Any
    ) -> None:
        """
        This hook is called before a new item is created.

        Args:
            request: The request being processed.
            data: Dict values contained converted form data.
            obj: The object about to be created.
        """
        if obj.password:
            try:
                hashed_password = hash_password(obj.password)
                obj.password = hashed_password
            except Exception as e:
                raise Exception(f"Failed to create user {obj.name}: {e}")
            except (HTTPStatusError, RequestError) as exc:
                raise Exception(f"There was an error creating user:{exc.response}-{exc.request}")