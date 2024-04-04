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
import json
from dataclasses import dataclass

load_dotenv()


@dataclass
class ProcessedResponse:
    chat_memory_response: str = ""
    chat_response: str = ""


class MessageExtractor:
    def extract_message_data(self, message_soup):
        user_id = self._extract_user_id(message_soup)
        has_mention = self._contains_mention(message_soup)
        username = self._extract_username(message_soup)
        message_text = self._extract_message_text(message_soup, has_mention)
        # print(f"return data: {user_id}, {username}, {has_mention}, {message_text}")
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
        return mention and mention.text.startswith(Config.BOT_NAME)

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


class DiscordBrowser:
    def __init__(self, config: Config):
        self.config = config
        self.browser = None
        self.page = None

    async def launch(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)

    async def login(self):
        session_file = os.path.join("secret", Config.SESSION_FILE)

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


class MessageValidator:
    def is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


class MessageParser:
    def __init__(
        self, message_extractor: MessageExtractor, message_validator: MessageValidator
    ):
        self.message_extractor = message_extractor
        self.message_validator = message_validator

    def parse_message(self, message_html):
        if not self.message_validator.is_valid_message(message_html):
            return None

        message_soup = BeautifulSoup(message_html, "html.parser")
        return self.message_extractor.extract_message_data(message_soup)


class ResponseProcessor:

    async def process(self, api_response):
        tool_calls = self._extract_tool_calls(api_response)

        if tool_calls:
            return await self._handle_tool_calls(tool_calls)
        else:
            return await self._process_basic_response(api_response)

    # related to parsing google search results
    def handle_search_result(self, search_result):
        result_message = ""
        for item in search_result:
            description = f"```{item.description}```"
            result_message += f" <{item.url}>\n{description}\n"

        return result_message

    def _handle_execute_command_result(self, result):
        # return result wrapped in triple backticks
        return f"```{result}```"

    def _extract_tool_calls(self, response):
        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice["message"]
            if "tool_calls" in message:
                return message["tool_calls"]
        return None

    async def _handle_tool_calls(self, tool_calls):
        response = ProcessedResponse()
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            command = AITaskRegistry.get_command(tool_name)
            if command:
                output = command.execute(tool_args)

                if tool_name == "search_google":
                    output = self.handle_search_result(output)
                    response.chat_memory_response = output
                    response.chat_response = output
                    return response
                elif tool_name == "load_website":

                    response.chat_memory_response = "OK"
                    response.chat_response = output
                    return response
                elif tool_name == "execute_command":
                    output = self._handle_execute_command_result(output)
                    response.chat_memory_response = output
                    response.chat_response = output
                    return response

                return output
            else:
                print("Unsupported tool call.")

    async def _process_basic_response(self, api_response):
        response_text = api_response["choices"][0]["message"]["content"]
        # add_backticks = False
        # if add_backticks:
        #     response = await self._add_backticks(response_text)

        response = ProcessedResponse()
        response.chat_memory_response = response_text
        response.chat_response = response_text
        return response

    async def _add_backticks(self, response):
        return f"```\n{response}\n```"


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
            initial_system_message="You are a quirky cybersecurity enthousiast. You always answer in a humorous way."
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
            await self._process_message(message)

    def _add_user_message(self, message_text):
        try:
            self.message_store.add_message(
                Message(role=Role.USER, content=message_text)
            )
        except Exception as e:
            print(f"Error adding user message: {e}")

    def _add_assistant_message(self, message_text):
        try:
            self.message_store.add_message(
                Message(role=Role.ASSISTANT, content=message_text)
            )
        except Exception as e:
            print(f"Error adding assistant message: {e}")

    async def _process_message(self, message):

        ###User ID
        ###Has Mention
        ###Message Text
        ###Username

        if message["user_id"] == self.config.ADMIN_USER_ID:
            if not message["has_mention"]:
                return
            # print(f"dealing with the message {message}")
            message_text = message["message_text"].replace(Config.BOT_NAME, "").strip()
            self._add_user_message(message_text)
            api_response = self._get_api_response()

            ###Chat Response
            ###Chat Memory Response

            processed_response: ProcessedResponse = (
                await self.response_processor.process(api_response)
            )
            print(processed_response)
            if processed_response.chat_response:
                self._add_assistant_message(
                    processed_response.chat_memory_response
                )  # Add this line
                await self._send_response(processed_response.chat_response)

    def _get_api_response(self):
        return self.api_client.execute_api_call(
            self.message_store.get_messages(),
            self.tool_loader.tools,
            config=self.config,
        )

    async def _send_response(self, message):
        if not message:
            print("Empty message. Skipping sending to Discord.")
            return
        message_chunks = self._split_message_into_chunks(message)
        print(f"message chunks: {message_chunks}")
        # await self._clear_textbox()

        for chunk in message_chunks:
            await self._type_and_send_chunk(chunk)

    def _split_message_into_chunks(self, message, max_length=1900):
        """Split the message into chunks of up to max_length characters."""
        result = []
        try:
            result = [message[i : i + max_length] for i in range(0, len(message), max_length)]
        except Exception as e:
            print(f"Error splitting message: {e}")
            return "error splitting message"
        return result

    async def _clear_textbox(self):
        """Clear the textbox by selecting all text and pressing backspace."""
        await self.browser.page.click(
            'div[role="textbox"]', click_count=3
        )  # Triple click to select all text
        await self.browser.page.press('div[role="textbox"]', "Backspace")

    async def _type_and_send_chunk(self, chunk):
        print(f"type and send chunk: {chunk}")
        """Type a chunk of text into the textbox and send it."""

        lines = chunk.split("\n")
        print(f"lines: {lines}")
        for i, line in enumerate(lines):
            await self.browser.page.type('div[role="textbox"]', line)
            if i < len(lines) - 1:
                print("press shift enter")
                await self._press_shift_enter()
            else:
                print("press enter")
                await self.browser.page.keyboard.press("Enter")

    async def _press_shift_enter(self):
        """Press Shift+Enter to create a newline without sending the message."""
        await self.browser.page.keyboard.down("Shift")
        await self.browser.page.keyboard.press("Enter")
        await self.browser.page.keyboard.up("Shift")


# I dont think the discord bot should load the tools. if i want to have a while loop to avoir using discord to chat,
# then I still need the tools to be loaded. the tools should be passed to the bot as a parameter.
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
