# import os
# import re
# from dotenv import load_dotenv
# from bs4 import BeautifulSoup
# import requests
# import yaml
# from enum import Enum
# from dataclasses import dataclass
# from typing import List, Optional, Dict
# import subprocess
# from abc import ABC, abstractmethod
# import asyncio
# from playwright.async_api import async_playwright
# import json
# from search.google_searcher import GoogleSearcher
# from search.search_result import SearchResult
# from datetime import datetime
# from urllib.parse import parse_qs, urlparse
# from playwright.sync_api import sync_playwright
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, ElementHandle
# from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
# from urllib.parse import urlparse, parse_qs
# from typing import List, Optional

# class PlaywrightBrowserWrapper:
#     async def __init__(self, browser_type="chromium", headless=False):
#         self.playwright = await async_playwright().start()
#         self.browser = await self.playwright[browser_type].launch(headless=headless)
#         self.context = await self.browser.new_context()
#         self.page = await self.context.new_page()

#     async def get_hash_parameters(self) -> dict:
#         current_url = await self.get_current_url()
#         parsed_url = urlparse(current_url)
#         fragment = parsed_url.fragment
#         query_params = parse_qs(fragment)
#         return {k: v[0] for k, v in query_params.items()}

#     async def accept_alert(self):
#         await self.page.accept_dialog()

#     async def dismiss_alert(self):
#         await self.page.dismiss_dialog()

#     async def get_alert_text(self) -> str:
#         return await self.page.dialog.message

#     async def upload_file(self, selector: str, file_path: str):
#         await self.page.set_input_files(selector, file_path)

#     async def switch_to_frame(self, selector: str):
#         frame = await self.page.frame(selector)
#         self.page = frame

#     async def execute_script(self, script: str):
#         return await self.page.evaluate(script)

#     async def click_and_wait_for_network_activity(self, selector, timeout=5000):
#         pending_requests = 0

#         async def request_handler(route, request):
#             nonlocal pending_requests
#             pending_requests += 1
#             print(f"Request: {request.method} {request.url}")
#             await route.continue_()

#         async def response_handler(response):
#             nonlocal pending_requests
#             print(f"Response: {response.status} {response.url}")
#             if response.status == 200 and response.request.method != "OPTIONS":
#                 pending_requests -= 1
#                 print(f"Pending requests: {pending_requests}")
#                 if pending_requests == 0:
#                     await self.page.evaluate("window.networkActivityComplete = true")

#         await self.page.route("**/*", request_handler)
#         self.page.on("response", response_handler)

#         await self.page.evaluate("window.networkActivityComplete = false")
#         await self.page.click(selector)

#         try:
#             await self.page.wait_for_function(
#                 "window.networkActivityComplete === true", timeout=timeout
#             )
#             return True
#         except PlaywrightTimeoutError:
#             print("Timeout occurred")
#             return False
#         finally:
#             await self.page.unroute("**/*", request_handler)
#             self.page.remove_listener("response", response_handler)

#     async def navigate_to(self, url: str, timeout: int = 30000):
#         await self.page.goto(url, timeout=timeout)

#     async def click_element(self, selector: str, timeout: int = 5000):
#         try:
#             await self.page.click(selector, timeout=timeout)
#         except PlaywrightTimeoutError:
#             raise TimeoutError(
#                 f"Timed out waiting for element '{selector}' to be clickable"
#             )

#     async def fill_input(self, selector: str, value: str, delay: int = 100):
#         await self.page.type(selector, value, delay=delay)

#     async def get_text(self, selector: str) -> str:
#         return await self.page.inner_text(selector)

#     async def take_screenshot(self, file_path: str):
#         await self.page.screenshot(path=file_path)

#     async def wait_for_selector(self, selector: str, timeout: int = 5000):
#         try:
#             await self.page.wait_for_selector(selector, timeout=timeout)
#         except PlaywrightTimeoutError:
#             raise TimeoutError(f"Timed out waiting for selector '{selector}'")

#     async def wait_for_navigation(self, timeout: int = 30000):
#         await self.page.wait_for_load_state("networkidle", timeout=timeout)

#     async def find_elements(self, selector: str) -> List[ElementHandle]:
#         return await self.page.query_selector_all(selector)

#     async def get_current_url(self) -> str:
#         return await self.page.url

#     async def go_back(self, timeout: int = 30000):
#         await self.page.go_back(timeout=timeout)

#     async def go_forward(self, timeout: int = 30000):
#         await self.page.go_forward(timeout=timeout)

#     async def refresh_page(self, timeout: int = 30000):
#         await self.page.reload(timeout=timeout)

#     async def is_element_visible(self, selector: str) -> bool:
#         element = await self.page.query_selector(selector)
#         if element:
#             return await element.is_visible()
#         return False

#     async def is_element_enabled(self, selector: str) -> bool:
#         element = await self.page.query_selector(selector)
#         if element:
#             return await element.is_enabled()
#         return False

#     async def get_input_value(self, selector: str) -> Optional[str]:
#         element = await self.page.query_selector(selector)
#         if element:
#             return await element.get_attribute("value")
#         return None

#     async def evaluate_javascript(self, script: str):
#         return await self.page.evaluate(script)

#     async def close(self):
#         await self.context.close()
#         await self.browser.close()
#         await self.playwright.stop()



# class NavigationError(Exception):
#     pass


# class ElementNotFoundError(Exception):
#     pass


# class InteractionError(Exception):
#     pass
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import yaml
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
import subprocess
from abc import ABC, abstractmethod
import asyncio
from playwright.async_api import async_playwright
import json
from search.google_searcher import GoogleSearcher
from search.search_result import SearchResult
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, ElementHandle

class PlaywrightBrowserWrapper:
    def __init__(self, browser_type="chromium", headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright[browser_type].launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def get_hash_parameters(self) -> dict:
        current_url = self.get_current_url()
        parsed_url = urlparse(current_url)
        fragment = parsed_url.fragment
        query_params = parse_qs(fragment)
        return {k: v[0] for k, v in query_params.items()}

    def accept_alert(self):
        self.page.accept_dialog()

    def dismiss_alert(self):
        self.page.dismiss_dialog()

    def get_alert_text(self) -> str:
        return self.page.dialog.message

    def upload_file(self, selector: str, file_path: str):
        self.page.set_input_files(selector, file_path)

    def switch_to_frame(self, selector: str):
        frame = self.page.frame(selector)
        self.page = frame

    def execute_script(self, script: str):
        return self.page.evaluate(script)

    def click_and_wait_for_network_activity(self, selector, timeout=5000):
        pending_requests = 0

        def request_handler(route, request):
            nonlocal pending_requests
            pending_requests += 1
            print(f"Request: {request.method} {request.url}")
            route.continue_()

        def response_handler(response):
            nonlocal pending_requests
            print(f"Response: {response.status} {response.url}")
            if response.status == 200 and response.request.method != "OPTIONS":
                pending_requests -= 1
                print(f"Pending requests: {pending_requests}")
                if pending_requests == 0:
                    self.page.evaluate("window.networkActivityComplete = true")

        self.page.route("**/*", request_handler)
        self.page.on("response", response_handler)

        self.page.evaluate("window.networkActivityComplete = false")
        self.page.click(selector)

        try:
            self.page.wait_for_function(
                "window.networkActivityComplete === true", timeout=timeout
            )
            return True
        except TimeoutError:
            print("Timeout occurred")
            return False
        finally:
            self.page.unroute("**/*", request_handler)
            self.page.remove_listener("response", response_handler)

    def navigate_to(self, url: str, timeout: int = 30000):
        self.page.goto(url, timeout=timeout)

    def click_element(self, selector: str, timeout: int = 5000):
        try:
            self.page.click(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(
                f"Timed out waiting for element '{selector}' to be clickable"
            )

    def fill_input(self, selector: str, value: str, delay: int = 100):
        self.page.type(selector, value, delay=delay)

    def get_text(self, selector: str) -> str:
        return self.page.inner_text(selector)

    def take_screenshot(self, file_path: str):
        self.page.screenshot(path=file_path)

    def wait_for_selector(self, selector: str, timeout: int = 5000):
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(f"Timed out waiting for selector '{selector}'")

    def wait_for_navigation(self, timeout: int = 30000):
        self.page.wait_for_load_state("networkidle", timeout=timeout)

    def find_elements(self, selector: str) -> List[ElementHandle]:
        return self.page.query_selector_all(selector)

    def get_current_url(self) -> str:
        return self.page.url

    def go_back(self, timeout: int = 30000):
        self.page.go_back(timeout=timeout)

    def go_forward(self, timeout: int = 30000):
        self.page.go_forward(timeout=timeout)

    def refresh_page(self, timeout: int = 30000):
        self.page.reload(timeout=timeout)

    def is_element_visible(self, selector: str) -> bool:
        element = self.page.query_selector(selector)
        if element:
            return element.is_visible()
        return False

    def is_element_enabled(self, selector: str) -> bool:
        element = self.page.query_selector(selector)
        if element:
            return element.is_enabled()
        return False

    def get_input_value(self, selector: str) -> Optional[str]:
        element = self.page.query_selector(selector)
        if element:
            return element.get_attribute("value")
        return None

    def evaluate_javascript(self, script: str):
        return self.page.evaluate(script)

    def close(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()


class NavigationError(Exception):
    pass


class ElementNotFoundError(Exception):
    pass


class InteractionError(Exception):
    pass
