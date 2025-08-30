"""
Streaming responses and Server-Sent Events (SSE) for AgniAPI.

This module provides comprehensive streaming capabilities including:
- Large file streaming
- Server-Sent Events (SSE) support
- Real-time event streaming
- Chunked transfer encoding
- Async generators for streaming data
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Generator, Iterator, Optional, Union
from datetime import datetime

from .response import Response
from .exceptions import HTTPException


class StreamingResponse(Response):
    """Response class for streaming content."""

    def __init__(
        self,
        content: Union[AsyncIterator[bytes], Iterator[bytes], AsyncGenerator[bytes, None], Generator[bytes, None, None]],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background=None,
    ):
        super().__init__(content=None, status_code=status_code, headers=headers, media_type=media_type)
        self.body_iterator = content
        self.background = background
    
    async def __call__(self, scope, receive, send):
        """ASGI application interface for streaming response."""
        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': self.raw_headers,
        })
        
        if hasattr(self.body_iterator, '__aiter__'):
            # Async iterator
            async for chunk in self.body_iterator:
                if chunk:
                    await send({
                        'type': 'http.response.body',
                        'body': chunk,
                        'more_body': True,
                    })
        else:
            # Sync iterator - run in thread pool
            import concurrent.futures
            
            def sync_iterator():
                for chunk in self.body_iterator:
                    yield chunk
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for chunk in sync_iterator():
                    if chunk:
                        await send({
                            'type': 'http.response.body',
                            'body': chunk,
                            'more_body': True,
                        })
        
        # Send final empty body to signal end
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })


class ServerSentEvent:
    """Server-Sent Event data structure."""
    
    def __init__(
        self,
        data: Any,
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
        comment: Optional[str] = None,
    ):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment
    
    def encode(self) -> bytes:
        """Encode the event as SSE format."""
        lines = []
        
        if self.comment:
            for line in self.comment.split('\n'):
                lines.append(f": {line}")
        
        if self.event:
            lines.append(f"event: {self.event}")
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # Handle data
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)
        
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        # Add double newline to separate events
        lines.append('')
        lines.append('')
        
        return '\n'.join(lines).encode('utf-8')


class SSEResponse(StreamingResponse):
    """Server-Sent Events response."""
    
    def __init__(
        self,
        generator: Union[AsyncGenerator[ServerSentEvent, None], Generator[ServerSentEvent, None, None]],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        ping_interval: Optional[int] = None,
    ):
        # Set SSE headers
        sse_headers = {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control',
        }
        
        if headers:
            sse_headers.update(headers)
        
        # Convert SSE generator to bytes generator
        if hasattr(generator, '__aiter__'):
            content_generator = self._async_sse_generator(generator, ping_interval)
        else:
            content_generator = self._sync_sse_generator(generator, ping_interval)
        
        super().__init__(
            content=content_generator,
            status_code=status_code,
            headers=sse_headers,
            media_type='text/event-stream'
        )
    
    async def _async_sse_generator(
        self,
        generator: AsyncGenerator[ServerSentEvent, None],
        ping_interval: Optional[int]
    ) -> AsyncGenerator[bytes, None]:
        """Convert async SSE generator to bytes generator."""
        last_ping = asyncio.get_event_loop().time()
        
        async for event in generator:
            yield event.encode()
            
            # Send ping if interval specified
            if ping_interval:
                current_time = asyncio.get_event_loop().time()
                if current_time - last_ping >= ping_interval:
                    ping_event = ServerSentEvent(data='ping', event='ping')
                    yield ping_event.encode()
                    last_ping = current_time
    
    def _sync_sse_generator(
        self,
        generator: Generator[ServerSentEvent, None, None],
        ping_interval: Optional[int]
    ) -> Generator[bytes, None, None]:
        """Convert sync SSE generator to bytes generator."""
        import time
        last_ping = time.time()
        
        for event in generator:
            yield event.encode()
            
            # Send ping if interval specified
            if ping_interval:
                current_time = time.time()
                if current_time - last_ping >= ping_interval:
                    ping_event = ServerSentEvent(data='ping', event='ping')
                    yield ping_event.encode()
                    last_ping = current_time


class FileStreamingResponse(StreamingResponse):
    """Response for streaming large files."""
    
    def __init__(
        self,
        path: Union[str, Path],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
        chunk_size: int = 8192,
    ):
        self.path = Path(path)
        self.chunk_size = chunk_size
        
        if not self.path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not self.path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Determine media type
        if media_type is None:
            media_type, _ = mimetypes.guess_type(str(self.path))
            if media_type is None:
                media_type = 'application/octet-stream'
        
        # Set up headers
        file_headers = {
            'Content-Length': str(self.path.stat().st_size),
            'Last-Modified': datetime.fromtimestamp(self.path.stat().st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT'),
        }
        
        if filename:
            file_headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        if headers:
            file_headers.update(headers)
        
        super().__init__(
            content=self._file_generator(),
            status_code=status_code,
            headers=file_headers,
            media_type=media_type
        )
    
    async def _file_generator(self) -> AsyncGenerator[bytes, None]:
        """Generate file chunks asynchronously."""
        # Use thread pool for file operations
        import concurrent.futures

        def read_chunk(file_obj):
            return file_obj.read(self.chunk_size)

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            with open(self.path, 'rb') as file:
                while True:
                    chunk = await loop.run_in_executor(executor, read_chunk, file)
                    if not chunk:
                        break
                    yield chunk


def stream_file(
    path: Union[str, Path],
    chunk_size: int = 8192,
    headers: Optional[Dict[str, str]] = None,
    media_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> FileStreamingResponse:
    """
    Stream a file as a response.
    
    Args:
        path: Path to the file to stream
        chunk_size: Size of chunks to read at a time
        headers: Additional headers to include
        media_type: MIME type of the file
        filename: Filename for Content-Disposition header
        
    Returns:
        FileStreamingResponse object
    """
    return FileStreamingResponse(
        path=path,
        chunk_size=chunk_size,
        headers=headers,
        media_type=media_type,
        filename=filename,
    )


def stream_response(
    generator: Union[AsyncGenerator[bytes, None], Generator[bytes, None, None]],
    media_type: str = 'application/octet-stream',
    headers: Optional[Dict[str, str]] = None,
) -> StreamingResponse:
    """
    Create a streaming response from a generator.
    
    Args:
        generator: Generator that yields bytes
        media_type: MIME type of the content
        headers: Additional headers to include
        
    Returns:
        StreamingResponse object
    """
    return StreamingResponse(
        content=generator,
        media_type=media_type,
        headers=headers,
    )


def sse_response(
    generator: Union[AsyncGenerator[ServerSentEvent, None], Generator[ServerSentEvent, None, None]],
    headers: Optional[Dict[str, str]] = None,
    ping_interval: Optional[int] = None,
) -> SSEResponse:
    """
    Create a Server-Sent Events response.
    
    Args:
        generator: Generator that yields ServerSentEvent objects
        headers: Additional headers to include
        ping_interval: Interval in seconds to send ping events
        
    Returns:
        SSEResponse object
    """
    return SSEResponse(
        generator=generator,
        headers=headers,
        ping_interval=ping_interval,
    )


# Utility functions for common streaming patterns
async def stream_json_array(
    items: AsyncIterator[Any],
    chunk_size: int = 100,
) -> AsyncGenerator[bytes, None]:
    """Stream a JSON array of items."""
    yield b'['
    
    first = True
    buffer = []
    
    async for item in items:
        if not first:
            buffer.append(',')
        else:
            first = False
        
        buffer.append(json.dumps(item))
        
        if len(buffer) >= chunk_size:
            yield ''.join(buffer).encode('utf-8')
            buffer = []
    
    if buffer:
        yield ''.join(buffer).encode('utf-8')
    
    yield b']'


async def stream_csv_rows(
    rows: AsyncIterator[Dict[str, Any]],
    fieldnames: Optional[list[str]] = None,
) -> AsyncGenerator[bytes, None]:
    """Stream CSV data row by row."""
    import csv
    from io import StringIO
    
    first_row = True
    
    async for row in rows:
        if first_row:
            if fieldnames is None:
                fieldnames = list(row.keys())
            
            # Write header
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            yield output.getvalue().encode('utf-8')
            first_row = False
        
        # Write row
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writerow(row)
        yield output.getvalue().encode('utf-8')


def create_sse_event(
    data: Any,
    event: Optional[str] = None,
    id: Optional[str] = None,
    retry: Optional[int] = None,
) -> ServerSentEvent:
    """Create a Server-Sent Event."""
    return ServerSentEvent(data=data, event=event, id=id, retry=retry)
