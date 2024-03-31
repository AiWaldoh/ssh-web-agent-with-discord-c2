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
from init_api import ChatAPIService, ResponseProcessor
import json

load_dotenv()


class MessageExtractor:
    def extract_message_data(self, message_soup):
        user_id = self._extract_user_id(message_soup)
        has_mention = self._contains_mention(message_soup)
        username = self._extract_username(message_soup)
        message_text = self._extract_message_text(message_soup, has_mention)
        print(f"return data: {user_id}, {username}, {has_mention}, {message_text}")
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


class MessageValidator:
    def is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


class MessageParser:
    def __init__(
        self, message_extractor: MessageExtractor, message_validator: MessageValidator
    ):
        self.message_extractor: MessageExtractor = message_extractor
        self.message_validator: MessageValidator = message_validator

    def parse_message(self, message_html):
        if not self.message_validator.is_valid_message(message_html):
            return None

        message_soup = BeautifulSoup(message_html, "html.parser")
        return self.message_extractor.extract_message_data(message_soup)


class DiscordBrowser:
    def __init__(self, config: Config):
        self.config = config
        self.browser = None
        self.page = None

    async def launch(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)

    async def login(self):
        session_file = os.path.join("secret", self.config.SESSION_FILE)

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

    async def close(self):
        await self.browser.close()


class DiscordClient:
    def __init__(
        self,
        config: Config,
        message_parser: MessageParser,
        api_client: ChatAPIService,
        response_processor: ResponseProcessor,
        tool_loader: ToolLoader,
    ):
        self.config: Config = config
        self.message_parser: MessageParser = message_parser
        self.api_client: ChatAPIService = api_client
        self.response_processor: ResponseProcessor = response_processor
        self.browser: DiscordBrowser = DiscordBrowser(config)
        self.tool_loader: ToolLoader = tool_loader
        self.message_store = MessageStore(
            initial_system_message="You are a helpful assistant."
        )

    async def start(self):
        async with async_playwright() as playwright:
            await self.browser.launch(playwright)
            await self.browser.login()
            await self.browser.load_channel()
            await self.browser.expose_on_message_function(self._on_message)
            await self._keep_alive()

    async def _keep_alive(self):
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Script terminated by user.")
        finally:
            await self.browser.close()

    async def _on_message(self, raw_message):
        message = await asyncio.to_thread(
            self.message_parser.parse_message, raw_message
        )
        if message:
            await self.process_message(message)

    async def _post_process_response(self, response):
        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice["message"]

            # this is insecure. can make api return the word "tool_calls" and it will be executed
            if "tool_calls" in message:
                print(f"message: {message}")
                # Handle tool calls
                tool_calls = message["tool_calls"]
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    print(f"Tool call: {tool_name}")
                    if tool_name == "execute_command":
                        print("Executing command...")

                    else:
                        print("Unsupported tool call.")
            else:
                # Handle non-tool call
                print("Assistant:", message["content"])
                return message["content"]
                # message_history.append(message)
        else:
            print("No response or no choices in the response.")
            return None

    async def process_message(self, message):
        print(f"message: {message}")
        # if message["user_id"] != self.config.BOT_USER_ID:
        #     return

        if message["has_mention"]:
            print(f"has_mention: {message['has_mention']}")

        if message["user_id"] == self.config.ADMIN_USER_ID:
            print("Admin message")
            message_text = message["message_text"].replace("@Wendah", "").strip()
            print(f"message_text: {message_text}")
            try:

                self.message_store.add_message(
                    Message(role=Role.USER, content=message_text)
                )
            except Exception as e:
                print(f"Error adding message: {e}")

            api_response = self.api_client.execute_api_call(
                self.message_store.get_messages(),
                self.tool_loader.tools,
                config=self.config,
            )
            print("-------------------- API RESPONSE -----------------------")
            print(api_response)
            print("-------------------- END API RESPONSE -------------------")
            # self.message_store = self.response_processor.process(api_response)
            processed_response = await self._post_process_response(api_response)
            print(f"processed_response: {processed_response}")
            if processed_response:
                print("sending response to discord")
                await self._send_response(processed_response)
            else:
                print("No response to send.")
        else:
            print("User message")
            # Handle different API calls based on the message content
            if message["message_text"].startswith("!command"):
                # Call a specific API for handling commands
                command = message["message_text"][len("!command") :].strip()
                api_response = self.api_client.execute_command_api_call(command)
                await self._send_response(api_response["content"])
            elif message["message_text"].startswith("!search"):
                # Call a specific API for handling searches
                query = message["message_text"][len("!search") :].strip()
                api_response = self.api_client.execute_search_api_call(query)
                await self._send_response(api_response["content"])
            else:
                print("Unknown message type")
                # Handle regular messages without mentions
                self.message_store.add_message(
                    Message(role=Role.USER, content=message["message_text"])
                )
                api_response = self.api_client.execute_api_call(
                    self.message_store.get_messages(),
                    self.tool_loader.tools,
                    config=self.config,
                )
                print(api_response)
                self.message_store = self.response_processor.process_api_response(
                    api_response, self.message_store
                )
                await self._send_response(api_response["content"])

    async def _send_response(self, response_text):
        # for chunk in self._split_response(response_text):
        try:

            await self.browser.page.type("div[role='textbox']", response_text)
            await self.browser.page.press("div[role='textbox']", "Enter")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error sending response: {e}")

    def _split_response(self, response_text, max_length=1500):
        words = response_text.split()
        chunks = []
        current_chunk = []

        for word in words:
            if len(" ".join(current_chunk + [word])) <= max_length:
                current_chunk.append(word)
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


class DiscordBot:
    def __init__(self, config: Config):
        self.config = config
        message_extractor = MessageExtractor()
        message_validator = MessageValidator()
        self.message_parser = MessageParser(message_extractor, message_validator)
        self.api_client = ChatAPIService(config.OPENROUTER_API_KEY, config.MODEL_NAME)
        self.response_processor = ResponseProcessor()
        self.tool_loader = ToolLoader()
        self.discord_client = DiscordClient(
            config,
            self.message_parser,
            self.api_client,
            self.response_processor,
            self.tool_loader,
        )

    async def start(self):
        self.load_tools("tools.yaml")
        await self.discord_client.start()

    def load_tools(self, file_path):
        self.tool_loader.load_tools_from_yaml(file_path)
        self.register_tools()

    def register_tools(self):
        for tool_data in self.tool_loader.tools:
            tool_name = tool_data["function"]["name"]
            tool_class = self.get_tool_class(tool_name)
            AITaskRegistry.register(tool_name, tool_class())

    def get_tool_class(self, tool_name):
        tool_class_name = (
            "".join(word.capitalize() for word in tool_name.split("_")) + "Task"
        )
        return globals()[tool_class_name]


if __name__ == "__main__":
    config = Config()
    bot = DiscordBot(config)
    asyncio.run(bot.start())
