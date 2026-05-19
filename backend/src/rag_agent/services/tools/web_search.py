"""Web search tool — DuckDuckGo (default, key-free) or Tavily.

Wraps results as LangChain ``Document`` objects so they flow seamlessly through
the rest of the agent's context-handling code.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger(__name__)


def _ddg_search(query: str, max_results: int) -> List[Document]:
    from duckduckgo_search import DDGS

    results: List[Document] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results) or []:
            body = r.get("body") or r.get("snippet") or ""
            results.append(
                Document(
                    page_content=body,
                    metadata={
                        "title": r.get("title"),
                        "source": r.get("href") or r.get("url"),
                        "origin": "web",
                        "provider": "duckduckgo",
                    },
                )
            )
    return results


def _tavily_search(query: str, max_results: int, api_key: str) -> List[Document]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results, search_depth="advanced")
    docs: List[Document] = []
    for r in response.get("results", []) or []:
        docs.append(
            Document(
                page_content=r.get("content", ""),
                metadata={
                    "title": r.get("title"),
                    "source": r.get("url"),
                    "score": r.get("score"),
                    "origin": "web",
                    "provider": "tavily",
                },
            )
        )
    return docs


def web_search(query: str, max_results: int | None = None) -> List[Document]:
    """Search the public web and return results as LangChain Documents."""
    settings = get_settings()
    n = max_results or settings.web_search_max_results
    logger.info("WEB_SEARCH | provider=%s | query='%s'", settings.web_search_provider, query)

    try:
        if settings.web_search_provider == "tavily" and settings.tavily_api_key:
            return _tavily_search(query, n, settings.tavily_api_key)
        return _ddg_search(query, n)
    except Exception as exc:  # noqa: BLE001
        logger.warning("WEB_SEARCH | failure: %s", exc)
        return []
