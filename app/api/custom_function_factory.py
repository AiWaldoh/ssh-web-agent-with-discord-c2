from api.chat_api import ChatAPI


class CustomFunctionFactory:
    def __init__(self, chat_api):
        self.chat_api: ChatAPI = chat_api

    def create_all_functions(self):
        return [
            self.create_execute_command_function(),
            self.create_search_google_function(),
            self.create_load_website_function(),
        ]

    def create_execute_command_function(self):
        return {
            "name": "execute_command",
            "description": "Determine if the message is asking to run a command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "User input command.",
                    }
                },
            },
        }

    def create_search_google_function(self):
        return {
            "name": "search_google",
            "description": "Search for a query on Google",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "The query to search on Google if user specified to search.",
                    }
                },
                "required": ["search_query"],
            },
        }

    def create_load_website_function(self):
        return {
            "name": "load_website",
            "description": "Load a website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "website_url": {
                        "type": "string",
                        "description": "The URL of the website to load if user specified to load a website.",
                    }
                },
                "required": ["website_url"],
            },
        }
