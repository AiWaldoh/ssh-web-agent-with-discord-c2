from typing import List, Dict
from .web_page import WebPage


class PageAnalyzer:
    def __init__(self, web_page: WebPage):
        self.web_page = web_page

    def get_page_title(self) -> str:
        return self.web_page.page.title()

    def get_headings(self) -> List[Dict[str, str]]:
        headings = []
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            elements = self.web_page.page.query_selector_all(tag)
            for element in elements:
                headings.append({"tag": tag, "text": element.text_content()})
        return headings

    def get_paragraphs(self) -> List[str]:
        paragraphs = []
        elements = self.web_page.page.query_selector_all("p")
        for element in elements:
            paragraphs.append(element.text_content())
        return paragraphs

    def get_links(self) -> List[Dict[str, str]]:
        links = []
        elements = self.web_page.page.query_selector_all("a")
        for element in elements:
            links.append(
                {"url": element.get_attribute("href"), "text": element.text_content()}
            )
        return links

    def get_input_fields(self) -> List[Dict[str, str]]:
        input_fields = []
        elements = self.web_page.page.query_selector_all("input")
        for element in elements:
            input_fields.append(
                {
                    "type": element.get_attribute("type"),
                    "name": element.get_attribute("name"),
                }
            )
        return input_fields

    def get_buttons(self) -> List[str]:
        buttons = []
        elements = self.web_page.page.query_selector_all("button")
        for element in elements:
            buttons.append(element.text_content())
        return buttons

    def get_meta_description(self) -> str:
        meta_element = self.web_page.page.query_selector('meta[name="description"]')
        if meta_element:
            return meta_element.get_attribute("content")
        return ""

    def get_meta_keywords(self) -> List[str]:
        meta_element = self.web_page.page.query_selector('meta[name="keywords"]')
        if meta_element:
            content = meta_element.get_attribute("content")
            return content.split(",")
        return []

    def get_page_text(self) -> str:
        return self.web_page.page.text_content()

    def get_images(self) -> List[str]:
        images = []
        elements = self.web_page.page.query_selector_all("img")
        for element in elements:
            images.append(element.get_attribute("src"))
        return images

    def get_css_classes(self) -> List[str]:
        classes = []
        elements = self.web_page.page.query_selector_all("*")
        for element in elements:
            class_attr = element.get_attribute("class")
            if class_attr:
                classes.extend(class_attr.split())
        return list(set(classes))

    def get_css_ids(self) -> List[str]:
        ids = []
        elements = self.web_page.page.query_selector_all("*")
        for element in elements:
            id_attr = element.get_attribute("id")
            if id_attr:
                ids.append(id_attr)
        return list(set(ids))

    def get_javascript_events(self) -> List[str]:
        events = []
        elements = self.web_page.page.query_selector_all("*")
        for element in elements:
            event_handlers = element.get_property("__events__")
            if event_handlers:
                events.extend(event_handlers.json_value())
        return list(set(events))
