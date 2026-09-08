"""
Kaivor HTTP Client
"""

import requests


class HTTPClient:
    """Simple HTTP client."""

    @staticmethod
    def post(url, headers=None, json=None, timeout=60):
        response = requests.post(
            url,
            headers=headers,
            json=json,
            timeout=timeout,
        )

        response.raise_for_status()

        return response.json()
