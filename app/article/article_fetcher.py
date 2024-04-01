from requests.models import Response
from curl_cffi import requests


class ArticleFetcher:
    @staticmethod
    def fetch_content(url):
        r: Response = requests.get(url, impersonate="chrome120")
        return r.content
