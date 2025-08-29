"""
Content negotiation for AgniAPI.

This module provides comprehensive content negotiation capabilities including:
- Accept header parsing and handling
- Multiple response format support (JSON, XML, CSV, HTML)
- Automatic content type detection
- Custom format handlers
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from io import StringIO
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass

from .request import Request
from .response import Response, JSONResponse, HTMLResponse
from .exceptions import HTTPException


class UnsupportedMediaType(HTTPException):
    """Exception raised when requested media type is not supported."""
    
    def __init__(self, detail: str = "Unsupported media type"):
        super().__init__(status_code=415, detail=detail)


class NotAcceptable(HTTPException):
    """Exception raised when no acceptable response format is available."""
    
    def __init__(self, detail: str = "Not acceptable"):
        super().__init__(status_code=406, detail=detail)


@dataclass
class MediaType:
    """Represents a media type with quality factor."""
    type: str
    subtype: str
    quality: float = 1.0
    params: Dict[str, str] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}
    
    @property
    def main_type(self) -> str:
        """Get the main type (e.g., 'application' from 'application/json')."""
        return self.type
    
    @property
    def full_type(self) -> str:
        """Get the full media type (e.g., 'application/json')."""
        return f"{self.type}/{self.subtype}"
    
    def matches(self, other: Union[str, 'MediaType']) -> bool:
        """Check if this media type matches another."""
        if isinstance(other, str):
            other_type, other_subtype = other.split('/', 1)
        else:
            other_type, other_subtype = other.type, other.subtype
        
        # Handle wildcards
        if self.type == '*' or other_type == '*':
            return True
        if self.type != other_type:
            return False
        if self.subtype == '*' or other_subtype == '*':
            return True
        return self.subtype == other_subtype
    
    def __str__(self) -> str:
        return self.full_type
    
    def __repr__(self) -> str:
        return f"MediaType('{self.full_type}', quality={self.quality})"


class ContentHandler(ABC):
    """Abstract base class for content handlers."""
    
    @property
    @abstractmethod
    def media_types(self) -> List[str]:
        """List of media types this handler supports."""
        pass
    
    @abstractmethod
    def serialize(self, data: Any, **kwargs) -> Union[str, bytes]:
        """Serialize data to the format."""
        pass
    
    @abstractmethod
    def deserialize(self, content: Union[str, bytes], **kwargs) -> Any:
        """Deserialize content from the format."""
        pass
    
    @property
    def content_type(self) -> str:
        """Default content type for this handler."""
        return self.media_types[0]


class JSONHandler(ContentHandler):
    """JSON content handler."""
    
    @property
    def media_types(self) -> List[str]:
        return ['application/json', 'text/json']
    
    def serialize(self, data: Any, **kwargs) -> str:
        """Serialize data to JSON."""
        # Handle special types
        if hasattr(data, 'to_dict'):
            data = data.to_dict()
        elif hasattr(data, '__dict__'):
            data = data.__dict__
        
        return json.dumps(data, default=str, **kwargs)
    
    def deserialize(self, content: Union[str, bytes], **kwargs) -> Any:
        """Deserialize JSON content."""
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return json.loads(content, **kwargs)


class XMLHandler(ContentHandler):
    """XML content handler."""
    
    @property
    def media_types(self) -> List[str]:
        return ['application/xml', 'text/xml']
    
    def serialize(self, data: Any, root_name: str = 'root', **kwargs) -> str:
        """Serialize data to XML."""
        root = ET.Element(root_name)
        self._dict_to_xml(data, root)
        return ET.tostring(root, encoding='unicode')
    
    def _dict_to_xml(self, data: Any, parent: ET.Element) -> None:
        """Convert dictionary to XML elements."""
        if isinstance(data, dict):
            for key, value in data.items():
                child = ET.SubElement(parent, str(key))
                self._dict_to_xml(value, child)
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, 'item')
                self._dict_to_xml(item, child)
        else:
            parent.text = str(data)
    
    def deserialize(self, content: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """Deserialize XML content."""
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        root = ET.fromstring(content)
        return self._xml_to_dict(root)
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {}
        
        # Handle attributes
        if element.attrib:
            result['@attributes'] = element.attrib
        
        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children
                return element.text.strip()
            result['#text'] = element.text.strip()
        
        # Handle children
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # Multiple children with same tag - convert to list
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result


class CSVHandler(ContentHandler):
    """CSV content handler."""
    
    @property
    def media_types(self) -> List[str]:
        return ['text/csv', 'application/csv']
    
    def serialize(self, data: Any, **kwargs) -> str:
        """Serialize data to CSV."""
        output = StringIO()
        
        if isinstance(data, list) and data:
            # List of dictionaries
            if isinstance(data[0], dict):
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames, **kwargs)
                writer.writeheader()
                writer.writerows(data)
            else:
                # List of values
                writer = csv.writer(output, **kwargs)
                for row in data:
                    if isinstance(row, (list, tuple)):
                        writer.writerow(row)
                    else:
                        writer.writerow([row])
        elif isinstance(data, dict):
            # Single dictionary
            writer = csv.DictWriter(output, fieldnames=data.keys(), **kwargs)
            writer.writeheader()
            writer.writerow(data)
        else:
            # Single value
            writer = csv.writer(output, **kwargs)
            writer.writerow([data])
        
        return output.getvalue()
    
    def deserialize(self, content: Union[str, bytes], **kwargs) -> List[Dict[str, Any]]:
        """Deserialize CSV content."""
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        input_stream = StringIO(content)
        reader = csv.DictReader(input_stream, **kwargs)
        return list(reader)


class HTMLHandler(ContentHandler):
    """HTML content handler."""
    
    @property
    def media_types(self) -> List[str]:
        return ['text/html', 'application/xhtml+xml']
    
    def serialize(self, data: Any, template: Optional[str] = None, **kwargs) -> str:
        """Serialize data to HTML."""
        if template:
            # Use template rendering if available
            try:
                from .templating import render_template_string
                return render_template_string(template, data=data, **kwargs)
            except ImportError:
                pass
        
        # Simple HTML generation
        if isinstance(data, dict):
            html = "<table border='1'>\n"
            for key, value in data.items():
                html += f"  <tr><td>{key}</td><td>{value}</td></tr>\n"
            html += "</table>"
            return html
        elif isinstance(data, list):
            html = "<ul>\n"
            for item in data:
                html += f"  <li>{item}</li>\n"
            html += "</ul>"
            return html
        else:
            return f"<p>{data}</p>"
    
    def deserialize(self, content: Union[str, bytes], **kwargs) -> str:
        """Deserialize HTML content (returns as string)."""
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return content


class ContentNegotiator:
    """Main content negotiation class."""
    
    def __init__(self):
        self.handlers: Dict[str, ContentHandler] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default content handlers."""
        self.register_handler(JSONHandler())
        self.register_handler(XMLHandler())
        self.register_handler(CSVHandler())
        self.register_handler(HTMLHandler())
    
    def register_handler(self, handler: ContentHandler) -> None:
        """Register a content handler."""
        for media_type in handler.media_types:
            self.handlers[media_type] = handler
    
    def parse_accept_header(self, accept_header: str) -> List[MediaType]:
        """Parse Accept header into list of MediaType objects."""
        if not accept_header:
            return [MediaType('*', '*')]
        
        media_types = []
        
        for item in accept_header.split(','):
            item = item.strip()
            if not item:
                continue
            
            # Split media type and parameters
            parts = item.split(';')
            media_type_str = parts[0].strip()
            
            # Parse media type
            if '/' in media_type_str:
                type_part, subtype = media_type_str.split('/', 1)
            else:
                type_part, subtype = media_type_str, '*'
            
            # Parse parameters
            quality = 1.0
            params = {}
            
            for param in parts[1:]:
                if '=' in param:
                    key, value = param.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    
                    if key == 'q':
                        try:
                            quality = float(value)
                        except ValueError:
                            quality = 1.0
                    else:
                        params[key] = value
            
            media_types.append(MediaType(type_part, subtype, quality, params))
        
        # Sort by quality (highest first)
        media_types.sort(key=lambda x: x.quality, reverse=True)
        return media_types
    
    def select_handler(self, accept_header: str) -> Optional[ContentHandler]:
        """Select the best content handler based on Accept header."""
        accepted_types = self.parse_accept_header(accept_header)
        
        for media_type in accepted_types:
            for handler_type, handler in self.handlers.items():
                if media_type.matches(handler_type):
                    return handler
        
        return None
    
    def negotiate_response(self, request: Request, data: Any, **kwargs) -> Response:
        """Negotiate response format based on request Accept header."""
        accept_header = request.headers.get('accept', 'application/json')
        handler = self.select_handler(accept_header)
        
        if not handler:
            raise NotAcceptable(f"No acceptable format found for: {accept_header}")
        
        # Serialize data
        content = handler.serialize(data, **kwargs)
        
        # Create appropriate response
        if isinstance(handler, JSONHandler):
            return JSONResponse(content=json.loads(content))
        elif isinstance(handler, HTMLHandler):
            return HTMLResponse(content=content)
        else:
            return Response(
                content=content,
                media_type=handler.content_type
            )


# Global content negotiator instance
content_negotiator = ContentNegotiator()


def negotiate_content(data: Any, request: Request, **kwargs) -> Response:
    """Convenience function for content negotiation."""
    return content_negotiator.negotiate_response(request, data, **kwargs)
