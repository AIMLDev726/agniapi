"""
MCP Server example using Agni API framework.
Demonstrates how to create an API that also serves as an MCP server.
"""

import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime

from agniapi import AgniAPI, mcp_tool, mcp_resource, mcp_prompt
from agniapi.response import JSONResponse


# Create the application with MCP enabled
app = AgniAPI(
    title="MCP Server Example",
    description="An API that demonstrates MCP server capabilities",
    version="1.0.0",
    mcp_enabled=True,
    mcp_server_name="agni-example-server"
)

# Mock data
weather_data = {
    "New York": {"temperature": 22, "condition": "sunny", "humidity": 65},
    "London": {"temperature": 15, "condition": "cloudy", "humidity": 80},
    "Tokyo": {"temperature": 28, "condition": "rainy", "humidity": 90},
    "Sydney": {"temperature": 18, "condition": "windy", "humidity": 55},
}

user_data = [
    {"id": 1, "name": "Alice", "role": "admin", "active": True},
    {"id": 2, "name": "Bob", "role": "user", "active": True},
    {"id": 3, "name": "Charlie", "role": "user", "active": False},
]

system_logs = [
    {"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "message": "System started"},
    {"timestamp": "2024-01-01T10:05:00Z", "level": "WARN", "message": "High memory usage"},
    {"timestamp": "2024-01-01T10:10:00Z", "level": "ERROR", "message": "Database connection failed"},
]


# Regular API endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MCP Server Example",
        "mcp_enabled": True,
        "available_tools": ["get_weather", "search_users", "analyze_logs"],
        "available_resources": ["weather_data", "user_database", "system_logs"],
        "available_prompts": ["weather_report", "user_summary"]
    }


@app.get("/weather/{city}")
async def get_weather_api(city: str):
    """Get weather via regular API endpoint."""
    if city not in weather_data:
        return {"error": "City not found"}
    return {"city": city, **weather_data[city]}


@app.get("/users")
async def list_users_api():
    """List users via regular API endpoint."""
    return {"users": user_data}


# MCP Tools
@mcp_tool(
    name="get_weather",
    description="Get current weather information for a specific city"
)
async def get_weather_tool(city: str) -> Dict[str, Any]:
    """
    Get weather information for a city.
    
    Args:
        city: Name of the city to get weather for
    
    Returns:
        Weather information including temperature, condition, and humidity
    """
    city_normalized = city.title()
    
    if city_normalized not in weather_data:
        return {
            "error": f"Weather data not available for {city}",
            "available_cities": list(weather_data.keys())
        }
    
    weather = weather_data[city_normalized]
    return {
        "city": city_normalized,
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "timestamp": datetime.now().isoformat()
    }


@mcp_tool(
    name="search_users",
    description="Search for users by name or role"
)
async def search_users_tool(query: str, role: str = None) -> List[Dict[str, Any]]:
    """
    Search for users in the system.
    
    Args:
        query: Search query for user name
        role: Optional role filter (admin, user)
    
    Returns:
        List of matching users
    """
    results = []
    
    for user in user_data:
        # Check name match
        name_match = query.lower() in user["name"].lower()
        
        # Check role filter
        role_match = role is None or user["role"] == role
        
        if name_match and role_match:
            results.append(user)
    
    return results


@mcp_tool(
    name="analyze_logs",
    description="Analyze system logs and provide insights"
)
async def analyze_logs_tool(level: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    Analyze system logs.
    
    Args:
        level: Log level filter (INFO, WARN, ERROR)
        limit: Maximum number of logs to analyze
    
    Returns:
        Log analysis results
    """
    filtered_logs = system_logs
    
    if level:
        filtered_logs = [log for log in system_logs if log["level"] == level.upper()]
    
    # Limit results
    filtered_logs = filtered_logs[:limit]
    
    # Basic analysis
    level_counts = {}
    for log in system_logs:
        level_counts[log["level"]] = level_counts.get(log["level"], 0) + 1
    
    return {
        "total_logs": len(system_logs),
        "filtered_logs": len(filtered_logs),
        "level_distribution": level_counts,
        "recent_logs": filtered_logs,
        "analysis_timestamp": datetime.now().isoformat()
    }


# MCP Resources
@mcp_resource(
    uri="weather://data",
    name="Weather Data",
    description="Complete weather database",
    mime_type="application/json"
)
async def weather_resource() -> str:
    """Provide access to complete weather data."""
    return json.dumps({
        "weather_data": weather_data,
        "last_updated": datetime.now().isoformat(),
        "cities_count": len(weather_data)
    }, indent=2)


@mcp_resource(
    uri="database://users",
    name="User Database",
    description="User management database",
    mime_type="application/json"
)
async def user_database_resource() -> str:
    """Provide access to user database."""
    active_users = [user for user in user_data if user["active"]]
    inactive_users = [user for user in user_data if not user["active"]]
    
    return json.dumps({
        "users": user_data,
        "statistics": {
            "total_users": len(user_data),
            "active_users": len(active_users),
            "inactive_users": len(inactive_users),
            "admin_users": len([u for u in user_data if u["role"] == "admin"])
        },
        "last_updated": datetime.now().isoformat()
    }, indent=2)


@mcp_resource(
    uri="logs://system",
    name="System Logs",
    description="System log files and monitoring data",
    mime_type="text/plain"
)
async def system_logs_resource() -> str:
    """Provide access to system logs."""
    log_text = []
    log_text.append("=== SYSTEM LOGS ===")
    log_text.append(f"Generated: {datetime.now().isoformat()}")
    log_text.append("")
    
    for log in system_logs:
        log_line = f"[{log['timestamp']}] {log['level']}: {log['message']}"
        log_text.append(log_line)
    
    log_text.append("")
    log_text.append(f"Total entries: {len(system_logs)}")
    
    return "\n".join(log_text)


# MCP Prompts
@mcp_prompt(
    name="weather_report",
    description="Generate a weather report prompt for a city"
)
async def weather_report_prompt(city: str, format: str = "detailed") -> Dict[str, Any]:
    """
    Generate a prompt for creating weather reports.
    
    Args:
        city: City name for the weather report
        format: Report format (brief, detailed, forecast)
    
    Returns:
        Prompt template for weather reporting
    """
    weather_info = await get_weather_tool(city)
    
    if format == "brief":
        prompt_text = f"Create a brief weather summary for {city}. Current conditions: {weather_info}"
    elif format == "forecast":
        prompt_text = f"Create a weather forecast for {city} based on current conditions: {weather_info}. Include predictions for the next 24 hours."
    else:  # detailed
        prompt_text = f"Create a detailed weather report for {city}. Include current conditions, analysis, and recommendations. Data: {weather_info}"
    
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a professional meteorologist creating weather reports."
            },
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    }


@mcp_prompt(
    name="user_summary",
    description="Generate a user summary prompt"
)
async def user_summary_prompt(user_id: int = None, include_stats: bool = True) -> Dict[str, Any]:
    """
    Generate a prompt for user analysis.
    
    Args:
        user_id: Specific user ID to analyze (optional)
        include_stats: Whether to include statistics
    
    Returns:
        Prompt template for user analysis
    """
    if user_id:
        user = next((u for u in user_data if u["id"] == user_id), None)
        if user:
            prompt_text = f"Analyze this user profile: {user}. Provide insights about their role, status, and recommendations."
        else:
            prompt_text = f"User with ID {user_id} not found. Provide guidance on user management."
    else:
        prompt_text = f"Analyze the user database: {user_data}. "
        if include_stats:
            prompt_text += "Include statistics, patterns, and recommendations for user management."
        else:
            prompt_text += "Focus on user roles and access patterns."
    
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a user management specialist analyzing user data and providing insights."
            },
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    }


# MCP server management endpoints
@app.get("/mcp/status")
async def mcp_status():
    """Get MCP server status."""
    if not app.mcp_enabled:
        return {"mcp_enabled": False}
    
    return {
        "mcp_enabled": True,
        "server_name": app.mcp_server.name,
        "tools": list(app.mcp_server.get_tools().keys()),
        "resources": list(app.mcp_server.get_resources().keys()),
        "prompts": list(app.mcp_server.get_prompts().keys())
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Run as MCP server
        print("Starting MCP server...")
        asyncio.run(app.mcp_server.run_stdio())
    else:
        # Run as regular API server
        print("Starting API server...")
        print("To run as MCP server: python mcp_server_example.py mcp")
        app.run(host="127.0.0.1", port=8000, debug=True)
