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
    SSH_HOST = os.getenv("SSH_HOST")
    SSH_PORT = int(os.getenv("SSH_PORT"))
    SSH_USERNAME = os.getenv("SSH_USERNAME")
    SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

    def __init__(self):
        if not self.SSH_KEY_PATH:
            raise ValueError("SSH_KEY_PATH is not set")
        if not self.SSH_HOST:
            raise ValueError("SSH_HOST is not set")
        if not self.SSH_PORT:
            raise ValueError("SSH_PORT is not set")
        if not self.SSH_USERNAME:
            raise ValueError("SSH_USERNAME is not set")
        if not self.BOT_NAME:
            raise ValueError("BOT_NAME is not set")
        if not self.MODEL_NAME:
            raise ValueError("MODEL_NAME is not set")
        if not self.API_URL:
            raise ValueError("API_URL is not set")
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
        if not self.ADMIN_USER_ID:
            raise ValueError("ADMIN_USER_ID is not set")
        if not self.SESSION_FILE:
            raise ValueError("SESSION_FILE is not set")
        if not self.SYSTEM_MESSAGE:
            raise ValueError("SYSTEM_MESSAGE is not set")
        if not self.DISCORD_CHANNEL_URL:
            raise ValueError("DISCORD_CHANNEL_URL is not set")
        if not self.BASE_URL:
            raise ValueError("BASE_URL is not set")
