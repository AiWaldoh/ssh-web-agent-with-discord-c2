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
from datetime import datetime


class AITaskCommand(ABC):
    @abstractmethod
    def execute(self, arguments):
        pass

    @abstractmethod
    def process_result(self, result, response):
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

    def process_result(self, result, response):
        output = f"```{result}```"
        response.chat_memory_response = output
        response.chat_response = output


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

    def process_result(self, result, response):
        result_message = ""
        for item in result:
            description = f"```{item.description}```"
            result_message += f" <{item.url}>\n{description}\n"
        response.chat_memory_response = result_message
        response.chat_response = result_message


class LoadWebsiteTask(AITaskCommand):
    def execute(self, arguments):
        website_url = arguments.get("website_url")
        if website_url:
            print(f"Loading website: {website_url}")
            searcher = SearchResult("title", website_url, "description")
            res = searcher.fetch_and_parse_article()
            res = self.trim_by_chars(res, 1500)
            return res
        else:
            print("No website URL provided.")
            return "No website URL provided."

    def process_result(self, result, response):
        response.chat_memory_response = "OK"
        response.chat_response = result

    def trim_by_chars(self, text, max_chars):
        if len(text) <= max_chars:
            return text
        else:
            return text[:max_chars] + "..."


class GoToPageTask(AITaskCommand):
    async def execute(self, arguments, dependencies):
        print("go to page task")
        url = arguments.get("url")
        print(f"url: {url}")
        if url:
            print("getting additional tab")
            additional_tab = await dependencies.browser.get_additional_tab()
            print("got additional tab")
            await dependencies.browser.navigate_to(url, page=additional_tab)
            print("navigated to url")
            await dependencies.browser.wait_for_navigation(page=additional_tab)
            print(f"navigated to url: {url}")

            return f"Navigated to URL: {url}"
        else:
            return "No URL provided."

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class TakeScreenshotTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        folder_name = "screenshots"
        os.makedirs(folder_name, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{folder_name}/screenshot_{timestamp}.png"

        dependencies.browser.take_screenshot(file_name)

        print(f"Screenshot captured and saved as: {file_name}")
        return file_name

    def process_result(self, result, response):
        response.chat_memory_response = f"Screenshot saved as: {result}"
        response.chat_response = f"Screenshot saved as: {result}"


class ClickElementTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        selector = arguments.get("selector")
        if selector:
            dependencies.browser.click_and_wait_for_network_activity(selector)
            return f"Click interaction performed on element: {selector}"
        else:
            return "No selector provided."

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class FormDetailsTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        return dependencies.feedback_provider.get_form_details_feedback()

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class LinksTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        return dependencies.feedback_provider.get_links_feedback()

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class ButtonsTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        return dependencies.feedback_provider.get_buttons_feedback()

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class SubmitFormTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        selector = arguments.get("selector")
        if selector:
            dependencies.browser.click_element(selector)
            return f"Form submitted successfully using selector: {selector}"
        else:
            return "No selector provided for form submission."

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class GetPageSourceTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        page_source = dependencies.browser.page.content()
        page_source = "Page source retrieval not implemented."
        return f"Page source:\n{page_source}"

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class GetCurrentUrlTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        current_url = dependencies.browser.get_current_url()
        current_url = "Current URL retrieval not implemented."
        return f"Current URL: {current_url}"

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result


class FillInputTask(AITaskCommand):
    def execute(self, arguments, dependencies):
        selector = arguments.get("selector")
        value = arguments.get("value")
        if selector and value:
            dependencies.browser.fill_input(selector, value)
            return f"Fill interaction performed on element: {selector}"
        else:
            return "Selector or value not provided."

    def process_result(self, result, response):
        response.chat_memory_response = result
        response.chat_response = result
