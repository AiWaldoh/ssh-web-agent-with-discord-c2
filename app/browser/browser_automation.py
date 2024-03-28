from abc import ABC, abstractmethod
from playwright.async_api import async_playwright


class BrowserAutomation(ABC):
    def __init__(self):
        self.browser = None
        self.page = None

    @abstractmethod
    async def start_app(self, playwright):
        pass

    @abstractmethod
    async def keep_alive(self):
        pass

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            await self.keep_alive()
