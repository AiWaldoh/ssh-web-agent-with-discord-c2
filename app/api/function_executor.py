from api.http_client import HttpClient
from api.chat_api import ChatAPI
from search.google_searcher import GoogleSearcher
from search.search_result import SearchResult
import json
from config.config import Config


class FunctionExecutor:
    def __init__(self, chat_api):
        self.chat_api: ChatAPI = chat_api

    def execute_function(self, function_call, user_id):
        function_name = function_call["name"]
        print(f"Executing function: {function_name}")

        if function_name == "search_google":
            return self.execute_search_google(function_call)
        elif function_name == "load_website":
            return self.execute_load_website(function_call)
        elif function_name == "execute_command":
            print("in execute_command")
            print(f"user_id: {user_id}")
            print(f"Config.ADMIN_USER_ID: {Config.ADMIN_USER_ID}")
            if user_id == Config.ADMIN_USER_ID:
                print(f"running admin command for user {user_id}")
                result = self.execute_command(function_call)

                # surround with triple backticks to make it a code block
                # remove triple backticks from result string
                result = result.replace("```", "")
                result = self.truncate_string(result, 1900)
                return f"```{result}```"
            else:
                return "haha charade you are"
        else:
            print(f"Function {function_name} not recognized.")
            return None

    def truncate_string(self, string, max_chars):
        if len(string) <= max_chars:
            return string
        else:
            return string[:max_chars]

    def execute_search_google(self, function_call):
        search_query = json.loads(function_call["arguments"])["search_query"]
        print(f"Searching for: {search_query}")
        results = GoogleSearcher.search(search_query, 10)
        return results

    def execute_load_website(self, function_call):
        print("Loading website")
        website_url = json.loads(function_call["arguments"])["website_url"]
        print(f"Loading website: {website_url}")
        searcher = SearchResult("title", website_url, "description")
        res = searcher.fetch_and_parse_article()
        # print(res)
        print(f"before trim: ")
        return res["text"]

    def execute_command(self, function_call):
        command = json.loads(function_call["arguments"])["command"]
        try:
            data = {"command": command}
            response = self.chat_api.http_client.post(
                f"{Config.BASE_URL}/execute", data
            )
            output = response["output"]
            error = response["error"]

            print(f"Command: {command}")
            print(f"Output: {output}")
            return output
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None
