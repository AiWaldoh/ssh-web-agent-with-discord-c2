class ChatAPI:
    def __init__(
        self,
        http_client,
        model_name,
        api_url,
        initial_system_message,
    ):
        self.http_client = http_client
        self.model_name = model_name
        self.url = api_url
        self.messages = [{"role": "system", "content": initial_system_message}]
        self.max_history = 5
        self.temperature = 1.1
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
            return response["error"]["message"]

    def _add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def _remove_last_user_message(self):
        self.messages.pop()
