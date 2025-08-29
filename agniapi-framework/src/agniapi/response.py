"""
Response handling for Agni API framework.
Combines Flask and FastAPI response patterns.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from http import HTTPStatus

from werkzeug.wrappers import Response as WerkzeugResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import HTMLResponse as StarletteHTMLResponse
from starlette.responses import PlainTextResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel


class Response:
    """
    Unified response object that works with both WSGI and ASGI.
    Provides Flask and FastAPI-style interfaces.
    """
    
    def __init__(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type
        
        # Cookies to be set
        self._cookies: List[Dict[str, Any]] = []
    
    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: Optional[int] = None,
        expires: Optional[str] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None,
    ):
        """Set a cookie (Flask-style)."""
        cookie = {
            "key": key,
            "value": value,
            "max_age": max_age,
            "expires": expires,
            "path": path,
            "domain": domain,
            "secure": secure,
            "httponly": httponly,
            "samesite": samesite,
        }
        self._cookies.append(cookie)
    
    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: Optional[str] = None,
    ):
        """Delete a cookie."""
        self.set_cookie(
            key=key,
            value="",
            max_age=0,
            path=path,
            domain=domain,
        )
    
    def to_starlette_response(self) -> StarletteResponse:
        """Convert to Starlette response for ASGI."""
        if isinstance(self.content, (dict, list)):
            response = StarletteJSONResponse(
                content=self.content,
                status_code=self.status_code,
                headers=self.headers,
            )
        elif isinstance(self.content, BaseModel):
            response = StarletteJSONResponse(
                content=self.content.model_dump(),
                status_code=self.status_code,
                headers=self.headers,
            )
        else:
            response = StarletteResponse(
                content=str(self.content),
                status_code=self.status_code,
                headers=self.headers,
                media_type=self.media_type or "text/plain",
            )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response
    
    def to_werkzeug_response(self) -> WerkzeugResponse:
        """Convert to Werkzeug response for WSGI."""
        if isinstance(self.content, (dict, list)):
            content = json.dumps(self.content)
            media_type = "application/json"
        elif isinstance(self.content, BaseModel):
            content = self.content.model_dump_json()
            media_type = "application/json"
        else:
            content = str(self.content)
            media_type = self.media_type or "text/plain"
        
        response = WerkzeugResponse(
            response=content,
            status=self.status_code,
            headers=self.headers,
            mimetype=media_type,
        )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response


class JSONResponse(Response):
    """JSON response class."""
    
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="application/json",
        )
    
    def to_starlette_response(self) -> StarletteJSONResponse:
        """Convert to Starlette JSON response."""
        if isinstance(self.content, BaseModel):
            content = self.content.model_dump()
        else:
            content = self.content
        
        response = StarletteJSONResponse(
            content=content,
            status_code=self.status_code,
            headers=self.headers,
        )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response


class HTMLResponse(Response):
    """HTML response class."""
    
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html",
        )
    
    def to_starlette_response(self) -> StarletteHTMLResponse:
        """Convert to Starlette HTML response."""
        response = StarletteHTMLResponse(
            content=self.content,
            status_code=self.status_code,
            headers=self.headers,
        )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response


class PlainTextResponse(Response):
    """Plain text response class."""
    
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
        )


class RedirectResponse(Response):
    """Redirect response class."""
    
    def __init__(
        self,
        url: str,
        status_code: int = 302,
        headers: Optional[Dict[str, str]] = None,
    ):
        headers = headers or {}
        headers["location"] = url
        
        super().__init__(
            content="",
            status_code=status_code,
            headers=headers,
        )
        
        self.url = url
    
    def to_starlette_response(self) -> RedirectResponse:
        """Convert to Starlette redirect response."""
        response = RedirectResponse(
            url=self.url,
            status_code=self.status_code,
            headers=self.headers,
        )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response


class StreamingResponse(Response):
    """Streaming response class."""
    
    def __init__(
        self,
        content,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )
    
    def to_starlette_response(self) -> StreamingResponse:
        """Convert to Starlette streaming response."""
        response = StreamingResponse(
            content=self.content,
            status_code=self.status_code,
            headers=self.headers,
            media_type=self.media_type,
        )
        
        # Set cookies
        for cookie in self._cookies:
            response.set_cookie(**cookie)
        
        return response


# Utility functions for creating responses
def make_response(
    content: Any = "",
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create a response object (Flask-style)."""
    return Response(content, status_code, headers)


def jsonify(data: Any, status_code: int = 200) -> JSONResponse:
    """Create a JSON response (Flask-style)."""
    return JSONResponse(data, status_code)


def redirect(url: str, code: int = 302) -> RedirectResponse:
    """Create a redirect response (Flask-style)."""
    return RedirectResponse(url, code)


def abort(status_code: int, description: Optional[str] = None):
    """Abort with an HTTP error (Flask-style)."""
    from .exceptions import HTTPException
    
    if description is None:
        description = HTTPStatus(status_code).phrase
    
    raise HTTPException(status_code=status_code, detail=description)


# Response type hints
ResponseType = Union[
    Response,
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
    dict,
    list,
    str,
    bytes,
    BaseModel,
]
