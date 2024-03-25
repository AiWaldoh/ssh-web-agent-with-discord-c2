import requests
import json
import logging


class BaseAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, data):
        response = requests.post(
            url=self.url, headers=self.headers, data=json.dumps(data)
        )
        return response.json()


class ChatAPI(BaseAPI):
    def __init__(self, api_key, initial_system_message="You are a helpful assistant."):
        super().__init__(api_key)
        self.messages = [{"role": "system", "content": initial_system_message}]
        self.max_history = 30

    def get_system_message(self):
        return self.messages[0]["content"] if self.messages else None

    def set_system_message(self, content):
        if self.messages:
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages.insert(0, {"role": "system", "content": content})

    def send_message(self, role, content):
        if role not in ["user", "assistant"]:
            raise ValueError("Role must be either 'user' or 'assistant'")

        # Append the new message from the user or the assistant
        self.messages.append({"role": role, "content": content})

        # Truncate message history to the last 10 user messages
        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        if len(user_messages) > self.max_history:
            index = len(self.messages) - len(user_messages) + self.max_history
            self.messages = self.messages[index:]

        data = {"model": "openai/gpt-3.5-turbo-16k", "messages": self.messages}

        response = self.post(data)

        # Add the AI's response to the conversation history if it's not the system message
        if role == "user":
            print(response)
            try:
                ai_message_content = response["choices"][0]["message"]["content"]
                self.messages.append(
                    {"role": "assistant", "content": ai_message_content}
                )
                return ai_message_content
            except KeyError:
                # If the response doesn't have the "choices" key, it means an error occurred
                # Remove the flagged message from the conversation history
                self.messages.pop()
                logging.error(f"Error in API response: {response}")
                return response["error"]["message"]
        return None  # No response is expected when the assistant sends a message
