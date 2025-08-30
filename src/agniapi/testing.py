"""
Testing utilities for Agni API framework.
Provides test client and testing helpers for both sync and async testing.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

import httpx
from starlette.testclient import TestClient as StarletteTestClient

from .app import AgniAPI
from .request import Request
from .response import Response


class TestClient:
    """
    Test client for Agni API applications.
    Supports both sync and async testing patterns.
    """
    
    def __init__(
        self,
        app: AgniAPI,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
    ):
        self.app = app
        self.base_url = base_url
        self.raise_server_exceptions = raise_server_exceptions
        self.root_path = root_path
        
        # Create underlying test clients
        self._starlette_client = StarletteTestClient(
            app,  # Use the AgniAPI app directly, not the internal Starlette app
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
        )
        
        # For async testing
        self._async_client: Optional[httpx.AsyncClient] = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.aclose()
    
    def close(self):
        """Close the test client."""
        if self._starlette_client:
            self._starlette_client.close()
    
    async def aclose(self):
        """Close the async test client."""
        if self._async_client:
            await self._async_client.aclose()
    
    # Synchronous HTTP methods
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a GET request."""
        return self._starlette_client.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a POST request."""
        return self._starlette_client.post(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a PUT request."""
        return self._starlette_client.put(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def patch(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a PATCH request."""
        return self._starlette_client.patch(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a DELETE request."""
        return self._starlette_client.delete(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def options(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an OPTIONS request."""
        return self._starlette_client.options(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    def head(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make a HEAD request."""
        return self._starlette_client.head(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    # Asynchronous HTTP methods
    async def aget(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an async GET request."""
        client = await self._get_async_client()
        return await client.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    async def apost(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an async POST request."""
        client = await self._get_async_client()
        return await client.post(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    async def aput(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an async PUT request."""
        client = await self._get_async_client()
        return await client.put(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    async def apatch(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an async PATCH request."""
        client = await self._get_async_client()
        return await client.patch(
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    async def adelete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        follow_redirects: bool = False,
        **kwargs
    ) -> httpx.Response:
        """Make an async DELETE request."""
        client = await self._get_async_client()
        return await client.delete(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            **kwargs
        )
    
    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async client."""
        if self._async_client is None:
            # Use httpx with ASGI transport for async testing
            from httpx import ASGITransport
            transport = ASGITransport(app=self.app)
            self._async_client = httpx.AsyncClient(
                transport=transport,
                base_url=self.base_url,
            )
        return self._async_client
    
    # WebSocket testing
    def websocket_connect(
        self,
        url: str,
        subprotocols: Optional[List[str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
    ):
        """Connect to a WebSocket endpoint."""
        return self._starlette_client.websocket_connect(
            url,
            subprotocols=subprotocols,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
        )
    
    # Utility methods
    def set_cookies(self, cookies: Dict[str, str]):
        """Set cookies for subsequent requests."""
        self._starlette_client.cookies.update(cookies)
    
    def clear_cookies(self):
        """Clear all cookies."""
        self._starlette_client.cookies.clear()
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current cookies."""
        return dict(self._starlette_client.cookies)


# Testing utilities and fixtures
class TestResponse:
    """Enhanced response object for testing."""
    
    def __init__(self, response: httpx.Response):
        self._response = response
    
    @property
    def status_code(self) -> int:
        """Response status code."""
        return self._response.status_code
    
    @property
    def headers(self) -> Dict[str, str]:
        """Response headers."""
        return dict(self._response.headers)
    
    @property
    def content(self) -> bytes:
        """Response content as bytes."""
        return self._response.content
    
    @property
    def text(self) -> str:
        """Response content as text."""
        return self._response.text
    
    def json(self) -> Any:
        """Response content as JSON."""
        return self._response.json()
    
    @property
    def cookies(self) -> Dict[str, str]:
        """Response cookies."""
        return dict(self._response.cookies)
    
    def assert_status_code(self, expected: int):
        """Assert response status code."""
        assert self.status_code == expected, f"Expected {expected}, got {self.status_code}"
    
    def assert_json_contains(self, expected: Dict[str, Any]):
        """Assert JSON response contains expected data."""
        actual = self.json()
        for key, value in expected.items():
            assert key in actual, f"Key '{key}' not found in response"
            assert actual[key] == value, f"Expected {value}, got {actual[key]} for key '{key}'"
    
    def assert_header_present(self, header: str):
        """Assert header is present."""
        assert header.lower() in [h.lower() for h in self.headers], f"Header '{header}' not found"
    
    def assert_header_equals(self, header: str, expected: str):
        """Assert header equals expected value."""
        actual = self.headers.get(header)
        assert actual == expected, f"Expected '{expected}', got '{actual}' for header '{header}'"


def create_test_client(app: AgniAPI, **kwargs) -> TestClient:
    """Create a test client for an Agni API application."""
    return TestClient(app, **kwargs)
