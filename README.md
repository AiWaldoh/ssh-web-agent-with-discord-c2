# Discord Chat Bot

This is a Discord chat bot that uses the OpenAI API to generate responses to user messages. The bot is designed to be helpful and engaging, providing assistance and conversation to users in a Discord server.

## Features

- Responds to user messages using the OpenAI API
- Supports custom functions for executing commands, searching Google, and loading websites
- Handles search results and formats them for sending to Discord
- Retries on connection failures to ensure reliability

## Installation

1. Clone the repository:
```git clone https://github.com/AiWaldoh/python-playwright-discord-openai-chatbot.git```
2. Install the required dependencies:
```poetry install```

3. Set up the necessary environment variables:
   - `BOT_NAME`: The name of your Discord bot
   - `MODEL_NAME`: The name of the OpenAI model to use
   - `API_URL`: The URL of the OpenAI API
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `ADMIN_USER_ID`: The user ID of the bot administrator
   - `SESSION_FILE`: The name of the file to store the Discord session data
   - `SYSTEM_MESSAGE`: The initial system message for the bot
   - `DISCORD_CHANNEL_URL`: The URL of the Discord channel to monitor

4. Run the bot:
```poetry run python app/botv3.py```

## Usage

Once the bot is running and connected to your Discord server, it will monitor the specified channel for new messages. When a user mentions the bot or sends a message that the bot is configured to respond to, the bot will generate a response using the OpenAI API and send it back to the Discord channel.

The bot supports the following custom functions:
- `execute_command`: Executes a specified command
- `search_google`: Searches Google for a given query and returns the results
- `load_website`: Loads a specified website URL and returns the content

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

- [OpenAI](https://openai.com/) for providing the language model API
- [Discord.py](https://discordpy.readthedocs.io/) for the Discord bot framework
- [OpenRouter](https://openrouter.io/) for the API routing service
