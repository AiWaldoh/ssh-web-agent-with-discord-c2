import requests
import os
import json
import yaml
from dotenv import load_dotenv
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List
from discord_bot import Config, DiscordBot

load_dotenv()


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str


class MessageStore:
    def __init__(self, initial_system_message: str):
        self.messages: List[Message] = [
            Message(role=Role.SYSTEM, content=initial_system_message)
        ]

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages(self) -> List[Message]:
        return self.messages

    def truncate_history(self, max_history: int):
        user_messages = [msg for msg in self.messages if msg.role == Role.USER]
        if len(user_messages) > max_history:
            trim_index = len(self.messages) - len(user_messages) + max_history
            self.messages = self.messages[trim_index:]


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


class AITaskCommand(ABC):
    @abstractmethod
    def execute(self, arguments):
        pass


class ExecuteCommandTask(AITaskCommand):
    def execute(self, arguments):
        command = arguments.get("command")
        if command:
            print(f"Executing command: {command}")
            output = subprocess.check_output(
                command, shell=True, universal_newlines=True
            )
            return output
        else:
            print("No command provided.")
            return "No command provided."


class SearchGoogleTask(AITaskCommand):
    def execute(self, arguments):
        search_query = arguments.get("search_query")
        if search_query:
            print(f"Searching for: {search_query}")
            return "Search results"
        else:
            print("No search query provided.")
            return "No search query provided."


class LoadWebsiteTask(AITaskCommand):
    def execute(self, arguments):
        website_url = arguments.get("website_url")
        if website_url:
            print(f"Loading website: {website_url}")
            return "Website loaded"
        else:
            print("No website URL provided.")
            return "No website URL provided."


class AITaskRegistry:
    _instance = None
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, task_name, command):
        cls._registry[task_name] = command

    @classmethod
    def get_command(cls, task_name):
        return cls._registry.get(task_name)


class ToolLoader:
    def __init__(self):
        self.tools = []

    def load_tools_from_yaml(self, file_path):
        with open(file_path, "r") as file:
            tools_data = yaml.safe_load(file)
            self.tools = tools_data["tools"]


class UserInputHandler:
    def get_user_input(self):
        return input("Enter a message: ")


class APIResponseProcessor:
    def process_api_response(self, response, message_store):
        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice["message"]
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]
                self.execute_tool_calls(tool_calls, message_store)
            else:
                print("Assistant:", message["content"])
                message_store.add_message(
                    Message(role=Role(message["role"]), content=message["content"])
                )
        else:
            print("No response or no choices in the response.")
        return message_store

    def execute_tool_calls(self, tool_calls, message_store):
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            command = AITaskRegistry.get_command(tool_name)
            if command:
                output = command.execute(tool_args)
                message_store.add_message(
                    Message(
                        role=Role.ASSISTANT,
                        content=f"Executed tool: {tool_name}\nExecuted command: {tool_args.get('command')}\nOutput:\n{output}",
                    )
                )
            else:
                print("Unsupported tool call.")


class ChatApplication:
    def __init__(self, api_key, model_name="gpt-3.5-turbo", temperature=1.0):
        self.chat_api_service = ChatAPIService(
            api_key=api_key, model_name=model_name, temperature=temperature
        )
        self.tool_loader = ToolLoader()
        self.user_input_handler = UserInputHandler()
        self.api_response_processor = APIResponseProcessor()
        self.message_store = MessageStore(
            initial_system_message="You are a helpful assistant."
        )

    def load_tools(self, file_path):
        self.tool_loader.load_tools_from_yaml(file_path)
        for tool_data in self.tool_loader.tools:
            tool_name = tool_data["function"]["name"]
            tool_class_name = (
                "".join(word.capitalize() for word in tool_name.split("_")) + "Task"
            )
            tool_class = globals()[tool_class_name]
            AITaskRegistry.register(tool_name, tool_class())

    def run(self):
        self.load_tools("tools.yaml")
        config = {
            "temperature": 1.2,
            "model_name": "gpt-3.5-turbo",
        }
        while True:

            # add discord bot here
            user_input = self.user_input_handler.get_user_input()
            self.message_store.add_message(Message(role=Role.USER, content=user_input))
            response = self.chat_api_service.execute_api_call(
                self.message_store.get_messages(), self.tool_loader.tools, config=config
            )
            self.message_store = self.api_response_processor.process_api_response(
                response, self.message_store
            )
            self.message_store.truncate_history(max_history=5)


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    chat_app = ChatApplication(api_key)
    chat_app.run()


if __name__ == "__main__":
    main()
