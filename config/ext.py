import os
import dotenv

dotenv.load_dotenv()
DATABASE_URL: str = os.getenv("DATABASE_URL")

