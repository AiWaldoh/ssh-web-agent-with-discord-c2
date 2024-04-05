from init import Config, JAVASCRIPT_SCR
import os
import re
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import Page, ElementHandle
from urllib.parse import urlparse, parse_qs
from typing import List, Optional, Dict
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


class MessageValidator:
    def is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


class DiscordBrowser:
    def __init__(self, config: Config):
        self.config = config
        self.browser = None
        self.page = None
        self.additional_tab = None

    async def launch(self, playwright):
        self.browser = await playwright.chromium.launch(headless=False)

    async def login(self):
        session_file = os.path.join("secret", Config.SESSION_FILE)

        if not os.path.exists("secret"):
            os.makedirs("secret")

        if os.path.exists(session_file):
            self.context = await self.browser.new_context(storage_state=session_file)
            self.page = await self.context.new_page()
        else:
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            await self.page.goto("https://discord.com/login")
            await self._submit_login_form()
            await self._update_settings()
            await self.context.storage_state(path=session_file)

    async def get_additional_tab(self):
        if not self.additional_tab:
            self.additional_tab = await self.context.new_page()
        return self.additional_tab

    async def _update_settings(self):
        await self.page.wait_for_selector(".flex_f18b02")
        await self.page.click('button[aria-label="User Settings"]')
        await self.page.click('div[aria-label="Appearance"]')
        await self.page.click('label:has-text("Show avatars in Compact mode")')
        await self.page.click('div[aria-label="Close"]')

    async def _submit_login_form(self):
        await self.page.fill('input[name="email"]', self.config.USERNAME)
        await self.page.fill('input[name="password"]', self.config.PASSWORD)
        await self.page.click('button[type="submit"]')

    async def load_channel(self):
        print(f"Loading {self.config.DISCORD_CHANNEL_URL}")
        await self.page.goto(self.config.DISCORD_CHANNEL_URL)
        await self.page.wait_for_selector("div[role='textbox']")
        await asyncio.sleep(5)

    async def expose_on_message_function(self, on_message_callback):
        await self.page.expose_function("onNewMessage", on_message_callback)
        await self.page.evaluate(JAVASCRIPT_SCR)
        print("Listening for new messages...")

    async def get_hash_parameters(self) -> dict:
        current_url = await self.get_current_url()
        parsed_url = urlparse(current_url)
        fragment = parsed_url.fragment
        query_params = parse_qs(fragment)
        return {k: v[0] for k, v in query_params.items()}

    async def accept_alert(self):
        await self.page.accept_dialog()

    async def dismiss_alert(self):
        await self.page.dismiss_dialog()

    async def get_alert_text(self) -> str:
        return await self.page.dialog.message

    async def upload_file(self, selector: str, file_path: str):
        await self.page.set_input_files(selector, file_path)

    async def switch_to_frame(self, selector: str):
        frame = await self.page.frame(selector)
        self.page = frame

    async def execute_script(self, script: str):
        return await self.page.evaluate(script)

    async def click_and_wait_for_network_activity(self, selector, timeout=5000):
        pending_requests = 0

        async def request_handler(route, request):
            nonlocal pending_requests
            pending_requests += 1
            print(f"Request: {request.method} {request.url}")
            await route.continue_()

        async def response_handler(response):
            nonlocal pending_requests
            print(f"Response: {response.status} {response.url}")
            if response.status == 200 and response.request.method != "OPTIONS":
                pending_requests -= 1
                print(f"Pending requests: {pending_requests}")
                if pending_requests == 0:
                    await self.page.evaluate("window.networkActivityComplete = true")

        await self.page.route("**/*", request_handler)
        self.page.on("response", response_handler)

        await self.page.evaluate("window.networkActivityComplete = false")
        await self.page.click(selector)

        try:
            await self.page.wait_for_function(
                "window.networkActivityComplete === true", timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            print("Timeout occurred")
            return False
        finally:
            await self.page.unroute("**/*", request_handler)
            self.page.remove_listener("response", response_handler)

    async def navigate_to(self, url: str, page: Page = None, timeout: int = 30000):
        if page is None:
            page = self.page
        await page.goto(url, timeout=timeout)

    async def click_element(self, selector: str, timeout: int = 5000):
        try:
            await self.page.click(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(
                f"Timed out waiting for element '{selector}' to be clickable"
            )

    async def fill_input(self, selector: str, value: str, delay: int = 100):
        await self.page.type(selector, value, delay=delay)

    async def get_text(self, selector: str) -> str:
        return await self.page.inner_text(selector)

    async def take_screenshot(self, file_path: str):
        await self.page.screenshot(path=file_path)

    async def wait_for_selector(self, selector: str, timeout: int = 5000):
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(f"Timed out waiting for selector '{selector}'")

    async def wait_for_navigation(self, page: Page = None, timeout: int = 30000):
        if page is None:
            page = self.page
        await page.wait_for_load_state("networkidle", timeout=timeout)

    async def find_elements(self, selector: str) -> List[ElementHandle]:
        return await self.page.query_selector_all(selector)

    async def get_current_url(self) -> str:
        return await self.page.url

    async def go_back(self, timeout: int = 30000):
        await self.page.go_back(timeout=timeout)

    async def go_forward(self, timeout: int = 30000):
        await self.page.go_forward(timeout=timeout)

    async def refresh_page(self, timeout: int = 30000):
        await self.page.reload(timeout=timeout)

    async def is_element_visible(self, selector: str) -> bool:
        element = await self.page.query_selector(selector)
        if element:
            return await element.is_visible()
        return False

    async def is_element_enabled(self, selector: str) -> bool:
        element = await self.page.query_selector(selector)
        if element:
            return await element.is_enabled()
        return False

    async def get_input_value(self, selector: str) -> Optional[str]:
        element = await self.page.query_selector(selector)
        if element:
            return await element.get_attribute("value")
        return None

    async def evaluate_javascript(self, script: str):
        return await self.page.evaluate(script)

    async def close(self):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def close(self):
        await self.browser.close()


class NavigationError(Exception):
    pass


class ElementNotFoundError(Exception):
    pass


class InteractionError(Exception):
    pass


class MessageExtractor:
    def extract_message_data(self, message_soup):
        user_id = self._extract_user_id(message_soup)
        has_mention = self._contains_mention(message_soup)
        username = self._extract_username(message_soup)
        message_text = self._extract_message_text(message_soup, has_mention)
        # print(f"return data: {user_id}, {username}, {has_mention}, {message_text}")
        return {
            "user_id": user_id,
            "username": username,
            "has_mention": has_mention,
            "message_text": message_text.strip(),
        }

    def _extract_user_id(self, message_soup):
        img_src = message_soup.find("img")["src"] if message_soup.find("img") else None
        return self._parse_user_id(img_src)

    def _contains_mention(self, message_soup):
        mention = message_soup.select_one('span[class*="mention"]')
        return mention and mention.text.startswith(Config.BOT_NAME)

    def _extract_username(self, message_soup):
        username_element = message_soup.find(
            "span", class_=lambda x: x and "username" in x
        )
        return username_element.text.strip() if username_element else None

    def _extract_message_text(self, message_soup, has_mention):
        message_div = self._find_message_div(message_soup)
        if message_div:
            message_spans = self._find_message_spans(message_div)
            mention_span = self._find_mention_span(message_div) if has_mention else None
            return self._combine_message_text(message_spans, mention_span).strip()
        else:
            return ""

    def _find_message_div(self, message_soup):
        return message_soup.select_one('div[class*="markup"]')

    def _find_message_spans(self, message_div):
        return message_div.find_all("span")

    def _find_mention_span(self, message_div):
        return message_div.select_one('span[class*="mention"]')

    def _combine_message_text(self, message_spans, mention_span=None):
        if mention_span:
            return (
                mention_span.get_text()
                + " "
                + " ".join(
                    span.get_text() for span in message_spans if span != mention_span
                )
            )
        else:
            return " ".join(span.get_text() for span in message_spans)

    def _parse_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            return match.group(1) if match else None
        return None


class MessageParser:
    def __init__(
        self, message_extractor: MessageExtractor, message_validator: MessageValidator
    ):
        self.message_extractor = message_extractor
        self.message_validator = message_validator

    def parse_message(self, message_html):
        if not self.message_validator.is_valid_message(message_html):
            return None

        message_soup = BeautifulSoup(message_html, "html.parser")
        return self.message_extractor.extract_message_data(message_soup)
