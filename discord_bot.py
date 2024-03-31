import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
from init_function_calls import (
    AITaskRegistry,
    ExecuteCommandTask,
    SearchGoogleTask,
    LoadWebsiteTask,
)
from init import Config, MessageStore, Message, Role, ToolLoader, JAVASCRIPT_SCR
from init_api import ChatAPIService

load_dotenv()


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
        print(message_soup)
        username_element = message_soup.find(
            "span", class_=lambda x: x and "username" in x
        )
        if username_element:
            return username_element.text.strip()
        return None

    def _extract_message_text(self, message_soup, has_mention):
        message_div = self._find_message_div(message_soup)
        if message_div:
            message_spans = self._find_message_spans(message_div)
            if has_mention:
                mention_span = self._find_mention_span(message_div)
                message_text = self._combine_message_text_with_mention(
                    mention_span, message_spans
                )
            else:
                message_text = self._combine_message_text(message_spans)
            return message_text.strip()
        else:
            return ""

    def _find_message_div(self, message_soup):
        return message_soup.select_one('div[class*="markup"]')

    def _find_message_spans(self, message_div):
        return message_div.find_all("span")

    def _find_mention_span(self, message_div):
        return message_div.select_one('span[class*="mention"]')

    def _combine_message_text_with_mention(self, mention_span, message_spans):
        if mention_span:
            return (
                mention_span.get_text()
                + " "
                + self._combine_message_text(
                    span for span in message_spans if span != mention_span
                )
            )
        else:
            return self._combine_message_text(message_spans)

    def _combine_message_text(self, message_spans):
        return " ".join(span.get_text() for span in message_spans)

    def _parse_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)
        return None

    def _is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


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
        self.browser = await playwright.chromium.launch(headless=True)

    async def _login_to_discord(self):
        session_file = os.path.join("secret", self.config.SESSION_FILE)

        if not os.path.exists("secret"):
            os.makedirs("secret")

        if os.path.exists(session_file):
            # If the session file exists, assume it's a valid session
            self.context = await self.browser.new_context(storage_state=session_file)
            self.page = await self.context.new_page()
        else:
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            await self.page.goto("https://discord.com/login")
            await self._submit_login_form()
            await self._update_settings()
            await self.context.storage_state(path=session_file)

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
        message = await asyncio.to_thread(
            self.message_parser.parse_message, raw_message
        )
        if message:
            self.message_store.add_message(
                Message(role=Role.USER, content=message["message_text"])
            )
            api_response = self.api_client.execute_api_call(
                self.message_store.get_messages(),
                self.tool_loader.tools,
                config=self.config,
            )
            self.message_store = self.response_processor.process_api_response(
                api_response, self.message_store
            )
            self.message_store.truncate_history(max_history=5)
            processed_responses = self.response_processor.process(api_response)
            for response in processed_responses:
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
        self.tool_loader = ToolLoader()
        self.message_store = MessageStore(
            initial_system_message="You are a helpful assistant."
        )

    async def start(self):
        self.load_tools("tools.yaml")
        await self.discord_client.start()

    def load_tools(self, file_path):
        self.tool_loader.load_tools_from_yaml(file_path)
        for tool_data in self.tool_loader.tools:
            tool_name = tool_data["function"]["name"]
            tool_class_name = (
                "".join(word.capitalize() for word in tool_name.split("_")) + "Task"
            )
            tool_class = globals()[tool_class_name]
            AITaskRegistry.register(tool_name, tool_class())


if __name__ == "__main__":
    config = Config()
    bot = DiscordBot(config)
    asyncio.run(bot.start())
