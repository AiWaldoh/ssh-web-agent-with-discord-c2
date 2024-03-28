from api.http_client import HttpClient
from api.chat_api import ChatAPI
from search.google_searcher import GoogleSearcher
from search.search_result import SearchResult
import json


class FunctionExecutor:
    def __init__(self, chat_api):
        self.chat_api: ChatAPI = chat_api

    def execute_function(self, function_call):
        function_name = function_call["name"]
        print(f"Executing function: {function_name}")

        if function_name == "search_google":
            return self.execute_search_google(function_call)
        elif function_name == "load_website":
            return self.execute_load_website(function_call)
        elif function_name == "execute_command":
            return self.execute_command(function_call)
        else:
            print(f"Function {function_name} not recognized.")
            return None

    def execute_search_google(self, function_call):
        search_query = json.loads(function_call["arguments"])["search_query"]
        print(f"Searching for: {search_query}")
        results = GoogleSearcher.search(search_query, 10)
        return results

    def execute_load_website(self, function_call):
        print("Loading website")
        website_url = json.loads(function_call["arguments"])["website_url"]
        searcher = SearchResult("title", "url", "description")
        res = searcher.fetch_and_parse_article(website_url)
        return self.trim_by_chars(res, 1000)

    def execute_command(self, function_call):
        command = json.loads(function_call["arguments"])["command"]
        try:
            BASE_URL = "http://localhost:8000"
            data = {"command": command}
            response = self.chat_api.http_client.post(f"{BASE_URL}/execute", data)
            output = response["output"]
            error = response["error"]

            print(f"Command: {command}")
            print(f"Output: {output}")
            return output
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None

    def trim_by_chars(self, res, limit):
        return f"```{res['article_full_text'][:limit]}```"
