import os
import sys
import logging
import uvicorn

from src.config.ext import settings 


logger = logging.getLogger(__name__)

def main():
    """Punto de entrada principal del servidor FastAPI."""
    try:
        uvicorn.run("src.app:app", host=settings.HOST, port=settings.PORT, log_level=settings.DEBUG, use_colors=True)
    except Exception as e:
        logger.exception(f"❌ Error running FastAPI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
