"""
Configuration management for AgniAPI.

This module provides comprehensive configuration management including:
- Environment-based configuration loading
- Configuration from files and objects
- Configuration validation and type conversion
- Flask-style configuration interface
"""

from __future__ import annotations

import os
import json
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
from typing import Any, Dict, Optional, Type, Union, get_type_hints
from dataclasses import dataclass, fields
from enum import Enum

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

try:
    from pydantic import BaseModel, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class Config(dict):
    """
    Configuration object that behaves like a dictionary but provides
    additional methods for loading configuration from various sources.
    """
    
    def __init__(self, defaults: Optional[Dict[str, Any]] = None):
        super().__init__()
        if defaults:
            self.update(defaults)
        
        # Track configuration sources for debugging
        self._sources: list[str] = []
    
    def from_envvar(self, variable_name: str, silent: bool = False) -> bool:
        """
        Load configuration from a file specified by an environment variable.
        
        Args:
            variable_name: Name of environment variable containing file path
            silent: If True, don't raise error if variable is not set
            
        Returns:
            True if configuration was loaded, False otherwise
        """
        file_path = os.environ.get(variable_name)
        if not file_path:
            if silent:
                return False
            raise ConfigError(f"Environment variable '{variable_name}' not set")
        
        return self.from_file(file_path)
    
    def from_file(self, file_path: Union[str, Path]) -> bool:
        """
        Load configuration from a file.
        Supports JSON, YAML, and TOML formats.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if configuration was loaded successfully
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ConfigError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.json']:
                    data = json.load(f)
                elif file_path.suffix.lower() in ['.yaml', '.yml']:
                    if not YAML_AVAILABLE:
                        raise ConfigError("YAML support not available. Install with: pip install pyyaml")
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() in ['.toml']:
                    if not TOML_AVAILABLE:
                        raise ConfigError("TOML support not available. Install with: pip install toml")
                    data = toml.load(f)
                else:
                    # Try to detect format from content
                    content = f.read()
                    f.seek(0)
                    
                    # Try JSON first
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        # Try YAML
                        if YAML_AVAILABLE:
                            try:
                                data = yaml.safe_load(content)
                            except yaml.YAMLError:
                                data = None
                        else:
                            data = None

                        if data is None:
                            # Try TOML if available
                            if TOML_AVAILABLE:
                                try:
                                    data = toml.loads(content)
                                except toml.TomlDecodeError:
                                    raise ConfigError(f"Unable to parse configuration file: {file_path}")
                            else:
                                raise ConfigError(f"Unable to parse configuration file: {file_path}")
            
            if isinstance(data, dict):
                self.update(data)
                self._sources.append(f"file:{file_path}")
                return True
            else:
                raise ConfigError(f"Configuration file must contain a dictionary: {file_path}")
                
        except Exception as e:
            if isinstance(e, ConfigError):
                raise
            raise ConfigError(f"Error loading configuration from {file_path}: {e}")
    
    def from_object(self, obj: Union[str, object]) -> None:
        """
        Load configuration from an object.
        
        Args:
            obj: Object or import string (e.g., 'myapp.config.ProductionConfig')
        """
        if isinstance(obj, str):
            # Import the object
            module_name, obj_name = obj.rsplit('.', 1)
            try:
                module = __import__(module_name, fromlist=[obj_name])
                obj = getattr(module, obj_name)
            except (ImportError, AttributeError) as e:
                raise ConfigError(f"Could not import configuration object '{obj}': {e}")
        
        # Extract configuration from object
        if hasattr(obj, '__dict__'):
            # Regular object with attributes
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    self[key] = value
        elif isinstance(obj, dict):
            # Dictionary-like object
            self.update(obj)
        else:
            raise ConfigError(f"Configuration object must have attributes or be dict-like: {type(obj)}")
        
        self._sources.append(f"object:{obj}")
    
    def from_env(self, prefix: str = "", separator: str = "_") -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables (e.g., 'MYAPP_')
            separator: Separator for nested keys (e.g., 'MYAPP_DB_HOST' -> {'DB': {'HOST': ...}})
        """
        env_vars = {}
        
        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue
            
            # Remove prefix
            config_key = key[len(prefix):] if prefix else key
            
            # Convert to nested structure if separator is found
            if separator in config_key:
                parts = config_key.split(separator)
                current = env_vars
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = self._convert_env_value(value)
            else:
                env_vars[config_key] = self._convert_env_value(value)
        
        self.update(env_vars)
        self._sources.append(f"env:prefix={prefix}")
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate Python type."""
        # Try boolean
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try JSON (for lists, dicts, etc.)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Return as string
        return value
    
    def get_namespace(self, namespace: str, lowercase: bool = True, trim_namespace: bool = True) -> Dict[str, Any]:
        """
        Get all configuration keys that start with a namespace.
        
        Args:
            namespace: Namespace prefix (e.g., 'DATABASE_')
            lowercase: Convert keys to lowercase
            trim_namespace: Remove namespace prefix from keys
            
        Returns:
            Dictionary with matching configuration
        """
        result = {}
        namespace_upper = namespace.upper()
        
        for key, value in self.items():
            key_upper = key.upper()
            if key_upper.startswith(namespace_upper):
                result_key = key
                
                if trim_namespace:
                    result_key = key[len(namespace):]
                
                if lowercase:
                    result_key = result_key.lower()
                
                result[result_key] = value
        
        return result
    
    def validate(self, schema: Union[Type[BaseModel], Type, Dict[str, Any]]) -> Any:
        """
        Validate configuration against a schema.
        
        Args:
            schema: Pydantic model, dataclass, or dictionary schema
            
        Returns:
            Validated configuration object
        """
        if PYDANTIC_AVAILABLE and isinstance(schema, type) and issubclass(schema, BaseModel):
            # Pydantic validation
            try:
                return schema(**self)
            except ValidationError as e:
                raise ConfigError(f"Configuration validation failed: {e}")
        
        elif hasattr(schema, '__dataclass_fields__'):
            # Dataclass validation
            try:
                # Get type hints for validation
                type_hints = get_type_hints(schema)
                validated_data = {}
                
                for field in fields(schema):
                    field_name = field.name
                    field_type = type_hints.get(field_name, Any)
                    
                    if field_name in self:
                        value = self[field_name]
                        # Basic type checking
                        if field_type != Any and not isinstance(value, field_type):
                            try:
                                value = field_type(value)
                            except (ValueError, TypeError):
                                raise ConfigError(f"Invalid type for field '{field_name}': expected {field_type}, got {type(value)}")
                        validated_data[field_name] = value
                    elif field.default != dataclass.MISSING:
                        validated_data[field_name] = field.default
                    elif field.default_factory != dataclass.MISSING:
                        validated_data[field_name] = field.default_factory()
                    else:
                        raise ConfigError(f"Required field '{field_name}' not found in configuration")
                
                return schema(**validated_data)
                
            except Exception as e:
                if isinstance(e, ConfigError):
                    raise
                raise ConfigError(f"Configuration validation failed: {e}")
        
        elif isinstance(schema, dict):
            # Dictionary schema validation (basic)
            validated_data = {}
            for key, expected_type in schema.items():
                if key in self:
                    value = self[key]
                    if expected_type != Any and not isinstance(value, expected_type):
                        try:
                            value = expected_type(value)
                        except (ValueError, TypeError):
                            raise ConfigError(f"Invalid type for key '{key}': expected {expected_type}, got {type(value)}")
                    validated_data[key] = value
                else:
                    raise ConfigError(f"Required key '{key}' not found in configuration")
            
            return validated_data
        
        else:
            raise ConfigError(f"Unsupported schema type: {type(schema)}")
    
    def get_sources(self) -> list[str]:
        """Get list of configuration sources that were loaded."""
        return self._sources.copy()
    
    def __repr__(self) -> str:
        return f"<Config {dict(self)}>"


# Common configuration patterns
@dataclass
class DatabaseConfig:
    """Database configuration schema."""
    url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30


@dataclass
class RedisConfig:
    """Redis configuration schema."""
    url: str = "redis://localhost:6379"
    max_connections: int = 10
    retry_on_timeout: bool = True


@dataclass
class SessionConfig:
    """Session configuration schema."""
    secret_key: str
    cookie_name: str = "session"
    cookie_httponly: bool = True
    cookie_secure: bool = False
    permanent_session_lifetime: int = 2678400  # 31 days in seconds


class Environment(Enum):
    """Common environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


def load_config(
    config_file: Optional[str] = None,
    env_prefix: str = "",
    defaults: Optional[Dict[str, Any]] = None
) -> Config:
    """
    Load configuration from multiple sources with sensible defaults.
    
    Args:
        config_file: Path to configuration file or environment variable name
        env_prefix: Prefix for environment variables
        defaults: Default configuration values
        
    Returns:
        Loaded configuration object
    """
    config = Config(defaults)
    
    # Load from file if specified
    if config_file:
        if config_file.startswith('$'):
            # Environment variable containing file path
            config.from_envvar(config_file[1:], silent=True)
        else:
            # Direct file path
            file_path = Path(config_file)
            if file_path.exists():
                config.from_file(file_path)
    
    # Load from environment variables
    config.from_env(prefix=env_prefix)
    
    return config
