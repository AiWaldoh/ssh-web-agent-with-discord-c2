import requests
import logging
import json
from termcolor import colored


def elegant_print(*args, **kwargs):
    for arg in args:
        if isinstance(arg, str):
            try:
                # Attempt to load the string as JSON
                json_object = json.loads(arg)
                # If successful, pretty-print the JSON string in green
                print(colored(json.dumps(json_object, indent=2), "green"))
            except json.JSONDecodeError:
                # If it's not valid JSON, just print the string in blue
                print(colored(arg, "blue"))
        else:
            # If the argument is not a string, print it in grey
            print(colored(str(arg), "grey"))


class HttpClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, url, data):
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        return response.json()


class ChatAPI:
    def __init__(
        self,
        http_client,
        model_name,
        api_url,
        initial_system_message="You are a helpful assistant.",
    ):
        self.http_client = http_client
        self.model_name = model_name
        self.url = api_url
        self.messages = [{"role": "system", "content": initial_system_message}]
        self.max_history = 30
        self.temperature = 0.7
        self.functions = []

    def get_system_message(self):
        return self.messages[0]["content"] if self.messages else None

    def set_system_message(self, content):
        self._update_or_insert_system_message(content)

    def get_temperature(self):
        return self.temperature

    def set_temperature(self, temperature):
        self.temperature = temperature

    def add_function(self, function):
        self.functions.append(function)

    def _update_or_insert_system_message(self, content):
        if self.messages:
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages.insert(0, {"role": "system", "content": content})

    def send_message(self, content):
        self._add_user_message(content)
        self._trim_history()
        response = self._send_api_request()
        return self._process_api_response(response)

    def _add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def _trim_history(self):
        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        if len(user_messages) > self.max_history:
            index = len(self.messages) - len(user_messages) + self.max_history
            self.messages = self.messages[index:]

    def _send_api_request(self):
        data = {
            "model": self.model_name,
            "messages": self.messages,
            "temperature": self.temperature,
            "functions": self.functions,
            "function_call": "auto" if self.functions else None,
        }
        print(data)
        return self.http_client.post(self.url, data)

    def _process_api_response(self, response):
        try:
            if "function_call" in response["choices"][0]["message"]:

                function_call = response["choices"][0]["message"]["function_call"]
                # function_name = function_call["name"]
                print(function_call)  # json.dumps(function_call)
                self._add_assistant_message("OK")
                return function_call
            else:
                ai_message_content = response["choices"][0]["message"]["content"]
                if ai_message_content is not None:
                    self._add_assistant_message(ai_message_content)
                return response
        except KeyError:
            self._remove_last_user_message()
            logging.error(f"Error in API response: {response}")
            return response["error"]["message"]

    def _add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def _remove_last_user_message(self):
        self.messages.pop()
