import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.IAMMETER_TOKEN = os.getenv("IAMMETER_TOKEN")

        self.REDIRECT_URI = "http://localhost:8000/auth/google/callback" 
        # the redirect uri asserts that you host both fend and bkend on the same device 
        # because google oauth doesnot allows you to redirect via raw ip , it allows only with a proper domain name 
        # or just localhost so we cant just host a server in one and fend in another device :( 
        # TODO : @prod
        # In Prod be sure to add origin and redirect url of the frontend in here
        # https://console.cloud.google.com/apis/credentials?project=vivid-grammar-383903
        # and also update REDIRECT_URI with the backend server ip
        
        self.GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
        self.GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
        self.GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
        
        assert self.DATABASE_URL is not None,   "DATABASE_URL is missing in .env"
        assert self.GOOGLE_CLIENT_ID is not None, "GOOGLE_CLIENT_ID is missing in .env"
        assert self.GOOGLE_CLIENT_SECRET is not None, "GOOGLE_CLIENT_SECRET is missing in .env"
        assert self.SECRET_KEY is not None, "SECRET_KEY is missing in .env"
        assert self.IAMMETER_TOKEN is not None, "IAMMETER_TOKEN is missing in .env"


settings = Settings()
