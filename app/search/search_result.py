from article.article_fetcher import ArticleFetcher
from article.article_parser import ArticleParser


class SearchResult:
    def __init__(self, title, url, description):
        self.title = title
        self.url = url
        self.description = description
        self.article_content = None
        self.article_summary = None
        self.article_full_text = None

    def fetch_and_parse_article(self):
        html_content = ArticleFetcher.fetch_content(self.url)
        parsed_data = ArticleParser.parse(html_content)
        self.article_content = parsed_data["title"]
        self.article_full_text = parsed_data["text"]
        self.article_summary = parsed_data["summary"]

    def display(self):
        print(f"Title: {self.title}")
        print(f"URL: {self.url}")
        print(f"Description: {self.description}")
        if self.article_content:
            print(f"Article Title (from newspaper3k): {self.article_content}")
            print(f"\nFull Text:\n{self.article_full_text}")
            print(f"\nSummary:\n{self.article_summary}")
        print("------")
