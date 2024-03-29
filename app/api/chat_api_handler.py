from config.config import Config
from api.function_executor import FunctionExecutor
from api.custom_function_factory import CustomFunctionFactory
from api.http_client import HttpClient
from api.chat_api import ChatAPI


class ChatAPIHandler:
    def __init__(self, chat_api):
        self.http_client = HttpClient(Config.OPENROUTER_API_KEY)
        self.chat_api: ChatAPI = chat_api
        self.function_executor: FunctionExecutor = FunctionExecutor(chat_api)
        self.custom_functions: CustomFunctionFactory = CustomFunctionFactory(
            self.chat_api
        )
        self.initialize_chat_api()

    def initialize_chat_api(self):
        self.chat_api.set_system_message(Config.SYSTEM_MESSAGE)
        self.add_custom_functions()

    def add_custom_functions(self):
        custom_functions = self.custom_functions.create_all_functions()
        for func in custom_functions:
            self.chat_api.add_function(func)

    # figure out why process_response is used in handle_message and in process_response
    def handle_message(self, message_data):
        print(f"in function handle_message")
        user_id = message_data["user_id"]
        print(f"user_id: {user_id}")
        message_text = message_data["message_text"]
        print(f"message_text: {message_text}")
        function_call = self.process_response(message_text, user_id)
        print(f"function_call: {function_call}")
        if function_call:
            print(f"Function call: {function_call}")
            return self.function_executor.execute_function(function_call, user_id)
        else:
            print("No function call detected")
            return self.send_message(message_text, user_id)

    def send_message(self, message, user_id):
        try:

            preprocessed_message = self.preprocess_message(message)
            response = self.chat_api.send_message(preprocessed_message)
            return self.process_response(response, user_id)
        except Exception as e:
            print(f"Error occurred during API call: {str(e)}")
            return None

    def preprocess_message(self, message):
        message = message.replace(Config.BOT_NAME, "")
        message = message.strip()
        return message

    def process_response(self, response, user_id):
        if isinstance(response, dict) and "name" in response:
            print("in a function? in process_response")
            return self.function_executor.execute_function(response, user_id)
        elif response and "choices" in response and len(response["choices"]) > 0:
            print("in regular response? in process_response")
            return response["choices"][0]["message"]["content"]
        else:
            print("Unexpected API response format.")
            return None
