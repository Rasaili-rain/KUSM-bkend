import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.IAMMETER_TOKEN = os.getenv("IAMMETER_TOKEN")
        self.IAMMETER_COOKIE = os.getenv("IAMMETER_COOKIE")

        self.PORT = int(os.environ.get("PORT", 8000))

        self.ENV = os.getenv("ENV", "debug")

        self.ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 1

        self.ALGORITHM: str = "HS256"

        assert self.DATABASE_URL is not None, "DATABASE_URL is missing in .env"
        assert self.SECRET_KEY is not None, "SECRET_KEY is missing in .env"
        assert self.IAMMETER_TOKEN is not None, "IAMMETER_TOKEN is missing in .env"


settings = Settings()
