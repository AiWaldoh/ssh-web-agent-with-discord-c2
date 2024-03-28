import requests


class HttpClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, url, data):
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        return response.json()
