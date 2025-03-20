import os
import dotenv

dotenv.load_dotenv()
DATABASE_URL: str = os.getenv("DATABASE_URL")
SALT: str = os.getenv("SALT")
PEPPER: str = os.getenv("PEPPER")
VINAGER: str = os.getenv("VINAGER")
SESSION_KEY: str = os.getenv("SESSION_KEY")
CSRF_KEY: str = os.getenv("CSRF_KEY")
