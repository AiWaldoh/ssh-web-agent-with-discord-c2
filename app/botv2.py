from playwright.sync_api import sync_playwright
from api2 import HttpClient, ChatAPI
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import playwright
from playwright.async_api import async_playwright
import asyncio

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
API_URL = os.getenv("API_URL")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")
JAVASCRIPT_SCR = """
                var target = document.querySelector('main[class^="chatContent"]');
                var observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList') {
                            mutation.addedNodes.forEach(function(node) {
                                window.onNewMessage(JSON.stringify(node.outerHTML));
                            });
                        }
                    });
                });
                var config = { childList: true, subtree: true };
                observer.observe(target, config);
            """


class MessageParser:
    def __init__(self, api_handler):
        self.api_handler = api_handler

    def on_message_received(self, message_html):
        if not self._is_valid_message(message_html):
            return

        message_soup = BeautifulSoup(message_html, "html.parser")
        message_data = self._parse_message(message_soup)

        if message_data["has_mention"]:
            print(message_data)
            return self.api_handler.handle_message(message_data)

    def _parse_message(self, message_soup):
        user_id = self._get_user_id(message_soup)
        has_mention = self._is_mention(message_soup)
        username = self._get_username(message_soup)
        message_text = self._get_message(message_soup, has_mention)

        return {
            "user_id": user_id,
            "username": username,
            "has_mention": has_mention,
            "message_text": message_text.strip(),
        }

    def _get_user_id(self, message_soup):
        img_src = message_soup.find("img")["src"] if message_soup.find("img") else None
        return self._extract_user_id(img_src)

    def _is_mention(self, message_soup):
        mention = message_soup.select_one('span[class*="mention"]')
        return mention and BOT_NAME in mention.text

    def _get_username(self, message_soup):
        username_element = message_soup.find(
            "span", class_=lambda x: x and "username_d30d99" in x
        )
        if username_element:
            return username_element.text.strip()
        return None

    def _get_message(self, message_soup, has_mention):
        message_text = ""
        if has_mention:
            message_spans = message_soup.select_one(
                'span[class*="mention"]'
            ).find_next_siblings("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        else:
            message_spans = message_soup.find_all("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        return message_text.strip()

    def _extract_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)
        return None

    def _is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


class DiscordMonitor:
    def __init__(self, message_parser, api_handler):
        self.browser = None
        self.page = None
        self.message_parser = message_parser
        self.api_handler = api_handler

    async def _send_discord_message(self, message):
        if message:
            await self.page.wait_for_selector('div[role="textbox"]')
            await self.page.type('div[role="textbox"]', message)
            await self.page.keyboard.press("Enter")
        else:
            print("Empty message. Skipping sending to Discord.")

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            await self.keep_alive()

    async def start_app(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        await self.login_to_discord()

        print(f"Loading {os.getenv('DISCORD_CHANNEL_URL')}")
        await self.page.goto(os.getenv("DISCORD_CHANNEL_URL"))
        await self.page.wait_for_load_state("networkidle")
        await self.page.expose_function("onNewMessage", self.on_new_message)
        await self.page.evaluate(JAVASCRIPT_SCR)

        print("Listening for new messages...")

    async def keep_alive(self):
        try:
            while True:
                await self.page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("Script terminated by user.")

        await self.browser.close()

    async def login_to_discord(self):
        if os.path.exists("secret/" + SESSION_FILE):
            self.context = await self.browser.new_context(
                storage_state="secret/" + SESSION_FILE
            )
        else:
            self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def on_new_message(self, msg):
        if self.message_parser._is_valid_message(msg):
            message = await asyncio.to_thread(
                self.message_parser.on_message_received, msg
            )

            if message:
                print(f"Sending message to Discord: {message}")
                await self._send_discord_message(message)


class ChatAPIHandler:
    def __init__(self, chat_api):
        self.chat_api: ChatAPI = chat_api
        self.chat_api.set_system_message(SYSTEM_MESSAGE)

    def handle_message(self, message_data):
        if self._is_admin(message_data["user_id"]):
            return self.send_message(message_data["message_text"])
        else:
            return self.send_message(message_data["message_text"])

    def _is_admin(self, user_id):
        return user_id == ADMIN_USER_ID

    def send_message(self, message):
        try:
            self.chat_api.set_temperature(1.0)
            response = self.chat_api.send_message(message)
            if response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                print("Unexpected API response format.")
                return None
        except Exception as e:
            print(f"Error occurred during API call")
            return None


if __name__ == "__main__":

    http_client = HttpClient(OPENROUTER_API_KEY)
    chat_api = ChatAPI(http_client, MODEL_NAME, API_URL)
    api_handler = ChatAPIHandler(chat_api)
    message_parser = MessageParser(api_handler)
    discord_monitor = DiscordMonitor(message_parser, api_handler)
    asyncio.run(discord_monitor.run())
