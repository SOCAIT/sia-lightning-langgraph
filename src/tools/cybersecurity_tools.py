from langchain_core.tools import Tool

def search_tavily(query: str) -> str:
    """Search the web for information"""
    return "I found this information: " + query

research_tools = [
    Tool(
        name="search_tavily",
        func=search_tavily,
        description="Search the web for information"
    )
]
