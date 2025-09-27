import os
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright
from typing import Any, List, Optional, Dict
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, ElementHandle
import json
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict


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


class PageAnalyzer:
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def get_forms(self) -> List[Dict[str, Any]]:
        forms = []
        elements = self.browser.find_elements("form")
        for element in elements:
            form_data = {
                "id": element.get_attribute("id"),
                "class": element.get_attribute("class"),
                "action": element.get_attribute("action"),
                "method": element.get_attribute("method"),
                "inputs": [],
                "buttons": [],
            }

            input_elements = element.query_selector_all("input, textarea, select")
            for input_element in input_elements:
                input_data = {
                    "type": input_element.get_attribute("type"),
                    "name": input_element.get_attribute("name"),
                    "value": input_element.get_attribute("value"),
                    "id": input_element.get_attribute("id"),
                    "class": input_element.get_attribute("class"),
                }
                form_data["inputs"].append(input_data)

            button_elements = element.query_selector_all("button")
            for button_element in button_elements:
                button_data = {
                    "type": button_element.get_attribute("type"),
                    "text": button_element.text_content(),
                    "id": button_element.get_attribute("id"),
                    "class": button_element.get_attribute("class"),
                }
                form_data["buttons"].append(button_data)

            forms.append(form_data)

        return forms

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

    def get_page_loaded_feedback(self, url: str) -> str:
        forms = self.page_analyzer.get_forms()
        self.page_info_saver.save_page_info(url, forms)

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


class GoToPageTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper, feedback_provider):
        self.browser = browser
        self.feedback_provider = feedback_provider

    def execute(self, arguments):
        url = arguments.get("url")
        if url:
            self.browser.navigate_to(url)
            self.browser.wait_for_navigation()
            return self.feedback_provider.get_page_loaded_feedback(url, self.browser.page)
        else:
            return "No URL provided."


class TakeScreenshotTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        # Create a folder to store the screenshots (if it doesn't exist)
        folder_name = "screenshots"
        os.makedirs(folder_name, exist_ok=True)

        # Generate a timestamp-based file name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{folder_name}/screenshot_{timestamp}.png"

        # Take the screenshot and save it with the generated file name
        self.browser.take_screenshot(file_name)

        print(f"Screenshot captured and saved as: {file_name}")
        return file_name


class ClickElementTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        selector = arguments.get("selector")
        if selector:
            # self.browser.click_element(selector)
            # self.browser.wait_for_navigation()
            self.browser.click_and_wait_for_network_activity(selector)
            return f"Click interaction performed on element: {selector}"

        else:
            return "No selector provided."


class FormDetailsTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper, feedback_provider):
        self.browser = browser
        self.feedback_provider = feedback_provider

    def execute(self, arguments):
        return self.feedback_provider.get_form_details_feedback()


class LinksTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper, feedback_provider):
        self.browser = browser
        self.feedback_provider = feedback_provider

    def execute(self, arguments):
        return self.feedback_provider.get_links_feedback()


class ButtonsTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper, feedback_provider):
        self.browser = browser
        self.feedback_provider = feedback_provider

    def execute(self, arguments):
        return self.feedback_provider.get_buttons_feedback()


class SubmitFormTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        selector = arguments.get("selector")
        if selector:
            self.browser.click_element(selector)
            return f"Form submitted successfully using selector: {selector}"
        else:
            return "No selector provided for form submission."


class GetPageSourceTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        page_source = self.browser.page.content()
        return f"Page source:\n{page_source}"


class GetCurrentUrlTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        current_url = self.browser.get_current_url()
        return f"Current URL: {current_url}"


class FillInputTask(AITaskCommand):
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

    def execute(self, arguments):
        selector = arguments.get("selector")
        value = arguments.get("value")
        if selector and value:
            self.browser.fill_input(selector, value)
            return f"Fill interaction performed on element: {selector}"
        else:
            return "Selector or value not provided."
