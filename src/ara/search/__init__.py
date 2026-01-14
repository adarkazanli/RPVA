"""Web search module for Ara Voice Assistant.

Provides web search capabilities using Tavily API.
"""

from .tavily import SearchResult, TavilySearch, create_search_client

__all__ = [
    "SearchResult",
    "TavilySearch",
    "create_search_client",
]
