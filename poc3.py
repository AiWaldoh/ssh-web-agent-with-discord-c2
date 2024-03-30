import requests
import os
import json
import yaml
from dotenv import load_dotenv
import subprocess
from abc import ABC, abstractmethod

load_dotenv()


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


class ChatAPI:
    def __init__(self, api_key, model_name="gpt-3.5-turbo", temperature=0.7):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.http_client = HttpClient(api_key)

    def execute_tool_call(self, messages, tools):
        url = "https://openrouter.ai/api/v1/chat/completions"
        data = {
            "messages": messages,
            "model": self.model_name,
            "temperature": self.temperature,
            "tools": tools,
        }
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


def load_tools_from_yaml(file_path):
    with open(file_path, "r") as file:
        tools_data = yaml.safe_load(file)
        return tools_data["tools"]


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")

    # Register AI task commands
    AITaskRegistry.register("execute_command", ExecuteCommandTask())

    chat_api = ChatAPI(api_key=api_key)
    message_history = [{"role": "system", "content": "You are a helpful assistant."}]
    while True:
        print(message_history)
        user_input = input("Enter a message: ")
        message_history.append({"role": "user", "content": user_input})
        tools_file_path = "tools.yaml"
        tools = load_tools_from_yaml(tools_file_path)

        response = chat_api.execute_tool_call(message_history, tools)

        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice["message"]
            if "tool_calls" in message:
                print(f"message: {message}")
                tool_calls = message["tool_calls"]
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    print(f"Tool call: {tool_name}")
                    command = AITaskRegistry.get_command(tool_name)
                    if command:
                        output = command.execute(tool_args)
                        message_history.append(
                            {
                                "role": "assistant",
                                "content": f"Executed tool: {tool_name}\nExecuted command: {tool_args['command']}\nOutput:\n{output}",
                            }
                        )
                    else:
                        print("Unsupported tool call.")
            else:
                print("Assistant:", message["content"])
                message_history.append(message)
        else:
            print("No response or no choices in the response.")


if __name__ == "__main__":
    main()
