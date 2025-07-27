import aiohttp
import asyncio
from langchain_core.tools import tool

@tool
def check_system_health(endpoint: str = "http://localhost:5001/api/health", timeout: int = 10) -> str:
    """Check the health status of the system by making a request to the health endpoint. Use this when users ask about system status, health, if the system is working properly, or want to know if services are running. Examples: 'Is the system working?', 'Check system health', 'Are all services running?', 'System status', 'Health check'."""
    try:
        # Use asyncio to run the async function
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_async_health_check(endpoint, timeout))
    except RuntimeError:
        # If no event loop is running, create a new one
        return asyncio.run(_async_health_check(endpoint, timeout))

async def _async_health_check(endpoint: str, timeout: int) -> str:
    """Execute the health check asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    # Extract key information
                    overall_status = health_data.get("status", "unknown")
                    services = health_data.get("services", {})
                    
                    # Build a readable response
                    result_parts = [f"System Status: {overall_status.upper()}"]
                    
                    if services:
                        result_parts.append("\nService Status:")
                        for service_name, service_info in services.items():
                            service_status = service_info.get("status", "unknown")
                            result_parts.append(f"  • {service_name}: {service_status}")
                            
                            # Add additional details if available
                            if service_name == "redis" and "connected" in service_info:
                                result_parts.append(f"    - Connected: {service_info['connected']}")
                            elif service_name == "agent_workflow" and "test_response_length" in service_info:
                                result_parts.append(f"    - Test Response Length: {service_info['test_response_length']} characters")
                    
                    # Add config info if available
                    config = health_data.get("config", {})
                    if config:
                        result_parts.append("\nConfiguration:")
                        result_parts.append(f"  • Valid: {config.get('valid', 'unknown')}")
                        result_parts.append(f"  • Model: {config.get('gemini_model', 'unknown')}")
                    
                    return "\n".join(result_parts)
                else:
                    return f"Health check failed with status code: {response.status}"
                    
    except asyncio.TimeoutError:
        return f"Health check timed out after {timeout} seconds"
    except aiohttp.ClientError as e:
        return f"Network error during health check: {str(e)}"
    except Exception as e:
        return f"Error during health check: {str(e)}" 