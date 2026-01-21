"""Web search module for Ara Voice Assistant.

Provides web search capabilities using Tavily and Perplexity APIs.
"""

from .perplexity import PerplexitySearch, create_perplexity_search
from .tavily import SearchResult, TavilySearch, create_search_client

__all__ = [
    "PerplexitySearch",
    "SearchResult",
    "TavilySearch",
    "create_perplexity_search",
    "create_search_client",
]
