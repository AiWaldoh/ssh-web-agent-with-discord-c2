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
import json
from search.google_searcher import GoogleSearcher
from search.search_result import SearchResult


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
            results = GoogleSearcher.search(search_query, 10)
            print(f"Search results: {results}")
            return results
        else:
            print("No search query provided.")
            return "No search query provided."


class LoadWebsiteTask(AITaskCommand):
    def execute(self, arguments):
        website_url = arguments.get("website_url")
        print(f"Loading website: {website_url}")
        if website_url:
            searcher = SearchResult("title", website_url, "description")
            # print(f"sending for: {website_url}")
            res = searcher.fetch_and_parse_article()
            print("1")
            res = self.trim_by_chars(res, 1500)
            print("2")
            return res

        else:
            print("No website URL provided.")
            return "No website URL provided."

    def trim_by_chars(self, res, limit):
        print(res)
        print("3")
        return f"```{res['text'][:limit]}```\nJust click the link for more..."
