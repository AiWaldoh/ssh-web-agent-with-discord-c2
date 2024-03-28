import urllib.parse


class UrlEncoder:
    @staticmethod
    def encode(url):
        return urllib.parse.quote_plus(url)
