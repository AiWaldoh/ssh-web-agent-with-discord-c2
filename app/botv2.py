from api3 import HttpClient, ChatAPI
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

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
API_URL = os.getenv("API_URL")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE")
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


def url_encode_string(s):
    return urllib.parse.quote_plus(s)


def fetch_article_content(url):
    """Fetch the content of the given URL using curl_cffi."""
    r: Response = requests.get(url, impersonate="chrome101")
    return r.content


def parse_article(html_content):
    """Parse the article using newspaper3k."""
    article = Article("")
    article.set_html(html_content)
    article.parse()
    article.nlp()  # This is required to compute the summary

    title = article.title
    text = article.text
    summary = article.summary

    return {"title": title, "text": text, "summary": summary}


def fetch_google_search_results(query, num_results=20, limit=3):
    """Fetch Google search results for the given query."""
    query = url_encode_string(query)
    r: Response = requests.get(
        f"https://www.google.com/search?client=firefox-b-d&q={query}&num={num_results}",
        impersonate="chrome101",
    )
    soup = BeautifulSoup(r.content, "html.parser")
    results = soup.find_all("div", class_="tF2Cxc")
    # Extract details from the search results
    search_results = []
    for result in results:
        title_element = result.find("h3", class_="LC20lb")
        link_element = result.find("a", href=True)
        description_element = result.find("div", class_="VwiC3b")

        title = title_element.text if title_element else None
        link = link_element["href"] if link_element else None
        description = description_element.text if description_element else None

        # Filtering out links not starting with http or https
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
        html_content = fetch_article_content(self.url)
        parsed_data = parse_article(html_content)
        self.article_content = parsed_data[
            "title"
        ]  # This is just to confirm title from newspaper matches our scraped title
        self.article_full_text = parsed_data["text"]
        self.article_summary = parsed_data["summary"]

    def fetch_and_parse_article(self, url):
        html_content = fetch_article_content(url)
        parsed_data = parse_article(html_content)

        article_data = {
            "article_url": url,
            "article_content": parsed_data["title"],
            "article_full_text": parsed_data["text"],
            "article_summary": parsed_data["summary"],
        }

        return article_data

    def display(self):
        """Display the search result details."""
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
        self.api_handler: ChatAPIHandler = api_handler

    def on_message_received(self, message_html):
        if not self._is_valid_message(message_html):
            return

        message_soup = BeautifulSoup(message_html, "html.parser")
        message_data = self._parse_message(message_soup)

        if message_data["has_mention"]:
            # print(message_data)
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
        return mention and BOT_NAME in mention.text

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


class DiscordMonitor:
    def __init__(self, message_parser, api_handler):
        self.browser = None
        self.page = None
        self.message_parser: MessageParser = message_parser
        self.api_handler: ChatAPIHandler = api_handler

    async def _send_discord_message(self, message):
        if not message:
            print("Empty message. Skipping sending to Discord.")
            return

        # Define the maximum message length
        MAX_LENGTH = 2000

        # Function to split the message into chunks of up to MAX_LENGTH characters
        def split_message(msg):
            for i in range(0, len(msg), MAX_LENGTH):
                yield msg[i : i + MAX_LENGTH]

        # Split the message into chunks
        message_chunks = list(split_message(message))

        # Send each chunk as a separate message
        for chunk in message_chunks:
            lines = chunk.split("\n")
            for i, line in enumerate(lines):
                await self.page.type('div[role="textbox"]', line)
                if i < len(lines) - 1:
                    await self.page.keyboard.down("Shift")
                    await self.page.keyboard.press("Enter")
                    await self.page.keyboard.up("Shift")
                else:
                    await self.page.keyboard.press("Enter")

    async def run(self):
        async with async_playwright() as playwright:
            await self.start_app(playwright)
            await self.keep_alive()

    async def start_app(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        await self.login_to_discord()

        print(f"Loading {os.getenv('DISCORD_CHANNEL_URL')}")
        await self.page.goto(os.getenv("DISCORD_CHANNEL_URL"))
        await self.page.wait_for_load_state("networkidle")
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
        if os.path.exists("secret/" + SESSION_FILE):
            self.context = await self.browser.new_context(
                storage_state="secret/" + SESSION_FILE
            )
        else:
            self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def on_new_message(self, msg):
        if self.message_parser._is_valid_message(msg):
            message = await asyncio.to_thread(
                self.message_parser.on_message_received, msg
            )
            #
            #
            #
            # do I parse function calls here?
            # can create different functions for different messages
            if contains_search_result(message):
                print(f"Received search result: {len(message)}")
                search_result_message = await self.handle_search_result(message)
                await self._send_discord_message(search_result_message)
            else:

                if message:
                    print("Sending this message to discord")
                    elegant_print(message)
                    await self._send_discord_message(message)

    async def handle_search_result(self, search_result):
        result_message = ""
        for item in search_result:
            result_message += f"URL: <{item.url}>\nDescription: {item.description}\n\n"
        return result_message


def contains_search_result(lst):
    if not isinstance(lst, list):
        return False
    return any(isinstance(item, SearchResult) for item in lst)


class ChatAPIHandler:
    def __init__(self, chat_api):
        self.chat_api: ChatAPI = chat_api
        self.chat_api.set_system_message("you are a helpful assistant")
        self.initialize_functions()

    def initialize_functions(self):
        custom_functions = [
            {
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
            },
            {
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
            },
            {
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
            },
        ]
        for func in custom_functions:
            self.chat_api.add_function(func)

    def handle_message(self, message_data):
        if self._is_admin(message_data["user_id"]):
            return self.send_message(message_data["message_text"])
        else:
            return self.send_message(message_data["message_text"])

    def _is_admin(self, user_id):
        return user_id == "ADMIN_USER_ID"

    def send_message(self, message):
        try:
            elegant_print(message)
            self.chat_api.set_temperature(0.3)
            # remove text @Wendah from message
            message = message.replace("@Wendah", "")
            # remove empty lines at start end end of message
            message = message.strip()

            response = self.chat_api.send_message(message)
            # print("")
            # print(response)
            elegant_print(response)
            if isinstance(response, dict) and "name" in response:
                return self.execute_function(response)
            elif response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                print("Unexpected API response format.")
                return None
        except Exception as e:
            print(f"Error occurred during API call")
            return None

    def execute_function(self, function_call):
        function_name = function_call["name"]
        print(f"Executing function: {function_name}")
        elegant_print(function_call)
        if function_name == "search_google":
            print("in search_google. Function call detected")
            search_query = json.loads(function_call["arguments"])["search_query"]
            print(f"Searching for: {search_query}")
            results = fetch_google_search_results(search_query, 10)
            return results
        elif function_name == "load_website":
            print("Loading website")
            website_url = json.loads(function_call["arguments"])["website_url"]
            searcher = SearchResult("title", "url", "description")
            res = searcher.fetch_and_parse_article(website_url)
            print(res)
            return res["article_full_text"]
        elif function_name == "execute_command":
            print("Executing command")
            # return function_call
        else:
            return None


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
    http_client = HttpClient(OPENROUTER_API_KEY)
    chat_api = ChatAPI(http_client, MODEL_NAME, API_URL)
    api_handler = ChatAPIHandler(chat_api)
    message_parser = MessageParser(api_handler)
    discord_monitor = DiscordMonitor(message_parser, api_handler)

    asyncio.run(run_with_retries(discord_monitor))
