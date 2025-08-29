"""
Monitoring and metrics for AgniAPI.

This module provides comprehensive monitoring capabilities including:
- Prometheus metrics integration
- Health check endpoints
- Structured logging with correlation IDs
- Request duration and count metrics
- Custom metrics support
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    # Provide fallback
    class structlog:
        @staticmethod
        def configure(**kwargs):
            pass

        @staticmethod
        def get_logger(name=None):
            return logging.getLogger(name or 'agniapi')

        class stdlib:
            @staticmethod
            def filter_by_level():
                pass
            @staticmethod
            def add_logger_name():
                pass
            @staticmethod
            def add_log_level():
                pass
            @staticmethod
            def PositionalArgumentsFormatter():
                pass

            class LoggerFactory:
                pass

            class BoundLogger:
                def __init__(self, logger):
                    self._logger = logger

                def bind(self, **kwargs):
                    return self

                def info(self, msg, **kwargs):
                    self._logger.info(msg)

                def error(self, msg, **kwargs):
                    self._logger.error(msg)

        class processors:
            @staticmethod
            def TimeStamper(**kwargs):
                pass
            @staticmethod
            def StackInfoRenderer():
                pass
            @staticmethod
            def format_exc_info():
                pass
            @staticmethod
            def UnicodeDecoder():
                pass
            @staticmethod
            def JSONRenderer():
                pass
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from contextlib import contextmanager

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from .request import Request
from .response import Response, JSONResponse


class MetricsRegistry:
    """Registry for application metrics."""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self._initialized = False
        self._setup_default_metrics()
    
    def _setup_default_metrics(self) -> None:
        """Setup default application metrics."""
        if not PROMETHEUS_AVAILABLE or self._initialized:
            return

        try:
            # Request metrics
            self.metrics['requests_total'] = Counter(
                'agniapi_requests_total',
                'Total number of HTTP requests',
                ['method', 'endpoint', 'status_code']
            )

            self.metrics['request_duration_seconds'] = Histogram(
                'agniapi_request_duration_seconds',
                'HTTP request duration in seconds',
                ['method', 'endpoint']
            )

            self.metrics['active_requests'] = Gauge(
                'agniapi_active_requests',
                'Number of active HTTP requests'
            )

            # Application metrics
            self.metrics['app_info'] = Info(
                'agniapi_app_info',
                'Application information'
            )

            # Database metrics
            self.metrics['db_connections_active'] = Gauge(
                'agniapi_db_connections_active',
                'Number of active database connections'
            )

            self.metrics['db_query_duration_seconds'] = Histogram(
                'agniapi_db_query_duration_seconds',
                'Database query duration in seconds',
                ['query_type']
            )

            # Cache metrics
            self.metrics['cache_hits_total'] = Counter(
                'agniapi_cache_hits_total',
                'Total number of cache hits',
                ['cache_type']
            )

            self.metrics['cache_misses_total'] = Counter(
                'agniapi_cache_misses_total',
                'Total number of cache misses',
                ['cache_type']
            )

            self._initialized = True

        except Exception as e:
            # If metrics already exist, just mark as initialized
            self._initialized = True
    
    def get_metric(self, name: str) -> Optional[Any]:
        """Get a metric by name."""
        return self.metrics.get(name)
    
    def register_metric(self, name: str, metric: Any) -> None:
        """Register a custom metric."""
        self.metrics[name] = metric
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1) -> None:
        """Increment a counter metric."""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'labels'):
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a histogram metric."""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'labels'):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'labels'):
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def inc_gauge(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a gauge metric."""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'labels'):
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def dec_gauge(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement a gauge metric."""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'labels'):
            if labels:
                metric.labels(**labels).dec(value)
            else:
                metric.dec(value)


class HealthChecker:
    """Health check system."""
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._register_default_checks()
    
    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check('app', self._check_app)
    
    def _check_app(self) -> Dict[str, Any]:
        """Basic application health check."""
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        """Register a health check function."""
        self.checks[name] = check_func
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_status = 'healthy'
        
        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results[name] = result
                
                # Check if this component is unhealthy
                if result.get('status') != 'healthy':
                    overall_status = 'unhealthy'
                    
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': results
        }


class StructuredLogger:
    """Structured logging with correlation IDs."""
    
    def __init__(self, logger_name: str = 'agniapi'):
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger(logger_name)
    
    def get_logger(self, **context) -> structlog.BoundLogger:
        """Get a logger with additional context."""
        return self.logger.bind(**context)
    
    @contextmanager
    def correlation_context(self, correlation_id: Optional[str] = None):
        """Context manager for correlation ID."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        logger = self.get_logger(correlation_id=correlation_id)
        
        # Store in context for middleware access
        import contextvars
        correlation_var = contextvars.ContextVar('correlation_id', default=None)
        token = correlation_var.set(correlation_id)
        
        try:
            yield logger
        finally:
            correlation_var.reset(token)


class MetricsMiddleware:
    """Middleware for collecting request metrics."""
    
    def __init__(self, metrics_registry: MetricsRegistry):
        self.metrics = metrics_registry
    
    async def __call__(self, request: Request, call_next):
        """Process request with metrics collection."""
        start_time = time.time()
        
        # Increment active requests
        self.metrics.inc_gauge('active_requests')
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract labels
            method = request.method
            endpoint = request.path
            status_code = str(response.status_code)
            
            # Record metrics
            self.metrics.increment_counter(
                'requests_total',
                labels={'method': method, 'endpoint': endpoint, 'status_code': status_code}
            )
            
            self.metrics.observe_histogram(
                'request_duration_seconds',
                duration,
                labels={'method': method, 'endpoint': endpoint}
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            
            self.metrics.increment_counter(
                'requests_total',
                labels={'method': request.method, 'endpoint': request.path, 'status_code': '500'}
            )
            
            self.metrics.observe_histogram(
                'request_duration_seconds',
                duration,
                labels={'method': request.method, 'endpoint': request.path}
            )
            
            raise
        
        finally:
            # Decrement active requests
            self.metrics.dec_gauge('active_requests')


class LoggingMiddleware:
    """Middleware for structured request logging."""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
    
    async def __call__(self, request: Request, call_next):
        """Process request with structured logging."""
        correlation_id = request.headers.get('x-correlation-id') or str(uuid.uuid4())
        
        with self.logger.correlation_context(correlation_id) as logger:
            start_time = time.time()
            
            # Log request start
            logger.info(
                "Request started",
                method=request.method,
                path=request.path,
                user_agent=request.headers.get('user-agent'),
                client_ip=request.client
            )
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Log request completion
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    duration=duration
                )
                
                # Add correlation ID to response headers
                response.headers['x-correlation-id'] = correlation_id
                
                return response
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                
                # Log request error
                logger.error(
                    "Request failed",
                    method=request.method,
                    path=request.path,
                    duration=duration,
                    error=str(e),
                    exc_info=True
                )
                
                raise


# Global instances
metrics_registry = MetricsRegistry()
health_checker = HealthChecker()
structured_logger = StructuredLogger()


def get_metrics_response() -> Response:
    """Get Prometheus metrics response."""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            content={'error': 'Prometheus client not available'},
            status_code=503
        )
    
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


def get_health_response() -> JSONResponse:
    """Get health check response."""
    health_data = health_checker.run_checks()
    status_code = 200 if health_data['status'] == 'healthy' else 503
    
    return JSONResponse(
        content=health_data,
        status_code=status_code
    )


def monitor_function(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to monitor function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success metric
                duration = time.time() - start_time
                metrics_registry.observe_histogram(
                    f"{metric_name}_duration_seconds",
                    duration,
                    labels=labels
                )
                metrics_registry.increment_counter(
                    f"{metric_name}_total",
                    labels={**(labels or {}), 'status': 'success'}
                )
                
                return result
                
            except Exception as e:
                # Record error metric
                duration = time.time() - start_time
                metrics_registry.observe_histogram(
                    f"{metric_name}_duration_seconds",
                    duration,
                    labels=labels
                )
                metrics_registry.increment_counter(
                    f"{metric_name}_total",
                    labels={**(labels or {}), 'status': 'error'}
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record success metric
                duration = time.time() - start_time
                metrics_registry.observe_histogram(
                    f"{metric_name}_duration_seconds",
                    duration,
                    labels=labels
                )
                metrics_registry.increment_counter(
                    f"{metric_name}_total",
                    labels={**(labels or {}), 'status': 'success'}
                )
                
                return result
                
            except Exception as e:
                # Record error metric
                duration = time.time() - start_time
                metrics_registry.observe_histogram(
                    f"{metric_name}_duration_seconds",
                    duration,
                    labels=labels
                )
                metrics_registry.increment_counter(
                    f"{metric_name}_total",
                    labels={**(labels or {}), 'status': 'error'}
                )
                
                raise
        
        if hasattr(func, '__await__'):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
