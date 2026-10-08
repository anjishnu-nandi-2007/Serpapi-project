import logging
from typing import Any, Dict, Optional
import httpx

from app.config import settings

logger = logging.getLogger("gontobbo.serpapi")


class SerpApiError(Exception):
    """Base exception for SerpApi communication errors."""

    def __init__(self, message: str, code: str = "SERPAPI_ERROR", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class SerpApiConfigError(SerpApiError):
    """Raised when the SerpApi API key is missing."""

    def __init__(self, message: str = "SerpApi API key is not configured on the server."):
        super().__init__(message, code="MISSING_API_KEY", status_code=500)


class SerpApiTimeoutError(SerpApiError):
    """Raised when a request to SerpApi times out."""

    def __init__(self, message: str = "Search request timed out while communicating with upstream service."):
        super().__init__(message, code="UPSTREAM_TIMEOUT", status_code=504)


_async_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or initialize the shared AsyncClient."""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _async_client


async def close_http_client() -> None:
    """Close the shared AsyncClient upon application shutdown."""
    global _async_client
    if _async_client is not None and not _async_client.is_closed:
        await _async_client.aclose()
        _async_client = None


async def serpapi_search(params: Dict[str, Any], client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """
    Execute a query against the SerpApi search endpoint.

    Parameters:
        params: Query parameters including 'engine' (e.g., 'google_hotels', 'google_flights')
        client: Optional custom or mocked AsyncClient for testing

    Returns:
        Parsed JSON dictionary response from SerpApi.
    """
    api_key = settings.SERPAPI_API_KEY
    if not api_key:
        logger.error("Attempted SerpApi search without configured SERPAPI_API_KEY.")
        raise SerpApiConfigError()

    # Create request params with API key, ensuring original dict is not mutated
    request_params = {**params, "api_key": api_key, "output": "json"}

    # Sanitize params for safe logging (strip api_key)
    safe_params = {k: v for k, v in params.items() if k.lower() != "api_key"}
    engine = params.get("engine", "unknown")
    logger.info("Sending SerpApi request: engine=%s, params=%s", engine, safe_params)

    http_client = client or get_http_client()

    try:
        response = await http_client.get(
            settings.SERPAPI_BASE_URL,
            params=request_params,
        )
    except httpx.TimeoutException as exc:
        logger.error("SerpApi request timed out for engine %s: %s", engine, type(exc).__name__)
        raise SerpApiTimeoutError() from exc
    except httpx.RequestError as exc:
        logger.error("SerpApi network communication error for engine %s: %s", engine, type(exc).__name__)
        raise SerpApiError(
            message=f"Failed to communicate with SerpApi search service: {type(exc).__name__}",
            code="NETWORK_ERROR",
            status_code=502,
        ) from exc

    try:
        data = response.json()
    except Exception as exc:
        logger.error("Malformed non-JSON response from SerpApi (HTTP %s)", response.status_code)
        raise SerpApiError(
            message="Received malformed non-JSON response from SerpApi upstream.",
            code="MALFORMED_RESPONSE",
            status_code=502,
        ) from exc

    # Check for SerpApi application-level errors
    if isinstance(data, dict) and "error" in data:
        err_msg = str(data["error"])
        logger.warning("SerpApi upstream reported an error: %s", err_msg)
        raise SerpApiError(
            message=f"SerpApi query error: {err_msg}",
            code="SERPAPI_UPSTREAM_ERROR",
            status_code=400 if response.status_code < 500 else 502,
        )

    if response.status_code >= 400:
        logger.error("SerpApi returned HTTP error status %s", response.status_code)
        raise SerpApiError(
            message=f"Upstream search service returned HTTP status {response.status_code}.",
            code="UPSTREAM_HTTP_ERROR",
            status_code=response.status_code if response.status_code in (400, 404, 429) else 502,
        )

    return data
