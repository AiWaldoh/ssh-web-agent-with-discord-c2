import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests

load_dotenv()

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


class Config:
    BOT_NAME = os.getenv("BOT_NAME")
    MODEL_NAME = os.getenv("MODEL_NAME")
    API_URL = os.getenv("API_URL")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
    SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
    SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")
    DISCORD_CHANNEL_URL = os.getenv("DISCORD_CHANNEL_URL")
    BASE_URL = os.getenv("BASE_URL")
    SSH_HOST = os.getenv("SSH_HOST")
    SSH_PORT = int(os.getenv("SSH_PORT"))
    SSH_USERNAME = os.getenv("SSH_USERNAME")
    SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
    USERNAME = os.getenv("DISCORD_EMAIL")
    PASSWORD = os.getenv("DISCORD_PASSWORD")


class Message:
    def __init__(self, username, user_id, profile_url, content):
        self.username = username
        self.user_id = user_id
        self.profile_url = profile_url
        self.content = content


class HttpClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, url, data):
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            print(f"Error occurred during API call: {str(e)}")
            return None


class ChatAPIService:
    def __init__(self, api_key, model_name="gpt-3.5-turbo", temperature=1.0):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.http_client = HttpClient(api_key)

    def execute_api_call(self, messages, tools, config=None):
        url = "https://openrouter.ai/api/v1/chat/completions"
        data = {
            "messages": [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ],
            "model": self.model_name,
            "temperature": self.temperature,
            "tools": tools,
        }
        if config:
            data.update(config)

        response = self.http_client.post(url, data)
        return response


class MessageParser:
    def __init__(self):
        self.api_handler = None

    def parse_message(self, message_html):
        if not self._is_valid_message(message_html):
            return

        message_soup = BeautifulSoup(message_html, "html.parser")
        message_data = self._extract_message_data(message_soup)

        if message_data["has_mention"]:
            print(f"has_mention: {message_data['has_mention']}")
            return self.api_handler.handle_message(message_data)

    def _extract_message_data(self, message_soup):
        user_id = self._extract_user_id(message_soup)
        has_mention = self._contains_mention(message_soup)
        username = self._extract_username(message_soup)
        message_text = self._extract_message_text(message_soup, has_mention)

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
        return mention and mention.text.startswith("@Wendah")

    def _extract_username(self, message_soup):
        username_element = message_soup.find(
            "span", class_=lambda x: x and "username_d30d99" in x
        )
        if username_element:
            return username_element.text.strip()
        return None

    def _extract_message_text(self, message_soup, has_mention):
        message_div = message_soup.select_one('div[class*="markup"]')
        if message_div:
            message_spans = message_div.find_all("span")
            if has_mention:
                mention_span = message_div.select_one('span[class*="mention"]')
                if mention_span:
                    message_text = (
                        mention_span.get_text()
                        + " "
                        + " ".join(
                            span.get_text()
                            for span in message_spans
                            if span != mention_span
                        )
                    )
                else:
                    message_text = " ".join(span.get_text() for span in message_spans)
            else:
                message_text = " ".join(span.get_text() for span in message_spans)
            return message_text.strip()
        else:
            return ""

    def _parse_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)
        return None

    def _is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


class ResponseProcessor:
    def process(self, api_response, max_length=1900):
        response_text = api_response["response"]
        return [
            response_text[i : i + max_length]
            for i in range(0, len(response_text), max_length)
        ]


import asyncio
from playwright.async_api import async_playwright


class DiscordClient:
    def __init__(self, config, message_parser, api_client, response_processor):
        self.config = config
        self.message_parser = message_parser
        self.api_client = api_client
        self.response_processor = response_processor
        self.browser = None
        self.page = None

    async def start(self):
        async with async_playwright() as playwright:
            await self._launch_browser(playwright)
            await self._login_to_discord()
            await self._load_discord_channel()
            await self._expose_on_message_function()
            await self._keep_alive()

    async def _launch_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=False)

    async def _login_to_discord(self):
        session_file = os.path.join("secret", self.config.SESSION_FILE)

        if not os.path.exists("secret"):
            os.makedirs("secret")

        if os.path.exists(session_file):
            # If the session file exists, assume it's a valid session
            self.context = await self.browser.new_context(storage_state=session_file)
            self.page = await self.context.new_page()
        else:
            # If the session file doesn't exist, create a new session and log in
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            # Navigate to the Discord login page
            await self.page.goto("https://discord.com/login")

            # Fill in the login form and submit
            await self.page.fill('input[name="email"]', self.config.USERNAME)
            await self.page.fill('input[name="password"]', self.config.PASSWORD)
            await self.page.click('button[type="submit"]')

            await self.page.wait_for_selector(".flex_f18b02")
            await self.page.click('button[aria-label="User Settings"]')
            await self.page.click('div[aria-label="Appearance"]')
            await self.page.click('label:has-text("Show avatars in Compact mode")')
            await self.page.click('div[aria-label="Close"]')

            # Save the session to the storage state
            await self.context.storage_state(path=session_file)

    async def _load_discord_channel(self):
        print(f"Loading {self.config.DISCORD_CHANNEL_URL}")
        await self.page.goto(self.config.DISCORD_CHANNEL_URL)
        await self.page.wait_for_selector("div[role='textbox']")
        await asyncio.sleep(5)

    async def _expose_on_message_function(self):
        await self.page.expose_function("onNewMessage", self._on_message)
        await self.page.evaluate(JAVASCRIPT_SCR)
        print("Listening for new messages...")

    async def _keep_alive(self):
        try:
            while True:
                await self.page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("Script terminated by user.")
        finally:
            await self.browser.close()

    async def _on_message(self, raw_message):
        print(f"Received message: {raw_message}")
        message = await asyncio.to_thread(
            self.message_parser.parse_message, raw_message
        )
        print(f"Parsed message: {message}")
        if message:
            api_response = self.api_client.execute_api_call([message], [])
            print(f"API response: {api_response}")
            processed_responses = self.response_processor.process(api_response)
            print(f"Processed responses: {processed_responses}")
            for response in processed_responses:
                print(f"Sending response: {response}")
                await self.send_message(response)

    async def send_message(self, message):
        print(f"typing message")
        await self.page.type("div[role='textbox']", message)
        await self.page.press("div[role='textbox']", "Enter")


class DiscordBot:
    def __init__(self, config: Config):
        self.config = config
        self.message_parser = MessageParser()
        self.api_client = ChatAPIService(config.OPENROUTER_API_KEY, config.MODEL_NAME)
        self.response_processor = ResponseProcessor()
        self.discord_client = DiscordClient(
            config, self.message_parser, self.api_client, self.response_processor
        )

    async def start(self):
        await self.discord_client.start()


if __name__ == "__main__":
    config = Config()
    bot = DiscordBot(config)
    asyncio.run(bot.start())
