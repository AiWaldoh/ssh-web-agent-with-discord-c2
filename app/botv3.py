import asyncio
from api.http_client import HttpClient
from api.chat_api import ChatAPI
from config.config import Config
from search.search_result_handler import SearchResultHandler
from message.message_parser import MessageParser
from message.message_sender import MessageSender
from browser.discord_monitor import DiscordMonitor
from api.chat_api_handler import ChatAPIHandler


async def run_with_retries(discord_monitor: DiscordMonitor, max_retries=5, interval=10):
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
    print(Config.MODEL_NAME)
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
