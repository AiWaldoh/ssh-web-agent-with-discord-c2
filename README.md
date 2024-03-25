# Discord OpenAI Self-Bot

This is a simple Discord self-bot that allows you to chat with OpenAI's language model directly in a Discord channel. The bot uses a custom prompt to provide an engaging and fun conversational experience.

## Features

- Integrates with OpenAI's API to generate responses based on your messages
- Supports custom prompts to personalize the chatbot's behavior
- Maintains conversation history for context-aware responses
- Easy to set up and run

## Prerequisites

Before running the bot, make sure you have the following:

- Python 3.x installed
- Discord account
- OpenAI API key

## Installation

1. Clone the repository:
```
git clone https://github.com/AiWaldoh/python-playwright-discord-openai-chatbot
```

2. Navigate to the project directory:
```
cd python-playwright-discord-openai-chatbot
```

3. Install the required dependencies using poetry:
```
poetry install
```

4. Create a .env file from .env.example in the project root and add your Discord account credentials and OpenAI API key:
```
DISCORD_EMAIL=your-discord-email
DISCORD_PASSWORD=your-discord-password
DISCORD_CHANNEL_URL=your-discord-channel-url
OPENROUTER_API_KEY=your-openai-api-key
INITIAL_SYSTEM_MESSAGE=your-initial-system-message
COOKIE_FILE_NAME="discord_session.json"
BOT_NAME=your-bot-name
```

## Usage

1. Run the self-bot:
```
poetry run python3 app/run.py
```

2. The self-bot will automatically log in to a Discord account.

3. In a Discord channel, mention the self-bot's name and type your message to start a conversation. For example:
@YourSelfBotName Hello! How are you doing?

4. The self-bot will respond to your message based on the custom prompt and the conversation history.

## Customization

To customize the chatbot's behavior, you can modify the INITIAL_SYSTEM_MESSAGE variable in the .env file. This variable defines the initial prompt that sets the context and personality of the chatbot.

For example, you can set it to:
```
INITIAL_SYSTEM_MESSAGE=You are a friendly and witty chatbot. Engage in fun and humorous conversations with users.
```

## Disclaimer

Please note that using a self-bot on Discord is against Discord's Terms of Service. Use this self-bot at your own risk. The developers are not responsible for any consequences that may arise from using this self-bot.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).