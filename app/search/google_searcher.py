from requests.models import Response
from curl_cffi import requests
from bs4 import BeautifulSoup
from search.search_result import SearchResult

import urllib.parse


class UrlEncoder:
    @staticmethod
    def encode(url):
        return urllib.parse.quote_plus(url)


class GoogleSearcher:
    @staticmethod
    def search(query, num_results=20, limit=3):
        query = UrlEncoder.encode(query)
        r: Response = requests.get(
            f"https://www.google.com/search?q={query}&num={num_results}",
            impersonate="chrome120",
        )
        soup = BeautifulSoup(r.content, "html.parser")
        results = soup.find_all("div", class_="tF2Cxc")
        search_results = []
        for result in results:
            title_element = result.find("h3", class_="LC20lb")
            link_element = result.find("a", href=True)
            description_element = result.find("div", class_="VwiC3b")

            title = title_element.text if title_element else None
            link = link_element["href"] if link_element else None
            description = description_element.text if description_element else None

            if link and (link.startswith("http://") or link.startswith("https://")):
                search_results.append(SearchResult(title, link, description))

        return search_results[:limit]
