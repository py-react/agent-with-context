from datetime import datetime
from langchain_core.tools import tool

@tool
def get_current_datetime(format: str = "readable", timezone: str = "UTC") -> str:
    """Get the current date and time in various formats. Use this when users ask about time, date, current time, or need to know what time it is. Examples: 'What time is it?', 'What's the current date?', 'What day is it today?', 'Tell me the time'."""
    now = datetime.now()
    
    if format == "iso":
        formatted_time = now.isoformat()
    elif format == "readable":
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    elif format == "timestamp":
        formatted_time = str(now.timestamp())
    elif format == "date_only":
        formatted_time = now.strftime("%Y-%m-%d")
    elif format == "time_only":
        formatted_time = now.strftime("%H:%M:%S")
    else:
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    return f"Current time ({timezone}): {formatted_time}" 