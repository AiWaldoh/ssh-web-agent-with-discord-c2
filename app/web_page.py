from typing import Union, List, Optional
from playwright.async_api import (
    Page,
    ElementHandle,
    TimeoutError as PlaywrightTimeoutError,
)


class WebPage:
    def __init__(self, page: Page):
        self.page = page

    async def navigate(self, url: str, timeout: int = 30000):
        await self.page.goto(url, timeout=timeout)

    async def click(self, selector: str, timeout: int = 5000):
        try:
            await self.page.click(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(
                f"Timed out waiting for element '{selector}' to be clickable"
            )

    async def type(self, selector: str, text: str, delay: int = 100):
        await self.page.type(selector, text, delay=delay)

    async def wait_for_selector(self, selector: str, timeout: int = 5000):
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            raise TimeoutError(f"Timed out waiting for selector '{selector}'")

    async def wait_for_navigation(self, timeout: int = 30000):
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    def find_elements(self, selector: str) -> List[ElementHandle]:
        return self.page.query_selector_all(selector)

    async def get_current_url(self) -> str:
        return self.page.url

    async def go_back(self, timeout: int = 30000):
        await self.page.go_back(timeout=timeout)

    async def go_forward(self, timeout: int = 30000):
        await self.page.go_forward(timeout=timeout)

    async def refresh_page(self, timeout: int = 30000):
        await self.page.reload(timeout=timeout)

    async def is_element_visible(self, selector: str) -> bool:
        element = self.page.query_selector(selector)
        if element:
            return await element.is_visible()
        return False

    async def is_element_enabled(self, selector: str) -> bool:
        element = self.page.query_selector(selector)
        if element:
            return await element.is_enabled()
        return False

    async def get_input_value(self, selector: str) -> Optional[str]:
        element = self.page.query_selector(selector)
        if element:
            return await element.get_attribute("value")
        return None


class NavigationError(Exception):
    pass


class ElementNotFoundError(Exception):
    pass


class InteractionError(Exception):
    pass
