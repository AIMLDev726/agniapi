# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-08-30

### Added
- Initial release of Agni API framework
- Complete ASGI and WSGI support
- Advanced dependency injection system with `Depends()`
- Automatic request body parsing (JSON, form data)
- Path parameter extraction with type conversion
- Query parameter handling with type conversion
- Pydantic model validation for request bodies
- Comprehensive error handling system
- Background task integration
- Flask-style and FastAPI-style routing decorators
- Blueprint support for modular applications
- Built-in MCP (Model Context Protocol) integration
- WebSocket support
- Security utilities and middleware
- OpenAPI documentation generation
- Comprehensive testing framework
- CLI tools for development

### Features
- **Unified API**: Combines the best of Flask and FastAPI patterns
- **Type Safety**: Full type hint support with automatic validation
- **Performance**: Async/await support with efficient request handling
- **Developer Experience**: Intuitive API design with excellent error messages
- **Extensibility**: Plugin system and middleware support
- **Production Ready**: Comprehensive testing and error handling

### Technical Highlights
- Zero-dependency core (optional dependencies for specific features)
- Support for Python 3.9+
- Full async/await support
- Automatic OpenAPI schema generation
- Built-in testing utilities
- Comprehensive type checking support
