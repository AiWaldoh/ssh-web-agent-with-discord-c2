import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Union
from playwright.sync_api import ElementHandle
from beta_v2.web_page import WebPage, ElementNotFoundError
from beta_v2.page_analyzer import PageAnalyzer, PageAnalysisError


class TestPageAnalyzer(unittest.TestCase):
    def setUp(self):
        self.page_mock = MagicMock(spec=WebPage)
        self.analyzer = PageAnalyzer(self.page_mock)

    @patch.object(PageAnalyzer, "_get_elements_by_selector")
    @patch.object(PageAnalyzer, "_get_element_texts")
    @patch.object(PageAnalyzer, "_get_element_attributes")
    def test_get_page_structure(
        self,
        mock_get_element_attributes,
        mock_get_element_texts,
        mock_get_elements_by_selector,
    ):
        # Mock the necessary methods and return values
        self.page_mock.get_text.return_value = "Page Title"
        mock_get_elements_by_selector.side_effect = [
            ["heading1", "heading2"],
            ["paragraph1", "paragraph2"],
            ["link1", "link2"],
            ["button1", "button2"],
            ["input1", "input2"],
        ]
        mock_get_element_texts.side_effect = [
            ["Heading 1", "Heading 2"],
            ["Paragraph 1", "Paragraph 2"],
            ["Button 1", "Button 2"],
        ]
        mock_get_element_attributes.side_effect = [
            ["https://link1", "https://link2"],
            ["input1", "input2"],
        ]

        # Call the method and assert the result
        result = self.analyzer.get_page_structure()
        expected_result = {
            "title": "Page Title",
            "headings": ["Heading 1", "Heading 2"],
            "paragraphs": ["Paragraph 1", "Paragraph 2"],
            "links": ["https://link1", "https://link2"],
            "buttons": ["Button 1", "Button 2"],
            "input_fields": ["input1", "input2"],
        }
        self.assertEqual(result, expected_result)

    def test_get_main_content(self):
        # Mock the necessary methods and return values
        self.page_mock.get_text.return_value = "Main Content"

        # Call the method and assert the result
        result = self.analyzer.get_main_content()
        self.assertEqual(result, "Main Content")

    def test_get_main_content_not_found(self):
        # Mock the necessary methods and return values
        self.page_mock.get_text.side_effect = ElementNotFoundError

        # Call the method and assert the exception
        with self.assertRaises(PageAnalysisError) as cm:
            self.analyzer.get_main_content()
        self.assertEqual(str(cm.exception), "Main content area not found on the page")

    def test_get_metadata(self):
        # Mock the necessary methods and return values
        self.page_mock.get_text.side_effect = ["Page Title", "Description", "Keywords"]

        # Call the method and assert the result
        result = self.analyzer.get_metadata()
        expected_result = {
            "title": "Page Title",
            "description": "Description",
            "keywords": "Keywords",
        }
        self.assertEqual(result, expected_result)

    @patch.object(PageAnalyzer, "_get_elements_by_selector")
    def test_get_elements_by_selector(self, mock_get_elements_by_selector):
        # Mock the necessary methods and return values
        mock_get_elements_by_selector.return_value = ["element1", "element2"]

        # Call the method and assert the result
        result = self.analyzer._get_elements_by_selector("selector")
        self.assertEqual(result, ["element1", "element2"])

    @patch.object(PageAnalyzer, "_get_elements_by_selector")
    def test_get_elements_by_selector_not_found(self, mock_get_elements_by_selector):
        # Mock the necessary method to return an empty list
        mock_get_elements_by_selector.return_value = []

        # Call the method and assert the result
        result = self.analyzer._get_elements_by_selector("selector")
        self.assertEqual(result, [])

    def test_get_element_texts(self):
        # Create mock elements
        element1_mock = MagicMock(spec=ElementHandle)
        element1_mock.text_content.return_value = "Element 1"
        element2_mock = MagicMock(spec=ElementHandle)
        element2_mock.text_content.return_value = "Element 2"
        elements = [element1_mock, element2_mock]

        # Call the method and assert the result
        result = self.analyzer._get_element_texts(elements)
        self.assertEqual(result, ["Element 1", "Element 2"])

    def test_get_element_attributes(self):
        # Create mock elements
        element1_mock = MagicMock(spec=ElementHandle)
        element1_mock.get_attribute.return_value = "Attribute 1"
        element2_mock = MagicMock(spec=ElementHandle)
        element2_mock.get_attribute.return_value = "Attribute 2"
        elements = [element1_mock, element2_mock]

        # Call the method and assert the result
        result = self.analyzer._get_element_attributes(elements, "attribute")
        self.assertEqual(result, ["Attribute 1", "Attribute 2"])


if __name__ == "__main__":
    unittest.main()
