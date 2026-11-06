"""
OpenOS Web Browser Tool.

Open URLs, search the web, and manage browser tabs.
"""

from __future__ import annotations

import subprocess
import urllib.parse

from openos_core.tools.base import BaseTool, tool_function


class WebBrowserTool(BaseTool):
    """Open websites and search the web."""

    @property
    def name(self) -> str:
        return "web_browser"

    @property
    def description(self) -> str:
        return "Open websites, search the web, and manage browser"

    @tool_function(
        description="Open a URL or website in the default browser",
        parameters={
            "url": {"type": "string", "description": "URL or website name (e.g., 'youtube.com', 'https://github.com')"},
        },
    )
    def open_url(self, url: str) -> str:
        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            if "." in url:
                url = f"https://{url}"
            else:
                # Treat as search query
                return str(self.search_web(query=url))
        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"🌐 Opened: {url}"
        except Exception as e:
            return f"Failed to open browser: {e}"

    @tool_function(
        description="Search the web using the default search engine",
        parameters={
            "query": {"type": "string", "description": "Search query"},
        },
    )
    def search_web(self, query: str) -> str:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://duckduckgo.com/?q={encoded}"
        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"🔍 Searching: {query}"
        except Exception as e:
            return f"Search failed: {e}"

    @tool_function(
        description="Open YouTube and optionally search for a video",
        parameters={
            "query": {"type": "string", "description": "YouTube search query", "optional": True},
        },
    )
    def open_youtube(self, query: str = "") -> str:
        if query:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            url = "https://www.youtube.com"
        return str(self.open_url(url))
