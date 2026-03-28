"""Healthie GraphQL API client."""

from __future__ import annotations

import os

import httpx
from loguru import logger

STAGING_API_URL = "https://staging-api.gethealthie.com/graphql"


class HealthieApiClient:
    """Wraps httpx.AsyncClient for Healthie GraphQL API calls."""

    def __init__(self) -> None:
        api_key = os.environ.get("HEALTHIE_API_KEY")
        if not api_key:
            raise ValueError("HEALTHIE_API_KEY must be set in environment variables")

        self._headers = {
            "Authorization": f"Basic {api_key}",
            "AuthorizationSource": "API",
            "Content-Type": "application/json",
        }
        self._http = httpx.AsyncClient(
            base_url=STAGING_API_URL,
            headers=self._headers,
            timeout=30.0,
        )
        self.patient_cache: dict[str, str] = {}

    async def execute(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query/mutation and return the response data.

        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self._http.post("", json=payload)
        response.raise_for_status()

        body = response.json()
        if "errors" in body:
            logger.error(f"GraphQL errors: {body['errors']}")
            raise RuntimeError(f"GraphQL errors: {body['errors']}")

        return body.get("data", {})

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_client: HealthieApiClient | None = None


async def get_client() -> HealthieApiClient:
    """Return the module-level singleton client, creating it if needed."""
    global _client
    if _client is None:
        _client = HealthieApiClient()
    return _client
