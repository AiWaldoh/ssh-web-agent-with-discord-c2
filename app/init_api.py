import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import yaml
from enum import Enum
from dataclasses import dataclass
from typing import List
import subprocess
from abc import ABC, abstractmethod
import asyncio
from playwright.async_api import async_playwright
import json


class HttpClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def post(self, url, data):
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            print(f"Error occurred during API call: {str(e)}")
            return None


class ChatAPIService:
    def __init__(self, api_key, model_name="gpt-3.5-turbo", temperature=1.0):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.http_client = HttpClient(api_key)

    def execute_api_call(self, messages, tools, config=None):

        # print(f"all variables: {messages}, {tools}, {config}")
        url = "https://openrouter.ai/api/v1/chat/completions"
        data = {
            "messages": [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ],
            "model": self.model_name,
            "temperature": self.temperature,
            "tools": tools,
        }
        print(f"data: {data}")
        # this was to update model name with the one from config or api url
        # if config:
        #     data.update(config)
        # print(f"after config")

        response = self.http_client.post(url, data)
        # print(f"response: {response}")
        return response
