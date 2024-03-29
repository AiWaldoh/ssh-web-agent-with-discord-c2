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

        return parsed_data
