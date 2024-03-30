import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

# Import the WebPage class and custom exceptions
from beta_v2.web_page import (
    WebPage,
    NavigationError,
    ElementNotFoundError,
    InteractionError,
)


# Fixture for creating a WebPage instance with a mocked Page object
@pytest.fixture
def web_page(mocker):
    mock_page = mocker.MagicMock(spec=Page)
    return WebPage(mock_page)


def test_navigate_success(web_page, mocker):
    url = "https://www.example.com"
    web_page.navigate(url)
    web_page.page.goto.assert_called_once_with(url, timeout=30000)


def test_navigate_failure(web_page, mocker):
    url = "https://www.example.com"
    web_page.page.goto.side_effect = PlaywrightTimeoutError("Timeout")
    with pytest.raises(NavigationError):
        web_page.navigate(url)


def test_find_element_success(web_page, mocker):
    selector = "button"
    element = mocker.MagicMock()
    web_page.page.wait_for_selector.return_value = element
    assert web_page.find_element(selector) == element
    web_page.page.wait_for_selector.assert_called_once_with(selector, timeout=10000)


def test_find_element_failure(web_page, mocker):
    selector = "button"
    web_page.page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")
    with pytest.raises(ElementNotFoundError):
        web_page.find_element(selector)


def test_find_elements_success(web_page, mocker):
    selector = "button"
    elements = [mocker.MagicMock(), mocker.MagicMock()]
    web_page.page.wait_for_selector.return_value = elements
    assert web_page.find_elements(selector) == elements
    web_page.page.wait_for_selector.assert_called_once_with(selector, timeout=10000)


def test_find_elements_failure(web_page, mocker):
    selector = "button"
    web_page.page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")
    with pytest.raises(ElementNotFoundError):
        web_page.find_elements(selector)


def test_click_success(web_page, mocker):
    selector = "button"
    element = mocker.MagicMock()
    web_page.find_element = mocker.MagicMock(return_value=element)
    web_page.click(selector)
    web_page.find_element.assert_called_once_with(selector, 10000)
    element.click.assert_called_once()


def test_click_failure(web_page, mocker):
    selector = "button"
    web_page.find_element = mocker.MagicMock(
        side_effect=ElementNotFoundError("Element not found")
    )
    with pytest.raises(InteractionError):
        web_page.click(selector)


# Similar tests for other methods like fill, get_text, wait_for_load_state, and wait_for_selector
