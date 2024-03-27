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
        self.api_handler = APIHandler(OPENROUTER_API_KEY)

    async def _send_discord_message(self, message):
        print("Entering _send_discord_message")
        print("Message:", message)
        if message:
            print("Current page URL:", self.page.url)

            try:
                # Check if the page is responsive and the necessary elements are present
                await self.page.evaluate(
                    "document.querySelector('div[role=\"textbox\"]')"
                )
            except playwright._impl._api_types.Error as e:
                print(f"Page is not responsive or in the expected state. Error: {e}")
                print("Recreating the browser context and page.")
                await self.context.close()
                await self.page.close()
                await self.login_to_discord()
                await self.page.goto(os.getenv("DISCORD_CHANNEL_URL"))
                await self.page.wait_for_load_state("networkidle")

            print("Page HTML:")
            print(await self.page.content())

            print("Waiting for selector")
            await self.page.wait_for_selector('div[role="textbox"]')
            print("Typing message")
            await self.page.type('div[role="textbox"]', message)
            await self.page.keyboard.press("Enter")
            print("Message sent")
        else:
            print("Empty message. Skipping sending to Discord.")
        print("Exiting _send_discord_message")

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            await self._send_discord_message("sup")
            await self.keep_alive()

    async def start_app(self, playwright):
        self.browser = await playwright.chromium.launch(headless=False)
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
        print("Received new message")
        api_response = await asyncio.to_thread(
            self.message_parser.on_message_received, msg
        )

        if api_response:
            print("API response:", api_response)
            await self._send_discord_message(api_response)
        else:
            print("No API response received.")


class MessageParser:
    def __init__(self):
        self.api_handler = APIHandler(OPENROUTER_API_KEY)

    def on_message_received(self, msg):
        parsed_data = self.parse_message(msg)
        if parsed_data:
            return self.api_handler.on_message_parsed(parsed_data)

    def extract_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)

        return None

    def parse_message(self, msg):
        msg = msg.strip()
        if msg.startswith('"<li'):
            soup = BeautifulSoup(msg, "html.parser")

            user_id, has_mention, message_text = self.get_message_attributes(soup)

            return {
                "user_id": user_id,
                "has_mention": has_mention,
                "message_text": message_text.strip(),
            }
        else:
            return None

    def get_message_attributes(self, soup):
        img_src = soup.find("img")["src"] if soup.find("img") else None
        user_id = self.extract_user_id(img_src)
        mention = soup.select_one('span[class*="mention"]')

        has_mention = mention and "@Wendah" in mention.text

        message_text = ""
        if has_mention:
            message_spans = mention.find_next_siblings("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        else:
            message_spans = soup.find_all("span")
            message_text = " ".join(span.get_text() for span in message_spans)
        return user_id, has_mention, message_text


class APIHandler:
    ADMIN_USER_ID = "1008186485901623386"

    def __init__(self, api_key):
        self.http_client = HttpClient(OPENROUTER_API_KEY)
        self.chat_api = ChatAPI(self.http_client)
        self.chat_api.set_system_message(
            "You are a quirky cybersecurity professional who always answers in a humorous way. You really like Justin Trudeau."
        )

    def on_message_parsed(self, data):
        if not data["has_mention"]:
            return

        if self.is_admin(data["user_id"]):
            return self.handle_admin_message(data)
        else:
            return self.handle_regular_message(data)

    def is_admin(self, user_id):
        return user_id == self.ADMIN_USER_ID

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
            print(f"Error occurred during API call: {str(e)}")
            return None


if __name__ == "__main__":
    discord_monitor = DiscordMonitor()
    asyncio.run(discord_monitor.run())
