from config.config import Config
from message.message_parser import MessageParser
from message.message_sender import MessageSender
from search.search_result_handler import SearchResultHandler
from utils.printer import Printer
import asyncio
import os
from config.config import Config
from search.search_result import SearchResult
from browser.browser_automation import BrowserAutomation
from api.chat_api_handler import ChatAPIHandler

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


def contains_search_result(lst):
    if not isinstance(lst, list):
        return False
    return any(isinstance(item, SearchResult) for item in lst)


class DiscordMonitor(BrowserAutomation):
    def __init__(
        self, message_parser, api_handler, message_sender, search_result_handler
    ):
        super().__init__()
        self.message_parser: MessageParser = message_parser
        self.api_handler: ChatAPIHandler = api_handler
        self.message_sender: MessageSender = message_sender
        self.search_result_handler: SearchResultHandler = search_result_handler

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
