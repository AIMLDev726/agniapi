"""
Static file serving for Agni API framework.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional

from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .exceptions import HTTPException


class StaticFiles(StarletteStaticFiles):
    """
    Static file serving with enhanced features.
    Compatible with Starlette's StaticFiles but with additional functionality.
    """
    
    def __init__(
        self,
        directory: str,
        packages: Optional[list] = None,
        html: bool = False,
        check_dir: bool = True,
    ):
        """
        Initialize static file handler.
        
        Args:
            directory: Directory to serve files from
            packages: List of packages to serve files from
            html: Whether to serve HTML files
            check_dir: Whether to check if directory exists
        """
        super().__init__(
            directory=directory,
            packages=packages,
            html=html,
            check_dir=check_dir,
        )


def send_file(
    path: str,
    mimetype: Optional[str] = None,
    as_attachment: bool = False,
    download_name: Optional[str] = None,
    conditional: bool = True,
    etag: bool = True,
    last_modified: Optional[bool] = None,
    max_age: Optional[int] = None,
) -> FileResponse:
    """
    Send a file to the client.
    
    Args:
        path: Path to the file
        mimetype: MIME type of the file
        as_attachment: Whether to send as attachment
        download_name: Name for download
        conditional: Whether to support conditional requests
        etag: Whether to include ETag header
        last_modified: Whether to include Last-Modified header
        max_age: Cache max age in seconds
    
    Returns:
        FileResponse object
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if mimetype is None:
        mimetype, _ = mimetypes.guess_type(path)
    
    headers = {}
    if as_attachment and download_name:
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    
    return FileResponse(
        path=path,
        media_type=mimetype,
        headers=headers,
    )


def send_from_directory(
    directory: str,
    filename: str,
    **kwargs
) -> FileResponse:
    """
    Send a file from a directory.
    
    Args:
        directory: Directory containing the file
        filename: Name of the file
        **kwargs: Additional arguments for send_file
    
    Returns:
        FileResponse object
    """
    path = os.path.join(directory, filename)
    
    # Security check - ensure file is within directory
    directory = os.path.abspath(directory)
    path = os.path.abspath(path)
    
    if not path.startswith(directory):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return send_file(path, **kwargs)
