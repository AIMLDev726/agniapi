"""
Command Line Interface for Agni API framework.
Provides commands for project scaffolding, running servers, and development tools.
"""

from __future__ import annotations

import os
import sys
import click
import asyncio
import subprocess
import importlib.util
from typing import Optional
from pathlib import Path
try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    def tabulate(data, headers=None, tablefmt='grid'):
        """Fallback tabulate function."""
        if not data:
            return "No data"

        # Simple table formatting
        if headers:
            result = " | ".join(str(h) for h in headers) + "\n"
            result += "-" * len(result) + "\n"
        else:
            result = ""

        for row in data:
            if isinstance(row, dict):
                result += " | ".join(str(row.get(h, '')) for h in headers) + "\n"
            else:
                result += " | ".join(str(cell) for cell in row) + "\n"

        return result

from .app import AgniAPI
from .database import MigrationManager, get_database


@click.group()
@click.version_option(version="0.1.1", prog_name="agniapi")
def cli():
    """Agni API - A unified REST API framework with MCP support."""
    pass


@cli.command()
@click.argument("name")
@click.option("--template", "-t", default="basic", help="Project template to use")
@click.option("--directory", "-d", default=".", help="Directory to create project in")
def new(name: str, template: str, directory: str):
    """Create a new Agni API project."""
    project_path = Path(directory) / name

    if project_path.exists():
        click.echo(f"Error: Directory '{project_path}' already exists", err=True)
        sys.exit(1)

    # Create project structure
    project_path.mkdir(parents=True)

    # Create basic project files
    _create_project_files(project_path, name, template)

    click.echo(f"Created new Agni API project: {name}")
    click.echo(f"Project location: {project_path.absolute()}")
    click.echo("\nNext steps:")
    click.echo(f"  cd {name}")
    click.echo("  pip install -r requirements.txt")
    click.echo("  agniapi run")


# Database command group
@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option("--directory", "-d", default="migrations", help="Migration directory")
def init(directory: str):
    """Initialize migration repository."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.init(directory)
        click.echo(f"Initialized migration repository in '{directory}'")
    except Exception as e:
        click.echo(f"Error initializing migrations: {e}", err=True)
        sys.exit(1)


@db.command()
@click.option("--message", "-m", required=True, help="Migration message")
@click.option("--autogenerate/--no-autogenerate", default=True, help="Auto-generate migration")
def migrate(message: str, autogenerate: bool):
    """Create a new migration."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.revision(message, autogenerate=autogenerate)
        click.echo(f"Created migration: {message}")
    except Exception as e:
        click.echo(f"Error creating migration: {e}", err=True)
        sys.exit(1)


@db.command()
@click.option("--revision", "-r", default="head", help="Revision to upgrade to")
def upgrade(revision: str):
    """Upgrade database to a revision."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.upgrade(revision)
        click.echo(f"Upgraded database to revision: {revision}")
    except Exception as e:
        click.echo(f"Error upgrading database: {e}", err=True)
        sys.exit(1)


@db.command()
@click.argument("revision")
def downgrade(revision: str):
    """Downgrade database to a revision."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.downgrade(revision)
        click.echo(f"Downgraded database to revision: {revision}")
    except Exception as e:
        click.echo(f"Error downgrading database: {e}", err=True)
        sys.exit(1)


@db.command()
def current():
    """Show current database revision."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.current()
    except Exception as e:
        click.echo(f"Error getting current revision: {e}", err=True)
        sys.exit(1)


@db.command()
def history():
    """Show migration history."""
    try:
        database = get_database()
        if not database:
            click.echo("Error: No database configured", err=True)
            sys.exit(1)

        migration_manager = MigrationManager(database)
        migration_manager.history()
    except Exception as e:
        click.echo(f"Error getting migration history: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--app", "-a", default="app:app", help="Application module and variable")
def shell(app: str):
    """Start an interactive shell with application context."""
    try:
        # Import the application
        app_instance = _load_app(app)

        # Setup shell context
        import code
        import readline
        import rlcompleter

        # Enable tab completion
        readline.set_completer(rlcompleter.Completer(locals()).complete)
        readline.parse_and_bind("tab: complete")

        # Create shell context
        context = {
            'app': app_instance,
            'db': get_database(),
        }

        # Add models to context if available
        try:
            from .database import Base
            for name, obj in Base.registry._class_registry.items():
                if hasattr(obj, '__tablename__'):
                    context[name] = obj
        except:
            pass

        banner = f"AgniAPI Shell\nPython {sys.version}\nApp: {app}\n"
        banner += f"Available objects: {', '.join(context.keys())}"

        code.interact(banner=banner, local=context)

    except Exception as e:
        click.echo(f"Error starting shell: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--format", "-f", type=click.Choice(['table', 'json', 'plain']), default='table', help="Output format")
@click.option("--app", "-a", default="app:app", help="Application module and variable")
def routes(format: str, app: str):
    """List all application routes."""
    try:
        app_instance = _load_app(app)

        routes_data = []
        for route in app_instance.router.routes:
            routes_data.append({
                'Path': route.path,
                'Methods': ', '.join(route.methods),
                'Name': route.name,
                'Handler': f"{route.handler.__module__}.{route.handler.__name__}",
                'Tags': ', '.join(route.tags) if route.tags else '',
            })

        if format == 'table':
            if routes_data:
                click.echo(tabulate(routes_data, headers='keys', tablefmt='grid'))
            else:
                click.echo("No routes found")
        elif format == 'json':
            import json
            click.echo(json.dumps(routes_data, indent=2))
        elif format == 'plain':
            for route_data in routes_data:
                click.echo(f"{route_data['Methods']:10} {route_data['Path']:30} {route_data['Handler']}")

    except Exception as e:
        click.echo(f"Error listing routes: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--watch", "-w", is_flag=True, help="Watch for file changes and re-run tests")
@click.option("--coverage", "-c", is_flag=True, help="Run with coverage reporting")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.argument("path", default="tests", required=False)
def test(watch: bool, coverage: bool, verbose: bool, path: str):
    """Run tests."""
    try:
        cmd = []

        if coverage:
            cmd.extend(["python", "-m", "coverage", "run", "-m"])
        else:
            cmd.extend(["python", "-m"])

        cmd.append("pytest")

        if verbose:
            cmd.append("-v")

        cmd.append(path)

        if watch:
            # Use pytest-watch if available
            try:
                # Check if pytest-watch is available
                __import__('pytest_watch')
                cmd = ["ptw"] + cmd[2:]  # Remove python -m
            except ImportError:
                click.echo("Warning: pytest-watch not installed. Install with: pip install pytest-watch")

        result = subprocess.run(cmd)

        if coverage and not watch:
            # Show coverage report
            subprocess.run(["python", "-m", "coverage", "report"])
            subprocess.run(["python", "-m", "coverage", "html"])
            click.echo("Coverage report generated in htmlcov/")

        sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"Error running tests: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--app", "-a", default="app:app", help="Application module and variable")
def lint(app: str):
    """Run code linting."""
    try:
        # Run flake8
        click.echo("Running flake8...")
        result1 = subprocess.run(["python", "-m", "flake8", "."])

        # Run mypy
        click.echo("Running mypy...")
        result2 = subprocess.run(["python", "-m", "mypy", "."])

        # Run bandit for security
        click.echo("Running bandit...")
        result3 = subprocess.run(["python", "-m", "bandit", "-r", "."])

        if result1.returncode == 0 and result2.returncode == 0 and result3.returncode == 0:
            click.echo("✅ All linting checks passed!")
        else:
            click.echo("❌ Some linting checks failed")
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"Linting tool not found: {e}. Install with: pip install flake8 mypy bandit")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running linting: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--check", is_flag=True, help="Check if files would be reformatted")
def format(check: bool):
    """Format code using black and isort."""
    try:
        # Run black
        black_cmd = ["python", "-m", "black"]
        if check:
            black_cmd.append("--check")
        black_cmd.append(".")

        click.echo("Running black...")
        result1 = subprocess.run(black_cmd)

        # Run isort
        isort_cmd = ["python", "-m", "isort"]
        if check:
            isort_cmd.append("--check-only")
        isort_cmd.append(".")

        click.echo("Running isort...")
        result2 = subprocess.run(isort_cmd)

        if result1.returncode == 0 and result2.returncode == 0:
            if check:
                click.echo("✅ Code formatting is correct!")
            else:
                click.echo("✅ Code formatted successfully!")
        else:
            if check:
                click.echo("❌ Code formatting issues found")
            else:
                click.echo("❌ Code formatting failed")
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"Formatting tool not found: {e}. Install with: pip install black isort")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error formatting code: {e}", err=True)
        sys.exit(1)


def _load_app(app_spec: str) -> AgniAPI:
    """Load application from module specification."""
    try:
        module_name, app_name = app_spec.split(':', 1)
    except ValueError:
        raise ValueError(f"Invalid app specification: {app_spec}. Use format 'module:variable'")

    # Add current directory to Python path
    sys.path.insert(0, os.getcwd())

    try:
        # Import the module
        spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
        if spec is None:
            # Try importing as package
            module = __import__(module_name, fromlist=[app_name])
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Get the app instance
        app_instance = getattr(module, app_name)

        if not isinstance(app_instance, AgniAPI):
            raise ValueError(f"'{app_spec}' is not an AgniAPI instance")

        return app_instance

    except (ImportError, AttributeError) as e:
        raise ValueError(f"Could not load app '{app_spec}': {e}")


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload", "-r", is_flag=True, help="Enable auto-reload")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode")
@click.option("--app", "-a", default="main:app", help="Application module and variable")
@click.option("--workers", "-w", default=1, help="Number of worker processes")
@click.option("--access-log", is_flag=True, help="Enable access logging")
def run(host: str, port: int, reload: bool, debug: bool, app: str, workers: int, access_log: bool):
    """Run the Agni API development server."""
    try:
        # Import the application
        module_name, app_name = app.split(":", 1)
        module = __import__(module_name, fromlist=[app_name])
        app_instance = getattr(module, app_name)
        
        if not isinstance(app_instance, AgniAPI):
            click.echo(f"Error: {app} is not an AgniAPI instance", err=True)
            sys.exit(1)
        
        # Set debug mode
        if debug:
            app_instance.debug = debug
        
        click.echo(f"Starting Agni API server on {host}:{port}")
        click.echo(f"Debug mode: {debug}")
        click.echo(f"Auto-reload: {reload}")
        
        # Run the server
        if reload or workers > 1:
            # Use uvicorn for advanced features
            try:
                import uvicorn
                uvicorn.run(
                    app,
                    host=host,
                    port=port,
                    reload=reload,
                    debug=debug,
                    workers=workers if not reload else 1,
                    access_log=access_log,
                )
            except ImportError:
                click.echo("Error: uvicorn is required for --reload and --workers options", err=True)
                click.echo("Install with: pip install uvicorn", err=True)
                sys.exit(1)
        else:
            # Use built-in server
            app_instance.run(host=host, port=port, debug=debug)
    
    except ImportError as e:
        click.echo(f"Error importing application: {e}", err=True)
        sys.exit(1)
    except AttributeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--app", "-a", default="main:app", help="Application module and variable")
@click.option("--output", "-o", default="openapi.json", help="Output file for OpenAPI spec")
@click.option("--format", "-f", type=click.Choice(["json", "yaml"]), default="json", help="Output format")
def openapi(app: str, output: str, format: str):
    """Generate OpenAPI specification."""
    try:
        # Import the application
        module_name, app_name = app.split(":", 1)
        module = __import__(module_name, fromlist=[app_name])
        app_instance = getattr(module, app_name)
        
        if not isinstance(app_instance, AgniAPI):
            click.echo(f"Error: {app} is not an AgniAPI instance", err=True)
            sys.exit(1)
        
        # Generate OpenAPI spec
        openapi_spec = app_instance.openapi_generator.generate_openapi(app_instance.router)
        
        # Write to file
        if format == "json":
            import json
            with open(output, "w") as f:
                json.dump(openapi_spec, f, indent=2)
        elif format == "yaml":
            try:
                import yaml
                with open(output, "w") as f:
                    yaml.dump(openapi_spec, f, default_flow_style=False)
            except ImportError:
                click.echo("Error: PyYAML is required for YAML output", err=True)
                click.echo("Install with: pip install PyYAML", err=True)
                sys.exit(1)
        
        click.echo(f"OpenAPI specification written to {output}")
    
    except ImportError as e:
        click.echo(f"Error importing application: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error generating OpenAPI spec: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--app", "-a", default="main:app", help="Application module and variable")
def routes(app: str):
    """List all routes in the application."""
    try:
        # Import the application
        module_name, app_name = app.split(":", 1)
        module = __import__(module_name, fromlist=[app_name])
        app_instance = getattr(module, app_name)
        
        if not isinstance(app_instance, AgniAPI):
            click.echo(f"Error: {app} is not an AgniAPI instance", err=True)
            sys.exit(1)
        
        # List routes
        routes = app_instance.router.get_all_routes()
        
        if not routes:
            click.echo("No routes found")
            return
        
        click.echo("Routes:")
        click.echo("-" * 80)
        click.echo(f"{'Method':<10} {'Path':<30} {'Name':<20} {'Handler'}")
        click.echo("-" * 80)
        
        for route in routes:
            methods = ", ".join(route.methods)
            handler_name = f"{route.handler.__module__}.{route.handler.__name__}"
            click.echo(f"{methods:<10} {route.path:<30} {route.name:<20} {handler_name}")
    
    except ImportError as e:
        click.echo(f"Error importing application: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error listing routes: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--app", "-a", default="main:app", help="Application module and variable")
@click.option("--transport", "-t", type=click.Choice(["stdio", "sse", "websocket"]), default="stdio", help="MCP transport")
@click.option("--host", "-h", default="localhost", help="Host for SSE/WebSocket transport")
@click.option("--port", "-p", default=8080, help="Port for SSE/WebSocket transport")
def mcp(app: str, transport: str, host: str, port: int):
    """Run MCP server."""
    try:
        # Import the application
        module_name, app_name = app.split(":", 1)
        module = __import__(module_name, fromlist=[app_name])
        app_instance = getattr(module, app_name)
        
        if not isinstance(app_instance, AgniAPI):
            click.echo(f"Error: {app} is not an AgniAPI instance", err=True)
            sys.exit(1)
        
        if not app_instance.mcp_enabled:
            click.echo("Error: MCP is not enabled for this application", err=True)
            sys.exit(1)
        
        click.echo(f"Starting MCP server with {transport} transport")
        
        # Run MCP server
        if transport == "stdio":
            asyncio.run(app_instance.mcp_server.run_stdio())
        elif transport == "sse":
            click.echo(f"MCP server running on http://{host}:{port}")
            asyncio.run(app_instance.mcp_server.run_sse(host, port))
        elif transport == "websocket":
            click.echo(f"MCP server running on ws://{host}:{port}")
            asyncio.run(app_instance.mcp_server.run_websocket(host, port))
    
    except ImportError as e:
        click.echo(f"Error importing application: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running MCP server: {e}", err=True)
        sys.exit(1)




def _create_project_files(project_path: Path, name: str, template: str):
    """Create project files based on template."""

    # Sanitize user input to prevent code injection
    safe_name = name.replace('"', '\\"').replace("'", "\\'").replace("{", "{{").replace("}", "}}")
    safe_title = safe_name.title().replace('"', '\\"')

    # Create main application file
    main_py = f'''"""
{safe_name} - Agni API application
"""

from agniapi import AgniAPI, JSONResponse

app = AgniAPI(
    title="{safe_title}",
    description="A new Agni API application",
    version="0.1.1"
)


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse({{"message": "Hello from {safe_name}!"}})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({{"status": "healthy"}})


if __name__ == "__main__":
    app.run(debug=True)
'''
    
    (project_path / "main.py").write_text(main_py)
    
    # Create requirements.txt
    requirements = '''agniapi>=0.1.1
uvicorn[standard]>=0.18.0
'''
    
    (project_path / "requirements.txt").write_text(requirements)
    
    # Create .gitignore
    gitignore = '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

.pytest_cache/
.coverage
htmlcov/

.DS_Store
'''
    
    (project_path / ".gitignore").write_text(gitignore)
    
    # Create README.md
    readme = f'''# {name.title()}

A new Agni API application.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the development server:
   ```bash
   agniapi run
   ```

3. Open your browser to http://127.0.0.1:8000

## API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Development

- Run tests: `agniapi test`
- Generate OpenAPI spec: `agniapi openapi`
- List routes: `agniapi routes`
'''
    
    (project_path / "README.md").write_text(readme)
    
    # Create tests directory
    tests_dir = project_path / "tests"
    tests_dir.mkdir()
    
    # Create test file
    test_main = f'''"""
Tests for {name}
"""

from agniapi.testing import TestClient
from main import app


def test_root():
    """Test root endpoint."""
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.json() == {{"message": "Hello from {name}!"}}


def test_health():
    """Test health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {{"status": "healthy"}}
'''
    
    (tests_dir / "test_main.py").write_text(test_main)
    (tests_dir / "__init__.py").write_text("")


if __name__ == "__main__":
    cli()
