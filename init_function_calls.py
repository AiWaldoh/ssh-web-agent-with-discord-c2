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


class AITaskCommand(ABC):
    @abstractmethod
    def execute(self, arguments):
        pass


class AITaskRegistry:
    _instance = None
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, task_name, command):
        cls._registry[task_name] = command

    @classmethod
    def get_command(cls, task_name):
        return cls._registry.get(task_name)


class ExecuteCommandTask(AITaskCommand):
    def execute(self, arguments):
        command = arguments.get("command")
        if command:
            print(f"Executing command: {command}")
            output = subprocess.check_output(
                command, shell=True, universal_newlines=True
            )
            return output
        else:
            print("No command provided.")
            return "No command provided."


class SearchGoogleTask(AITaskCommand):
    def execute(self, arguments):
        search_query = arguments.get("search_query")
        if search_query:
            print(f"Searching for: {search_query}")
            return "Search results"
        else:
            print("No search query provided.")
            return "No search query provided."


class LoadWebsiteTask(AITaskCommand):
    def execute(self, arguments):
        website_url = arguments.get("website_url")
        if website_url:
            print(f"Loading website: {website_url}")
            return "Website loaded"
        else:
            print("No website URL provided.")
            return "No website URL provided."
