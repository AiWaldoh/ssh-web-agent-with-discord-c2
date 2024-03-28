import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import urllib.parse
from playwright.async_api import async_playwright
import asyncio
from requests.models import Response
from curl_cffi import requests
from newspaper import Article
import json
from termcolor import colored
from api3 import HttpClient, ChatAPI

load_dotenv()

JAVASCRIPT_SCR = """
                var target = document.querySelector('main[class^="chatContent"]');
                var observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList') {
                            mutation.addedNodes.forEach(function(node) {
                                window.onNewMessage(JSON.stringify(node.outerHTML));
                            });
                        }
                    });
                });
                var config = { childList: true, subtree: true };
                observer.observe(target, config);
            """


class Config:
    BOT_NAME = os.getenv("BOT_NAME")
    MODEL_NAME = os.getenv("MODEL_NAME")
    API_URL = os.getenv("API_URL")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
    SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
    SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")
    DISCORD_CHANNEL_URL = os.getenv("DISCORD_CHANNEL_URL")


class Printer:
    @staticmethod
    def print_json(json_string):
        try:
            json_object = json.loads(json_string)
            print(colored(json.dumps(json_object, indent=2), "green"))
        except json.JSONDecodeError:
            print(colored(json_string, "blue"))

    @staticmethod
    def print_colored(text, color):
        print(colored(str(text), color))


class UrlEncoder:
    @staticmethod
    def encode(url):
        return urllib.parse.quote_plus(url)


class ArticleFetcher:
    @staticmethod
    def fetch_content(url):
        r: Response = requests.get(url, impersonate="chrome101")
        return r.content


class ArticleParser:
    @staticmethod
    def parse(html_content):
        article = Article("")
        article.set_html(html_content)
        article.parse()
        article.nlp()

        return {
            "title": article.title,
            "text": article.text,
            "summary": article.summary,
        }


class GoogleSearcher:
    @staticmethod
    def search(query, num_results=20, limit=3):
        query = UrlEncoder.encode(query)
        r: Response = requests.get(
            f"https://www.google.com/search?client=firefox-b-d&q={query}&num={num_results}",
            impersonate="chrome101",
        )
        soup = BeautifulSoup(r.content, "html.parser")
        results = soup.find_all("div", class_="tF2Cxc")
        search_results = []
        for result in results:
            title_element = result.find("h3", class_="LC20lb")
            link_element = result.find("a", href=True)
            description_element = result.find("div", class_="VwiC3b")

            title = title_element.text if title_element else None
            link = link_element["href"] if link_element else None
            description = description_element.text if description_element else None

            if link and (link.startswith("http://") or link.startswith("https://")):
                search_results.append(SearchResult(title, link, description))

        return search_results[:limit]


class SearchResult:
    def __init__(self, title, url, description):
        self.title = title
        self.url = url
        self.description = description
        self.article_content = None
        self.article_summary = None
        self.article_full_text = None

    def fetch_and_parse_article(self):
        html_content = ArticleFetcher.fetch_content(self.url)
        parsed_data = ArticleParser.parse(html_content)
        self.article_content = parsed_data["title"]
        self.article_full_text = parsed_data["text"]
        self.article_summary = parsed_data["summary"]

    def display(self):
        print(f"Title: {self.title}")
        print(f"URL: {self.url}")
        print(f"Description: {self.description}")
        if self.article_content:
            print(f"Article Title (from newspaper3k): {self.article_content}")
            print(f"\nFull Text:\n{self.article_full_text}")
            print(f"\nSummary:\n{self.article_summary}")
        print("------")


class MessageParser:
    def __init__(self, api_handler):
        self.api_handler = api_handler

    def on_message_received(self, message_html):
        if not self._is_valid_message(message_html):
            return

        message_soup = BeautifulSoup(message_html, "html.parser")
        message_data = self._parse_message(message_soup)

        if message_data["has_mention"]:
            return self.api_handler.handle_message(message_data)

    def _parse_message(self, message_soup):
        user_id = self._get_user_id(message_soup)
        has_mention = self._is_mention(message_soup)
        username = self._get_username(message_soup)
        message_text = self._get_message(message_soup, has_mention)

        return {
            "user_id": user_id,
            "username": username,
            "has_mention": has_mention,
            "message_text": message_text.strip(),
        }

    def _get_user_id(self, message_soup):
        img_src = message_soup.find("img")["src"] if message_soup.find("img") else None
        return self._extract_user_id(img_src)

    def _is_mention(self, message_soup):
        mention = message_soup.select_one('span[class*="mention"]')
        return mention and Config.BOT_NAME in mention.text

    def _get_username(self, message_soup):
        username_element = message_soup.find(
            "span", class_=lambda x: x and "username_d30d99" in x
        )
        if username_element:
            return username_element.text.strip()
        return None

    def _get_message(self, message_soup, has_mention):
        message_div = message_soup.select_one('div[class*="markup"]')
        if message_div:
            message_spans = message_div.find_all("span")
            if has_mention:
                mention_span = message_div.select_one('span[class*="mention"]')
                if mention_span:
                    message_text = (
                        mention_span.get_text()
                        + " "
                        + " ".join(
                            span.get_text()
                            for span in message_spans
                            if span != mention_span
                        )
                    )
                else:
                    message_text = " ".join(span.get_text() for span in message_spans)
            else:
                message_text = " ".join(span.get_text() for span in message_spans)
            return message_text.strip()
        else:
            return ""

    def _extract_user_id(self, img_src):
        if img_src:
            img_src = img_src.strip('"\\')
            match = re.search(r"/avatars/(\d+)/", img_src)
            if match:
                return match.group(1)
        return None

    def _is_valid_message(self, message_html):
        return message_html.strip().startswith('"<li')


from abc import ABC, abstractmethod


class BrowserAutomation(ABC):
    def __init__(self):
        self.browser = None
        self.page = None

    @abstractmethod
    async def start_app(self, playwright):
        pass

    @abstractmethod
    async def keep_alive(self):
        pass

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            await self.keep_alive()


class MessageSender:
    async def send_message(self, page, message):
        if not message:
            print("Empty message. Skipping sending to Discord.")
            return

        message_chunks = self._split_message_into_chunks(message)
        await self._clear_textbox(page)

        for chunk in message_chunks:
            await self._type_and_send_chunk(page, chunk)

    def _split_message_into_chunks(self, message, max_length=1900):
        return [message[i : i + max_length] for i in range(0, len(message), max_length)]

    async def _clear_textbox(self, page):
        await page.click('div[role="textbox"]', click_count=3)
        await page.press('div[role="textbox"]', "Backspace")

    async def _type_and_send_chunk(self, page, chunk):
        lines = chunk.split("\n")
        for i, line in enumerate(lines):
            await page.type('div[role="textbox"]', line)
            if i < len(lines) - 1:
                await self._press_shift_enter(page)
            else:
                await page.keyboard.press("Enter")

    async def _press_shift_enter(self, page):
        await page.keyboard.down("Shift")
        await page.keyboard.press("Enter")
        await page.keyboard.up("Shift")


class SearchResultHandler:
    def format_search_result(self, search_result):
        result_message = ""
        for item in search_result:
            description = f"```{item.description}```"
            result_message += f" <{item.url}>\n{description}\n"
        return result_message


class DiscordMonitor(BrowserAutomation):
    def __init__(
        self, message_parser, api_handler, message_sender, search_result_handler
    ):
        super().__init__()
        self.message_parser = message_parser
        self.api_handler = api_handler
        self.message_sender = message_sender
        self.search_result_handler = search_result_handler

    async def start_app(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        await self.login_to_discord()

        print(f"Loading {Config.DISCORD_CHANNEL_URL}")
        await self.page.goto(Config.DISCORD_CHANNEL_URL)
        await self.page.wait_for_selector("div[role='textbox']")
        await asyncio.sleep(5)
        await self.page.expose_function("onNewMessage", self.on_new_message)
        await self.page.evaluate(JAVASCRIPT_SCR)

        print("Listening for new messages...")

    async def keep_alive(self):
        try:
            while True:
                await self.page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("Script terminated by user.")

        await self.browser.close()

    async def login_to_discord(self):
        if os.path.exists("secret/" + Config.SESSION_FILE):
            self.context = await self.browser.new_context(
                storage_state="secret/" + Config.SESSION_FILE
            )
        else:
            self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def on_new_message(self, msg):
        if self.message_parser._is_valid_message(msg):
            message = await asyncio.to_thread(
                self.message_parser.on_message_received, msg
            )

            if contains_search_result(message):
                print(f"Received search result: {len(message)}")
                search_result_message = self.search_result_handler.format_search_result(
                    message
                )
                await self.message_sender.send_message(self.page, search_result_message)
            else:
                if message:
                    print("Sending this message to discord")
                    Printer.print_json(message)
                    await self.message_sender.send_message(self.page, message)


def contains_search_result(lst):
    if not isinstance(lst, list):
        return False
    return any(isinstance(item, SearchResult) for item in lst)


class ChatAPIHandler:
    def __init__(self, chat_api):
        self.http_client = HttpClient(Config.OPENROUTER_API_KEY)
        self.chat_api = chat_api
        self.function_executor = FunctionExecutor(chat_api)
        self.custom_functions = CustomFunctionFactory(self.chat_api)
        self.initialize_chat_api()

    def initialize_chat_api(self):
        self.chat_api.set_system_message(Config.SYSTEM_MESSAGE)
        self.add_custom_functions()

    def add_custom_functions(self):
        custom_functions = self.custom_functions.create_all_functions()
        for func in custom_functions:
            self.chat_api.add_function(func)

    def handle_message(self, message_data):
        user_id = message_data["user_id"]
        message_text = message_data["message_text"]
        function_call = self.process_response(message_text)
        if function_call:
            return self.function_executor.execute_function(function_call)
        else:
            return self.send_message(message_text)

    def send_message(self, message):
        try:

            preprocessed_message = self.preprocess_message(message)
            response = self.chat_api.send_message(preprocessed_message)
            print(f"Response: {response}")
            return self.process_response(response)
        except Exception as e:
            print(f"Error occurred during API call: {str(e)}")
            return None

    def preprocess_message(self, message):
        message = message.replace("@Wendah", "")
        message = message.strip()
        return message

    def process_response(self, response):
        if isinstance(response, dict) and "name" in response:
            print("in isinstance")
            return self.function_executor.execute_function(response)
        elif response and "choices" in response and len(response["choices"]) > 0:
            print("in choices")
            return response["choices"][0]["message"]["content"]
        else:
            print("Unexpected API response format.")
            return None


class CustomFunctionFactory:
    def __init__(self, chat_api):
        self.chat_api = chat_api

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


class FunctionExecutor:
    def __init__(self, chat_api):
        self.chat_api = chat_api

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


async def run_with_retries(discord_monitor, max_retries=5, interval=10):
    attempt = 0
    while attempt < max_retries:
        try:
            await discord_monitor.run()
            break  # Exit the loop if the run is successful
        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt} failed with error: {e}")
            if attempt < max_retries:
                print(f"Retrying in {interval} seconds...")
                await asyncio.sleep(
                    interval
                )  # Wait for the specified interval before retrying


if __name__ == "__main__":
    http_client = HttpClient(Config.OPENROUTER_API_KEY)
    chat_api = ChatAPI(http_client, Config.MODEL_NAME, Config.API_URL)
    api_handler = ChatAPIHandler(chat_api)
    message_parser = MessageParser(api_handler)
    message_sender = MessageSender()
    search_result_handler = SearchResultHandler()
    discord_monitor = DiscordMonitor(
        message_parser, api_handler, message_sender, search_result_handler
    )

    asyncio.run(run_with_retries(discord_monitor))
