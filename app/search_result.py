from curl_cffi import requests
from bs4 import BeautifulSoup
from newspaper import Article
from requests.models import Response
import urllib.parse


def url_encode_string(s):
    return urllib.parse.quote_plus(s)


def fetch_google_search_results(query, num_results=20):
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

    return search_results


def fetch_article_content(url):
    """Fetch the content of the given URL using curl_cffi."""
    r: Response = requests.get(url, impersonate="chrome101")
    return r.content


def function_calling_search_and_load_website(API_KEY, query):
    # Step 1: Define the available functions for GPT to consider
    functions = [
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
            "description": "Load a website URL and provide a summary or its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "website_url": {
                        "type": "string",
                        "description": "The URL of the website to load.",
                    }
                },
                "required": ["website_url"],
            },
        },
    ]

    # Step 2: Send the conversation and available functions to GPT
    openai.api_key = API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[{"role": "system", "content": query}],
        functions=functions,
        function_call="auto",  # auto is default, but we'll be explicit
    )
    response_message = response["choices"][0]["message"]
    return response_message


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
