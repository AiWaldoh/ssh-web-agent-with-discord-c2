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
    GoToPageTask,
    TakeScreenshotTask,
    ClickElementTask,
    FormDetailsTask,
    LinksTask,
    ButtonsTask,
    SubmitFormTask,
    GetPageSourceTask,
    GetCurrentUrlTask,
    FillInputTask,
)
from init import Config, MessageStore, Message, Role, ToolLoader, JAVASCRIPT_SCR
from init_web import DiscordBrowser, MessageExtractor, MessageParser, MessageValidator
from init_api import ChatAPIService
import json
from typing import Any, List,  Dict
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict
load_dotenv()


@dataclass
class ProcessedResponse:
    def __init__(self):
        self.chat_memory_response = ""
        self.chat_response = ""


class TaskDependencies:
    def __init__(self, browser: DiscordBrowser):
        self.browser = browser


class BasicResponseProcessor:
    async def process(self, api_response):
        response_text = api_response["choices"][0]["message"]["content"]
        response = ProcessedResponse()
        response.chat_memory_response = response_text
        response.chat_response = response_text
        return response


class ResponseProcessor:
    def __init__(self, dependencies: TaskDependencies):
        self.tool_call_processor = ToolCallProcessor(dependencies)
        self.basic_response_processor = BasicResponseProcessor()

    async def process(self, api_response):
        tool_calls = self._extract_tool_calls(api_response)

        if tool_calls:
            return await self.tool_call_processor.process(tool_calls)
        else:
            return await self.basic_response_processor.process(api_response)

    def _extract_tool_calls(self, response):
        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice["message"]
            if "tool_calls" in message:
                return message["tool_calls"]
        return None



class ToolManager:
    def __init__(self, config: Config, task_dependencies: TaskDependencies):
        self.config = config
        self.task_dependencies = task_dependencies
        self.message_extractor = MessageExtractor()
        self.message_validator = MessageValidator()
        self.message_parser = MessageParser(
            self.message_extractor, self.message_validator
        )
        self.api_client = ChatAPIService(config.OPENROUTER_API_KEY, config.MODEL_NAME)
        self.response_processor = ResponseProcessor(self.task_dependencies)
        self.tool_loader = ToolLoader()
        self.load_and_register_tools("tools.yaml")

    def load_and_register_tools(self, file_path):
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


class ToolCallProcessor:
    def __init__(self, dependencies: TaskDependencies):
        self.dependencies = dependencies

    async def process(self, tool_calls):
        try:

            response = ProcessedResponse()
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                print(f"tool name: {tool_name}")
                command = AITaskRegistry.get_command(tool_name)
                if command:

                    # Assume all functions are browser related and require a separate tab

                    output = await command.execute(tool_args, self.dependencies)
                    print(f"output: {output}")
                    await command.process_result(output, response)
                    return response
                else:
                    raise ValueError(f"Unsupported tool call: {tool_name}")
            return response
        except Exception as e:
            print(f"Error processing tool calls: {e}")
            return None


class DiscordClient:
    def __init__(
        self,
        config: Config,
        message_parser: MessageParser,
        api_client: ChatAPIService,
        response_processor: ResponseProcessor,
        tool_manager: ToolManager,
        discord_browser: DiscordBrowser,
    ):
        self.config: Config = config
        self.message_parser: MessageParser = message_parser
        self.api_client: ChatAPIService = api_client
        self.response_processor: ResponseProcessor = response_processor
        self.discord_browser: DiscordBrowser = discord_browser
        self.tool_manager: ToolManager = tool_manager
        self.message_store = MessageStore(
            initial_system_message="You are a quirky cybersecurity enthousiast. You always answer in a humorous way."
        )

    async def start(self):
        async with async_playwright() as playwright:
            await self.discord_browser.launch(playwright)
            await self.discord_browser.login()
            await self.discord_browser.load_channel()
            await self.discord_browser.expose_on_message_function(self._on_message)
            await self._keep_alive()

    async def _keep_alive(self):
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Script terminated by user.")
        finally:
            await self.discord_browser.close()

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
        if message["user_id"] == self.config.ADMIN_USER_ID:
            if not message["has_mention"]:
                return

            message_text = message["message_text"].replace(Config.BOT_NAME, "").strip()

            self._add_user_message(message_text)

            api_response = self._get_api_response()

            processed_response: ProcessedResponse = (
                await self.response_processor.process(api_response)
            )

            if processed_response.chat_response:
                self._add_assistant_message(processed_response.chat_memory_response)

                await self._send_response(processed_response.chat_response)

    def _get_api_response(self):
        return self.api_client.execute_api_call(
            self.message_store.get_messages(),
            self.tool_manager.tool_loader.tools,
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
            result = [
                message[i : i + max_length] for i in range(0, len(message), max_length)
            ]
        except Exception as e:
            print(f"Error splitting message: {e}")
            return "error splitting message"
        return result

    async def _clear_textbox(self):
        """Clear the textbox by selecting all text and pressing backspace."""
        await self.discord_browser.page.click(
            'div[role="textbox"]', click_count=3
        )  # Triple click to select all text
        await self.discord_browser.page.press('div[role="textbox"]', "Backspace")

    async def _type_and_send_chunk(self, chunk):
        print(f"type and send chunk: {chunk}")
        """Type a chunk of text into the textbox and send it."""

        lines = chunk.split("\n")
        print(f"lines: {lines}")
        for i, line in enumerate(lines):
            await self.discord_browser.page.type('div[role="textbox"]', line)
            if i < len(lines) - 1:
                print("press shift enter")
                await self._press_shift_enter()
            else:
                print("press enter")
                await self.discord_browser.page.keyboard.press("Enter")

    async def _press_shift_enter(self):
        """Press Shift+Enter to create a newline without sending the message."""
        await self.discord_browser.page.keyboard.down("Shift")
        await self.discord_browser.page.keyboard.press("Enter")
        await self.discord_browser.page.keyboard.up("Shift")


class DiscordBot:
    def __init__(self, config: Config):
        self.config = config
        self.discord_browser = DiscordBrowser(config)
        self.task_dependencies = TaskDependencies(self.discord_browser)
        self.tool_manager = ToolManager(config, self.task_dependencies)
        self.discord_client = DiscordClient(
            config,
            self.tool_manager.message_parser,
            self.tool_manager.api_client,
            self.tool_manager.response_processor,
            self.tool_manager,
            self.discord_browser,
        )

    async def start(self):
        await self.discord_client.start()


if __name__ == "__main__":
    config = Config()
    bot = DiscordBot(config)
    asyncio.run(bot.start())
