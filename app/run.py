import os
import logging
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from api import ChatAPI
import time
import re
import time

load_dotenv()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
DISCORD_CHANNEL_URL = os.getenv("DISCORD_CHANNEL_URL")
SESSION_FILE = os.getenv("COOKIE_FILE_NAME")
INITIAL_SYSTEM_MESSAGE = os.getenv("INITIAL_SYSTEM_MESSAGE")
USERNAME = os.getenv("DISCORD_EMAIL")
PASSWORD = os.getenv("DISCORD_PASSWORD")
BOT_NAME = os.getenv("BOT_NAME")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DiscordObserver:
    def __init__(self, context, chat_api):
        self.context = context
        self.page = None
        self.chat_api = chat_api

    def start_observing(self):
        self.page = self.context.new_page()
        print(f"Loading {DISCORD_CHANNEL_URL}")
        self.page.goto(DISCORD_CHANNEL_URL)
        self.page.wait_for_selector('div[role="textbox"]')

        self.page.evaluate(
            """
            var target = document.querySelector('main[class^="chatContent"]');
            var observer = new MutationObserver(function(mutations) {
                window.mutations = mutations.map(function(mutation) {
                    return {
                        type: mutation.type,
                        addedNodes: Array.from(mutation.addedNodes).map(function(node) {
                            return node.outerHTML;
                        })
                    };
                });
            });
            var config = { childList: true, subtree: true };
            observer.observe(target, config);
            """
        )
        time.sleep(5)
        print("Listening for new messages...")
        while True:
            try:
                mutations = self.page.evaluate("window.mutations")
                if mutations:
                    self.process_mutations(mutations)
                    self.page.evaluate("window.mutations = []")
            except Exception as e:
                logging.error(f"Error evaluating mutations: {e}")
            time.sleep(1)

    def process_mutations(self, mutations):
        for mutation in mutations:
            if mutation.get("type") == "childList":
                added_nodes = mutation.get("addedNodes", [])
                for node in added_nodes:
                    node_str = str(node)
                    if 'class="markup_a7e664 messageContent__21e69"' in node_str:
                        if (
                            '<span class="mention wrapper_f46140 interactive"'
                            in node_str
                            and BOT_NAME + "</span>" in node_str
                        ):
                            text_parts = []
                            start_index = node_str.find(BOT_NAME + "</span>")
                            if start_index != -1:
                                remaining_str = node_str[
                                    start_index + len(BOT_NAME + "</span>") :
                                ]
                                span_start_index = remaining_str.find("<span>")
                                while span_start_index != -1:
                                    span_end_index = remaining_str.find(
                                        "</span>", span_start_index
                                    )
                                    if span_end_index != -1:
                                        text_part = remaining_str[
                                            span_start_index + 6 : span_end_index
                                        ].strip()
                                        text_parts.append(text_part)
                                        remaining_str = remaining_str[
                                            span_end_index + len("</span>") :
                                        ]
                                        span_start_index = remaining_str.find("<span>")
                                    else:
                                        break

                            if text_parts:
                                text = " ".join(text_parts)

                                # Extract the nickname
                                username_match = re.search(
                                    r'<span class="username_d30d99 desaturateUserColors_b72bd3 clickable_d866f1"[^>]*>([^<]+)</span>',
                                    node_str,
                                )
                                if username_match:
                                    username = username_match.group(1)
                                    self.handle_wendah_mention(username, text)

    def handle_wendah_mention(self, username, text):
        message = text.replace("@Wendah", "").strip()
        print(message)
        print("sending to chat api")
        response = self.chat_api.send_message(role="user", content=message)

        print(f"response: {response}")
        self.send_discord_message(response)

    def send_discord_message(self, message):
        self.page.wait_for_selector('div[role="textbox"]')
        self.page.type('div[role="textbox"]', message)
        self.page.keyboard.press("Enter")
        logging.info(f"Sending message to Discord: {message}")


class DiscordLogin:
    def __init__(self, context):
        self.context = context

    def login(self):
        print("logging in to discord")
        page = self.context.new_page()
        page.goto("https://discord.com/login")
        page.fill('input[name="email"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_selector(".recentsIcon__3c4cf")
        page.click('button[aria-label="User Settings"]')
        page.click('div[aria-label="Appearance"]')
        page.click('label:has-text("Show avatars in Compact mode")')
        page.click('div[aria-label="Close"]')
        self.context.storage_state(path="secret/" + SESSION_FILE)


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            if os.path.exists("secret/" + SESSION_FILE):
                context = browser.new_context(storage_state="secret/" + SESSION_FILE)
            else:
                context = browser.new_context()
                login = DiscordLogin(context)
                login.login()

            chat_api = ChatAPI(OPENROUTER_API_KEY, INITIAL_SYSTEM_MESSAGE)
            observer = DiscordObserver(context, chat_api)
            observer.start_observing()

        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            input("Press Enter to quit...")
            browser.close()


if __name__ == "__main__":
    main()
