from playwright.sync_api import sync_playwright
from api import HttpClient, ChatAPI
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import playwright
from playwright.async_api import async_playwright
import asyncio

load_dotenv()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
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


class DiscordMonitor:
    def __init__(self):
        self.browser = None
        self.page = None
        self.message_parser = MessageParser()
        self.api_handler = ChatAPIHandler(OPENROUTER_API_KEY)

    async def _send_discord_message(self, message):

        if message:

            # await self.page.evaluate("document.querySelector('div[role=\"textbox\"]')")
            await self.page.wait_for_selector('div[role="textbox"]')
            await self.page.type('div[role="textbox"]', message)
            await self.page.keyboard.press("Enter")
        else:
            print("Empty message. Skipping sending to Discord.")

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            # await self._send_discord_message("sup")
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
        if self.message_parser.is_valid_message(msg):

            message = await asyncio.to_thread(
                self.message_parser.on_message_received, msg
            )

            if message:
                print(f"Sending message to Discord: {message}")
                await self._send_discord_message(message)


class MessageParser:
    def __init__(self):
        self.api_handler = ChatAPIHandler(OPENROUTER_API_KEY)

    def on_message_received(self, msg):
        soup = BeautifulSoup(msg, "html.parser")

        parsed_data = self.parse_message(soup)
        if not parsed_data["has_mention"]:
            return
        print(parsed_data)
        if parsed_data:
            return self.api_handler.on_message_parsed(parsed_data)

    def extract_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)

        return None

    def is_valid_message(self, msg):
        return msg.strip().startswith('"<li')

    def parse_message(self, soup):

        user_id, username, has_mention, message_text = self.get_message_attributes(soup)
        return {
            "user_id": user_id,
            "username": username,
            "has_mention": has_mention,
            "message_text": message_text.strip(),
        }

    def get_message_attributes(self, soup):
        user_id = self.get_user_id(soup)
        has_mention = self.is_mention(soup)
        username = self.get_username(soup)
        message_text = self.get_message(soup, has_mention)
        return user_id, username, has_mention, message_text

    def get_user_id(self, soup):
        img_src = soup.find("img")["src"] if soup.find("img") else None
        return self.extract_user_id(img_src)

    def is_mention(self, soup):
        mention = soup.select_one('span[class*="mention"]')
        return mention and "@Wendah" in mention.text

    def get_username(self, soup):
        username_element = soup.find(
            "span", class_=lambda x: x and "username_d30d99" in x
        )
        if username_element:
            return username_element.text.strip()
        return None

    def get_message(self, soup, has_mention):
        message_text = ""
        if has_mention:
            message_spans = soup.select_one(
                'span[class*="mention"]'
            ).find_next_siblings("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        else:
            message_spans = soup.find_all("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        return message_text.strip()


class ChatAPIHandler:

    def __init__(self, api_key):
        self.http_client = HttpClient(OPENROUTER_API_KEY)
        self.chat_api = ChatAPI(self.http_client)
        self.chat_api.set_system_message(
            "You are a quirky cybersecurity professional who always answers in a humorous way. You really like Justin Trudeau."
        )

    def on_message_parsed(self, data):

        if self.is_admin(data["user_id"]):
            return self.handle_admin_message(data)
        else:
            return self.handle_regular_message(data)

    def is_admin(self, user_id):
        return user_id == ADMIN_USER_ID

    def handle_admin_message(self, data):
        # Implement admin-specific message handling logic here
        response = self.send_message(data["message_text"])
        # print(f"Admin message response: {response}")
        return response

    def handle_regular_message(self, data):
        # Implement regular message handling logic here
        response = self.send_message(data["message_text"])
        # print(f"Regular message response: {response}")
        return response

    def send_message(self, message):
        try:
            response = self.chat_api.send_message(message)
            if response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                print("Unexpected API response format.")
                return None
        except Exception as e:
            # print(f"Error occurred during API call: {str(e)}")
            print(f"Error occurred during API call")
            return None


if __name__ == "__main__":
    discord_monitor = DiscordMonitor()
    asyncio.run(discord_monitor.run())
