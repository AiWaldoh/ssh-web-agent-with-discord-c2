import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import yaml
from enum import Enum
from dataclasses import dataclass
from typing import List
import subprocess
from abc import ABC, abstractmethod
import asyncio
from playwright.async_api import async_playwright


JAVASCRIPT_SCR = """
                var target = document.querySelector('main[class^="chatContent"]');
                var observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList') {
                            mutation.addedNodes.forEach(function(node) {
                                window.onNewMessage(JSON.stringify(node.outerHTML));
                            });
                        }
                    });
                });
                var config = { childList: true, subtree: true };
                observer.observe(target, config);
            """


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str


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
    USERNAME = os.getenv("DISCORD_EMAIL")
    PASSWORD = os.getenv("DISCORD_PASSWORD")
    TEMPERATURE = float(os.getenv("TEMPERATURE", 1.2))
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")


class ToolLoader:
    def __init__(self):
        self.tools = []

    def load_tools_from_yaml(self, file_path):
        with open(file_path, "r") as file:
            tools_data = yaml.safe_load(file)
            self.tools = tools_data["tools"]


class MessageStore:
    def __init__(self, initial_system_message: str):
        self.messages: List[Message] = [
            Message(role=Role.SYSTEM, content=initial_system_message)
        ]

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages(self) -> List[Message]:
        return self.messages

    def truncate_history(self, max_history: int):
        user_messages = [msg for msg in self.messages if msg.role == Role.USER]
        if len(user_messages) > max_history:
            trim_index = len(self.messages) - len(user_messages) + max_history
            self.messages = self.messages[trim_index:]
