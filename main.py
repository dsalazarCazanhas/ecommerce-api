import logging
import sys

import uvicorn

from src.config.ext import settings

logger = logging.getLogger(__name__)


def main():
    """Main FastAPI server entrypoint."""
    is_dev_environment = settings.ENVIRONMENT == "development"
    reload_enabled = is_dev_environment and settings.UVICORN_RELOAD_IN_DEV
    effective_log_level = "debug" if settings.DEBUG else settings.UVICORN_LOG_LEVEL
    worker_count = 1 if reload_enabled else settings.UVICORN_WORKERS

    try:
        uvicorn.run(
            "src.app:app",
            host=settings.HOST,
            port=settings.PORT,
            log_level=effective_log_level,
            reload=reload_enabled,
            workers=worker_count,
            use_colors=settings.UVICORN_USE_COLORS,
            access_log=settings.UVICORN_ACCESS_LOG,
            server_header=settings.UVICORN_SERVER_HEADER,
            date_header=settings.UVICORN_DATE_HEADER,
            proxy_headers=settings.UVICORN_PROXY_HEADERS,
            forwarded_allow_ips=settings.UVICORN_FORWARDED_ALLOW_IPS,
            timeout_keep_alive=settings.UVICORN_TIMEOUT_KEEP_ALIVE,
        )
    except Exception as exc:
        logger.exception("Error running FastAPI: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
