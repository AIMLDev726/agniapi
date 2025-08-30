"""
Template engine support for Agni API framework.
Supports Jinja2 templates with Flask-like interface.
"""

from typing import Any, Dict, Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from .response import HTMLResponse


class TemplateEngine:
    """
    Template engine wrapper for Jinja2.
    Provides Flask-like template rendering interface.
    """
    
    def __init__(
        self,
        template_folder: str = "templates",
        auto_reload: bool = False,
        enable_async: bool = False,
    ):
        """
        Initialize template engine.
        
        Args:
            template_folder: Folder containing templates
            auto_reload: Whether to auto-reload templates
            enable_async: Whether to enable async template rendering
        """
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2 is required for template support. "
                "Install with: pip install jinja2"
            )
        
        self.template_folder = template_folder
        self.auto_reload = auto_reload
        self.enable_async = enable_async
        
        # Create Jinja2 environment
        loader = FileSystemLoader(template_folder)
        self.env = Environment(
            loader=loader,
            autoescape=select_autoescape(['html', 'xml']),
            auto_reload=auto_reload,
            enable_async=enable_async,
        )
    
    def render_template(
        self,
        template_name: str,
        **context: Any
    ) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            **context: Template variables
        
        Returns:
            Rendered template as string
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            raise RuntimeError(f"Template rendering failed: {e}")
    
    async def render_template_async(
        self,
        template_name: str,
        **context: Any
    ) -> str:
        """
        Render a template asynchronously.
        
        Args:
            template_name: Name of the template file
            **context: Template variables
        
        Returns:
            Rendered template as string
        """
        if not self.enable_async:
            raise RuntimeError("Async rendering not enabled")
        
        try:
            template = self.env.get_template(template_name)
            return await template.render_async(**context)
        except Exception as e:
            raise RuntimeError(f"Async template rendering failed: {e}")
    
    def render_template_string(
        self,
        source: str,
        **context: Any
    ) -> str:
        """
        Render a template from string.
        
        Args:
            source: Template source code
            **context: Template variables
        
        Returns:
            Rendered template as string
        """
        try:
            template = self.env.from_string(source)
            return template.render(**context)
        except Exception as e:
            raise RuntimeError(f"Template string rendering failed: {e}")


def render_template(
    template_name: str,
    template_folder: str = "templates",
    **context: Any
) -> HTMLResponse:
    """
    Convenience function to render a template and return HTML response.
    
    Args:
        template_name: Name of the template file
        template_folder: Folder containing templates
        **context: Template variables
    
    Returns:
        HTMLResponse with rendered template
    """
    engine = TemplateEngine(template_folder)
    content = engine.render_template(template_name, **context)
    return HTMLResponse(content)


def render_template_string(
    source: str,
    **context: Any
) -> HTMLResponse:
    """
    Convenience function to render a template string and return HTML response.
    
    Args:
        source: Template source code
        **context: Template variables
    
    Returns:
        HTMLResponse with rendered template
    """
    engine = TemplateEngine()
    content = engine.render_template_string(source, **context)
    return HTMLResponse(content)
