"""
Form handling and file upload support for AgniAPI.

This module provides comprehensive form handling capabilities including:
- File uploads with UploadFile class
- Form validation with WTForms integration
- Multipart form data parsing
- FastAPI-style Form() dependency injection
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO, AsyncGenerator
from pathlib import Path

from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile as StarletteUploadFile
try:
    from starlette.formparsers import FormParser, MultiPartParser
    from starlette.requests import Request as StarletteRequest
    STARLETTE_AVAILABLE = True
except ImportError:
    STARLETTE_AVAILABLE = False
    # Fallback implementations will be provided


class UploadFile:
    """
    File upload wrapper that provides both sync and async file operations.
    Compatible with FastAPI's UploadFile but with enhanced features.
    """
    
    def __init__(
        self,
        file: BinaryIO,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        size: Optional[int] = None,
    ):
        self.file = file
        self.filename = filename
        self.content_type = content_type
        self.headers = headers or {}
        self.size = size
        self._file_position = 0
    
    @classmethod
    def from_starlette(cls, upload_file: StarletteUploadFile) -> UploadFile:
        """Create UploadFile from Starlette's UploadFile."""
        return cls(
            file=upload_file.file,
            filename=upload_file.filename,
            content_type=upload_file.content_type,
            headers=dict(upload_file.headers) if upload_file.headers else {},
            size=upload_file.size,
        )
    
    async def read(self, size: int = -1) -> bytes:
        """Read file content asynchronously."""
        if hasattr(self.file, 'read'):
            if size == -1:
                return self.file.read()
            return self.file.read(size)
        return b""
    
    async def readline(self, size: int = -1) -> bytes:
        """Read a line from the file asynchronously."""
        if hasattr(self.file, 'readline'):
            if size == -1:
                return self.file.readline()
            return self.file.readline(size)
        return b""
    
    async def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to a position in the file."""
        if hasattr(self.file, 'seek'):
            return self.file.seek(offset, whence)
        return 0
    
    async def close(self) -> None:
        """Close the file."""
        if hasattr(self.file, 'close'):
            self.file.close()
    
    async def write(self, data: Union[bytes, str]) -> int:
        """Write data to the file."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        if hasattr(self.file, 'write'):
            return self.file.write(data)
        return 0
    
    def __repr__(self) -> str:
        return f"<UploadFile filename={self.filename!r} content_type={self.content_type!r}>"


class FormData(BaseModel):
    """
    Base class for form data validation using Pydantic.
    Provides automatic validation and serialization for form fields.
    """
    
    class Config:
        # Allow extra fields by default for flexibility
        extra = "allow"
        # Use enum values instead of enum objects
        use_enum_values = True
        # Validate assignment
        validate_assignment = True


class FormParser:
    """
    Enhanced form parser that handles both regular forms and multipart data.
    Supports file uploads and form validation.
    """
    
    def __init__(self, max_file_size: int = 1024 * 1024 * 16):  # 16MB default
        self.max_file_size = max_file_size
    
    async def parse_form(self, request: StarletteRequest) -> Dict[str, Any]:
        """
        Parse form data from request.
        Returns dictionary with form fields and uploaded files.
        """
        content_type = request.headers.get("content-type", "")
        
        if content_type.startswith("multipart/form-data"):
            return await self._parse_multipart(request)
        elif content_type.startswith("application/x-www-form-urlencoded"):
            return await self._parse_urlencoded(request)
        else:
            return {}
    
    async def _parse_multipart(self, request) -> Dict[str, Any]:
        """Parse multipart form data."""
        if not STARLETTE_AVAILABLE:
            return {}

        parser = MultiPartParser(request.headers, request.stream())
        form_data = {}

        async for field in parser:
            if field.filename:
                # This is a file upload
                upload_file = UploadFile(
                    file=field.file,
                    filename=field.filename,
                    content_type=field.content_type,
                    headers=dict(field.headers) if field.headers else {},
                )

                if field.name in form_data:
                    # Multiple files with same name
                    if not isinstance(form_data[field.name], list):
                        form_data[field.name] = [form_data[field.name]]
                    form_data[field.name].append(upload_file)
                else:
                    form_data[field.name] = upload_file
            else:
                # Regular form field
                value = (await field.read()).decode('utf-8')

                if field.name in form_data:
                    # Multiple values with same name
                    if not isinstance(form_data[field.name], list):
                        form_data[field.name] = [form_data[field.name]]
                    form_data[field.name].append(value)
                else:
                    form_data[field.name] = value

        return form_data
    
    async def _parse_urlencoded(self, request) -> Dict[str, Any]:
        """Parse URL-encoded form data."""
        if not STARLETTE_AVAILABLE:
            return {}

        parser = FormParser(request.headers, request.stream())
        form_data = {}

        async for field in parser:
            value = (await field.read()).decode('utf-8')

            if field.name in form_data:
                # Multiple values with same name
                if not isinstance(form_data[field.name], list):
                    form_data[field.name] = [form_data[field.name]]
                form_data[field.name].append(value)
            else:
                form_data[field.name] = value

        return form_data


def Form(
    *,
    alias: Optional[str] = None,
    alias_priority: Optional[int] = None,
    validation_alias: Optional[str] = None,
    serialization_alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    examples: Optional[List[Any]] = None,
    exclude: Optional[bool] = None,
    include: Optional[bool] = None,
    discriminator: Optional[str] = None,
    json_schema_extra: Optional[Dict[str, Any]] = None,
    frozen: Optional[bool] = None,
    validate_default: Optional[bool] = None,
    repr: bool = True,
    init_var: Optional[bool] = None,
    kw_only: Optional[bool] = None,
    pattern: Optional[str] = None,
    strict: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    allow_inf_nan: Optional[bool] = None,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    **extra: Any,
) -> Any:
    """
    FastAPI-style Form dependency for automatic form parsing and validation.
    
    This function creates a dependency that will automatically parse form data
    from the request and validate it against the specified model.
    
    Usage:
        @app.post("/upload")
        async def upload_file(form_data: MyFormModel = Form()):
            return form_data
    """
    return Field(
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        description=description,
        examples=examples,
        exclude=exclude,
        include=include,
        discriminator=discriminator,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        validate_default=validate_default,
        repr=repr,
        init_var=init_var,
        kw_only=kw_only,
        pattern=pattern,
        strict=strict,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_length=max_length,
        min_length=min_length,
        **extra,
    )


# Convenience functions for common form operations
async def save_upload_file(upload_file: UploadFile, destination: Union[str, Path]) -> None:
    """Save an uploaded file to disk."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    with open(destination, "wb") as f:
        content = await upload_file.read()
        f.write(content)


async def get_file_content(upload_file: UploadFile) -> bytes:
    """Get the full content of an uploaded file."""
    await upload_file.seek(0)  # Reset to beginning
    content = await upload_file.read()
    await upload_file.seek(0)  # Reset again for potential reuse
    return content


def validate_file_type(upload_file: UploadFile, allowed_types: List[str]) -> bool:
    """Validate that uploaded file has an allowed content type."""
    if not upload_file.content_type:
        return False
    return upload_file.content_type in allowed_types


def validate_file_size(upload_file: UploadFile, max_size: int) -> bool:
    """Validate that uploaded file doesn't exceed maximum size."""
    if upload_file.size is None:
        return True  # Can't validate unknown size
    return upload_file.size <= max_size
