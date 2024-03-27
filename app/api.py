import requests
import json
import logging


class HttpClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, url, data):
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()


class ChatAPI:
    def __init__(
        self, http_client, initial_system_message="You are a helpful assistant."
    ):
        self.http_client = http_client
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.messages = [{"role": "system", "content": initial_system_message}]
        self.max_history = 30

    def get_system_message(self):
        return self.messages[0]["content"] if self.messages else None

    def set_system_message(self, content):
        if self.messages:
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages.insert(0, {"role": "system", "content": content})

    def send_message(self, content):

        self.messages.append({"role": "user", "content": content})

        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        if len(user_messages) > self.max_history:
            index = len(self.messages) - len(user_messages) + self.max_history
            self.messages = self.messages[index:]

        data = {"model": "openai/gpt-3.5-turbo-16k", "messages": self.messages}

        response = self.http_client.post(self.url, data)

        try:
            ai_message_content = response["choices"][0]["message"]["content"]
            self.messages.append({"role": "assistant", "content": ai_message_content})
            return response
        except KeyError:
            # If the response doesn't have the "choices" key, it means an error occurred
            # Remove the flagged message from the conversation history
            self.messages.pop()
            logging.error(f"Error in API response: {response}")
            return response["error"]["message"]
