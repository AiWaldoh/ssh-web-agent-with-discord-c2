import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_NAME = os.getenv("BOT_NAME")
    MODEL_NAME = os.getenv("MODEL_NAME")
    API_URL = os.getenv("API_URL")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
    SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
    SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")
    DISCORD_CHANNEL_URL = os.getenv("DISCORD_CHANNEL_URL")
    BASE_URL = os.getenv("BASE_URL")
