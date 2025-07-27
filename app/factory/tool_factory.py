from render_relay.utils.get_logger import get_logger
from ..tools.datetime_tool import get_current_datetime
from ..tools.weather_tool import get_weather
from ..tools.health_tool import check_system_health
from ..tools.calculator_tool import calculate
from ..tools.context_tool import retrieve_session_context


logger = get_logger("tool_factory")


class ToolFactory:
    def __init__(self):
        self.tools = [
            get_current_datetime,
            get_weather,
            check_system_health,
            calculate,
            retrieve_session_context,
        ]
        
    def get_tool_names(self):
        return [tool.name for tool in self.tools]

    def add_tool(self, tool):
        self.tools.append(tool)

    def get_tools(self):
        return self.tools