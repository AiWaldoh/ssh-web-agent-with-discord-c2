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
        url = "https://openrouter.ai/api/v1/chat/completions"
        data = {
            "messages": [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ],
            "model": self.model_name,
            "temperature": self.temperature,
            "tools": tools,
        }
        if config:
            data.update(config)

        response = self.http_client.post(url, data)
        return response


class ResponseProcessor:
    def process(self, api_response, max_length=1900):
        response_text = api_response["response"]
        return [
            response_text[i : i + max_length]
            for i in range(0, len(response_text), max_length)
        ]
