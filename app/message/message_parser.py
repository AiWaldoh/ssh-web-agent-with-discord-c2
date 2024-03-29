from bs4 import BeautifulSoup
from config.config import Config
import re
from api.chat_api_handler import ChatAPIHandler


class MessageParser:
    def __init__(self, api_handler):
        self.api_handler: ChatAPIHandler = api_handler

    def on_message_received(self, message_html):
        if not self._is_valid_message(message_html):
            return

        message_soup = BeautifulSoup(message_html, "html.parser")
        message_data = self._parse_message(message_soup)

        if message_data["has_mention"]:
            print(f"has_mention: {message_data['has_mention']}")
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
