from langchain_core.tools import tool

@tool
def get_weather(location: str, unit: str = "celsius") -> str:
    """Get current weather information for a specific location. Use this when users ask about weather, temperature, climate, or weather conditions. Examples: 'What's the weather like?', 'How's the weather in London?', 'What's the temperature?', 'Is it raining?', 'Weather forecast'."""
    # This is a mock implementation - in a real app, you'd call a weather API
    if "london" in location.lower():
        temp = 18 if unit == "celsius" else 64
        return f"Weather in London: {temp}°{'C' if unit == 'celsius' else 'F'}, Partly cloudy"
    elif "new york" in location.lower():
        temp = 22 if unit == "celsius" else 72
        return f"Weather in New York: {temp}°{'C' if unit == 'celsius' else 'F'}, Sunny"
    else:
        temp = 20 if unit == "celsius" else 68
        return f"Weather in {location}: {temp}°{'C' if unit == 'celsius' else 'F'}, Mild conditions" 