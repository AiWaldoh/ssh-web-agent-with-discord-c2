from init import Config, JAVASCRIPT_SCR
import os
import re
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import Page, ElementHandle
from urllib.parse import urlparse, parse_qs
from typing import Any, List, Optional, Dict
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from datetime import datetime


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


class PageAnalyzer:
    def __init__(self, browser):
        self.browser = browser

    async def get_forms(self) -> List[Dict[str, Any]]:
        forms = []
        #belongs to custom class
        page = await self.browser.get_additional_tab()
        elements = await page.query_selector_all("form")
        for element in elements:
            form_data = {
                "id": await element.get_attribute("id"),
                "class": await element.get_attribute("class"),
                "action": await element.get_attribute("action"),
                "method": await element.get_attribute("method"),
                "inputs": [],
                "buttons": [],
            }
            input_elements = await element.query_selector_all("input, textarea, select")
            input_data_list = await asyncio.gather(
                *[self.get_input_data(input_element) for input_element in input_elements]
            )
            form_data["inputs"].extend(input_data_list)

            button_elements = await element.query_selector_all("button")
            button_data_list = await asyncio.gather(
                *[self.get_button_data(button_element) for button_element in button_elements]
            )
            form_data["buttons"].extend(button_data_list)

            forms.append(form_data)

        return forms

    async def get_input_data(self,input_element):
        return {
            "type": await input_element.get_attribute("type"),
            "name": await input_element.get_attribute("name"),
            "value": await input_element.get_attribute("value"),
            "id": await input_element.get_attribute("id"),
            "class": await input_element.get_attribute("class"),
        }

    async def get_button_data(self,button_element):
        return {
            "type": await button_element.get_attribute("type"),
            "text": await button_element.text_content(),
            "id": await button_element.get_attribute("id"),
            "class": await button_element.get_attribute("class"),
        }

    def get_canonical_url(self) -> str:
        element = self.browser.page.query_selector('link[rel="canonical"]')
        if element:
            return element.get_attribute("href")
        return ""

    def get_meta_robots(self) -> List[str]:
        element = self.browser.page.query_selector('meta[name="robots"]')
        if element:
            content = element.get_attribute("content")
            return content.split(",")
        return []

    def get_open_graph_data(self) -> Dict[str, str]:
        og_data = {}
        elements = self.browser.find_elements('meta[property^="og:"]')
        for element in elements:
            property_name = element.get_attribute("property")
            content = element.get_attribute("content")
            og_data[property_name] = content
        return og_data

    def get_page_title(self) -> str:
        return self.browser.page.title()

    def get_headings(self) -> List[Dict[str, str]]:
        headings = []
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            elements = self.browser.find_elements(tag)
            for element in elements:
                headings.append({"tag": tag, "text": element.text_content()})
        return headings

    def get_paragraphs(self) -> List[str]:
        paragraphs = []
        elements = self.browser.find_elements("p")
        for element in elements:
            paragraphs.append(element.text_content())
        return paragraphs

    def get_links(self) -> List[Dict[str, str]]:
        links = []
        elements = self.browser.find_elements("a")
        for element in elements:
            links.append(
                {"url": element.get_attribute("href"), "text": element.text_content()}
            )
        return links

    def get_input_fields(self) -> List[Dict[str, str]]:
        input_fields = []
        elements = self.browser.find_elements("input")
        for element in elements:
            input_fields.append(
                {
                    "type": element.get_attribute("type"),
                    "name": element.get_attribute("name"),
                }
            )
        return input_fields

    def get_buttons(self) -> List[str]:
        buttons = []
        elements = self.browser.find_elements("button")
        for element in elements:
            buttons.append(element.text_content())
        return buttons

    def get_meta_description(self) -> str:
        meta_element = self.browser.page.query_selector('meta[name="description"]')
        if meta_element:
            return meta_element.get_attribute("content")
        return ""

    def get_meta_keywords(self) -> List[str]:
        meta_element = self.browser.page.query_selector('meta[name="keywords"]')
        if meta_element:
            content = meta_element.get_attribute("content")
            return content.split(",")
        return []

    def get_page_text(self) -> str:
        return self.browser.page.content()

    def get_images(self) -> List[str]:
        images = []
        elements = self.browser.find_elements("img")
        for element in elements:
            images.append(element.get_attribute("src"))
        return images

    def get_css_classes(self) -> List[str]:
        classes = []
        elements = self.browser.find_elements("*")
        for element in elements:
            class_attr = element.get_attribute("class")
            if class_attr:
                classes.extend(class_attr.split())
        return list(set(classes))

    def get_css_ids(self) -> List[str]:
        ids = []
        elements = self.browser.find_elements("*")
        for element in elements:
            id_attr = element.get_attribute("id")
            if id_attr:
                ids.append(id_attr)
        return list(set(ids))

    def get_javascript_events(self) -> List[str]:
        events = []
        elements = self.browser.find_elements("*")
        for element in elements:
            event_handlers = element.evaluate(
                "(el) => Object.keys(el.__proto__).filter(key => key.startsWith('on'))"
            )
            if event_handlers:
                events.extend(event_handlers)
        return list(set(events))


import json


class PageInfoSaver:
    def __init__(self, base_directory="llm_memory"):
        self.base_directory = base_directory
        self.create_directory()

    def create_directory(self):
        if not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory)

    def get_form_elements(self, form_id):
        # Implement the logic to retrieve form elements based on the form ID
        # You can load the JSON file and extract the relevant form information
        pass

    def save_page_info(self, url, forms):
        timestamp = datetime.now().strftime("%d-%B-%Y-%H-%M-%S")
        file_name = f"{timestamp}.json"
        file_path = os.path.join(self.base_directory, file_name)

        page_info = {url: {"forms": forms}}

        with open(file_path, "w") as file:
            json.dump(page_info, file, indent=4)


class FeedbackProvider:
    def __init__(self, page_analyzer: PageAnalyzer, page_info_saver: PageInfoSaver):
        self.page_analyzer = page_analyzer
        self.page_info_saver = page_info_saver

    async def get_page_loaded_feedback(self, url: str, page) -> str:
        print(f"url: {url}")
        forms = await self.page_analyzer.get_forms()
        print(f"forms: {forms}")
        # self.page_info_saver.save_page_info(url, forms)

        num_forms = len(forms)
        feedback = f"Website loaded successfully. It has {num_forms} form(s).\n\n"

        for form in forms:
            form_id = form["id"]
            feedback += f'Form with ID: "{form_id}" has the following inputs:\n'
            for input_data in form["inputs"]:
                input_str = ", ".join([f"{k}: {v}" for k, v in input_data.items()])
                feedback += f"- {input_str}\n"

            feedback += f'\nForm with ID: "{form_id}" has the following buttons:\n'
            for button_data in form["buttons"]:
                button_str = ", ".join([f"{k}: {v}" for k, v in button_data.items()])
                feedback += f"- {button_str}\n"

            feedback += "\n"  # Add a blank line between each form

        return feedback

    def get_page_loading_feedback(self, url: str) -> str:
        return f"Loading page: {url}"

    def get_form_details_feedback(self) -> str:
        input_fields = self.page_analyzer.get_input_fields()
        feedback = "Form details:\n"
        for field in input_fields:
            feedback += f"- Type: {field['type']}, Name: {field['name']}\n"
        return feedback

    def get_links_feedback(self) -> str:
        links = self.page_analyzer.get_links()
        feedback = "Links on the page:\n"
        for link in links:
            feedback += f"- URL: {link['url']}, Text: {link['text']}\n"
        return feedback

    def get_buttons_feedback(self) -> str:
        buttons = self.page_analyzer.get_buttons()
        feedback = "Buttons on the page:\n"
        for button in buttons:
            feedback += f"- {button}\n"
        return feedback

    def get_interaction_feedback(self, interaction_type: str, selector: str) -> str:
        return f"{interaction_type} interaction performed on element: {selector}"

    def get_error_feedback(self, error_message: str) -> str:
        return f"Error: {error_message}"
