from newspaper import Article


class ArticleParser:
    @staticmethod
    def parse(html_content):
        article = Article("")
        article.set_html(html_content)
        article.parse()
        article.nlp()

        return {
            "title": article.title,
            "text": article.text,
            "summary": article.summary,
        }
