"""Read-only client for Kalshi's public market-data API."""

from typing import Any

import httpx

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiClient:
    """Retrieve public market data without trading credentials."""

    def __init__(self, timeout: float = 15.0) -> None:
        """
        Initialize the client configuration.

        Parameters
        ----------
        timeout:
            Maximum number of seconds to wait for a request.

        This constructor does not contact the API.
        """
        self.timeout = timeout

    def get_markets(
        self,
        status: str = "settled",
        limit: int = 200,
        mve_filter: str = "exclude",
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve one page of Kalshi markets."""
        if status not in {"open", "closed", "settled"}:
            raise ValueError("Unsupported market status.")

        if not 1 <= limit <= 1000:
            raise ValueError("Limit must be between 1 and 1000.")

        if mve_filter not in {"exclude", "only"}:
            raise ValueError("Unsupported multivariate filter.")

        params = {
            "status": status,
            "limit": limit,
            "mve_filter": mve_filter,
        }

        if cursor is not None:
            params["cursor"] = cursor

        with httpx.Client(
            base_url=BASE_URL,
            timeout=self.timeout,
        ) as client:
            response = client.get("/markets", params=params)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("Expected a JSON object.")

        if not isinstance(payload.get("markets"), list):
            raise TypeError("Response is missing a markets list.")

        return payload
