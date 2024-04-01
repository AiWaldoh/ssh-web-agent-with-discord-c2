from playwright.sync_api import sync_playwright
from typing import List, Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, ElementHandle


class PlaywrightBrowserWrapper:
    def __init__(self, browser_type="chromium", headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright[browser_type].launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

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


from typing import List, Dict


class PageAnalyzer:
    def __init__(self, browser: PlaywrightBrowserWrapper):
        self.browser = browser

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


def playwright_browser_wrapper(
    PlaywrightBrowserWrapper, NavigationError, ElementNotFoundError, InteractionError
):
    browser = PlaywrightBrowserWrapper()

    try:
        # Navigate to Google
        browser.navigate_to("https://www.google.com")

        # Fill the search input with "Playwright"
        browser.fill_input("#APjFqb", "Playwright")

        # Click the search button
        browser.click_element(".gNO89b")

        # Wait for the search results page to load
        browser.wait_for_navigation()

        # Wait for the search results to be visible
        browser.wait_for_selector("#search")

        # Get the text of the search results
        text = browser.get_text("#search")
        print("Search Results:")
        print(text)

        # Take a screenshot of the search results page
        browser.take_screenshot("search_results.png")

        # Get the current URL
        current_url = browser.get_current_url()
        print("Current URL:", current_url)

        # Go back to the previous page
        browser.go_back()

        # Wait for the previous page to load
        browser.wait_for_navigation()

        # Refresh the page
        browser.refresh_page()

        # Check if an element is visible
        is_logo_visible = browser.is_element_visible("img[alt='Google']")
        print("Is Google logo visible:", is_logo_visible)

        # Check if an element is enabled
        is_search_enabled = browser.is_element_enabled(".gNO89b")
        print("Is search button enabled:", is_search_enabled)

        # Get the value of an input field
        search_value = browser.get_input_value("#APjFqb")
        print("Search input value:", search_value)

    except (NavigationError, ElementNotFoundError, InteractionError) as e:
        print("An error occurred:", str(e))

    finally:
        # Close the browser
        browser.close()


def test_page_analyzer(PlaywrightBrowserWrapper, PageAnalyzer):
    browser = PlaywrightBrowserWrapper()
    browser.navigate_to(
        "https://python.langchain.com/docs/integrations/text_embedding/cloudflare_workersai"
    )

    analyzer = PageAnalyzer(browser)

    title = analyzer.get_page_title()
    print("Page Title:", title)

    headings = analyzer.get_headings()
    print("Headings:")
    for heading in headings:
        print(f"- {heading['tag']}: {heading['text']}")

    paragraphs = analyzer.get_paragraphs()
    print("Paragraphs:")
    for paragraph in paragraphs:
        print(f"- {paragraph}")

    links = analyzer.get_links()
    print("Links:")
    for link in links:
        print(f"- URL: {link['url']}, Text: {link['text']}")

    input_fields = analyzer.get_input_fields()
    print("Input Fields:")
    for input_field in input_fields:
        print(f"- Type: {input_field['type']}, Name: {input_field['name']}")

    buttons = analyzer.get_buttons()
    print("Buttons:")
    for button in buttons:
        print(f"- {button}")

    meta_description = analyzer.get_meta_description()
    print("Meta Description:", meta_description)

    meta_keywords = analyzer.get_meta_keywords()
    print("Meta Keywords:", meta_keywords)

    page_text = analyzer.get_page_text()
    print("Page Text:")
    print(page_text)

    images = analyzer.get_images()
    print("Images:")
    for image in images:
        print(f"- {image}")

    css_classes = analyzer.get_css_classes()
    print("CSS Classes:", css_classes)

    css_ids = analyzer.get_css_ids()
    print("CSS IDs:", css_ids)

    javascript_events = analyzer.get_javascript_events()
    print("JavaScript Events:", javascript_events)

    browser.close()


if __name__ == "__main__":

    testing_playwright_browser_wrapper = False
    if testing_playwright_browser_wrapper:

        playwright_browser_wrapper(
            PlaywrightBrowserWrapper,
            NavigationError,
            ElementNotFoundError,
            InteractionError,
        )

    testing_page_analyzer_wrapper = True
    if testing_page_analyzer_wrapper:
        test_page_analyzer(PlaywrightBrowserWrapper, PageAnalyzer)
